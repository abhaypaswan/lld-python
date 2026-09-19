"""Splits that add up, and settlements that clear."""

import pytest
from splitwise import (
    EqualSplit,
    ExactSplit,
    ExpenseManager,
    PercentageSplit,
    ShareSplit,
    User,
)
from splitwise.user import Observer


@pytest.fixture
def people():
    return [User("alice"), User("bob"), User("carol")]


@pytest.fixture
def manager(people):
    m = ExpenseManager()
    for user in people:
        m.add_user(user)
    return m


# -- splits ---------------------------------------------------------------


def test_an_even_split_divides_cleanly(people):
    shares = EqualSplit().split(90, people)

    assert list(shares.values()) == [30, 30, 30]


def test_an_uneven_split_still_sums_to_the_total(people):
    shares = EqualSplit().split(100, people)

    assert sum(shares.values()) == 100, "the remainder must not be lost or invented"
    assert sorted(shares.values()) == [33, 33, 34]


@pytest.mark.parametrize("amount", range(1, 200))
def test_an_equal_split_always_sums_to_the_total(amount, people):
    assert sum(EqualSplit().split(amount, people).values()) == amount


@pytest.mark.parametrize("amount", [1, 7, 99, 100, 101, 1_000_003])
def test_nobody_is_more_than_one_unit_out_of_step(amount, people):
    shares = sorted(EqualSplit().split(amount, people).values())

    assert shares[-1] - shares[0] <= 1


def test_an_exact_split_uses_the_stated_amounts(people):
    alice, bob, carol = people
    strategy = ExactSplit({alice: 50, bob: 30, carol: 20})

    assert strategy.split(100, people) == {alice: 50, bob: 30, carol: 20}


def test_an_exact_split_that_does_not_add_up_is_rejected(people):
    alice, bob, carol = people
    strategy = ExactSplit({alice: 50, bob: 30, carol: 30})

    with pytest.raises(ValueError, match="Shares sum to 110"):
        strategy.split(100, people)


def test_an_exact_split_needs_an_amount_for_everyone(people):
    alice, bob, carol = people

    with pytest.raises(ValueError, match="No amount given for: carol"):
        ExactSplit({alice: 50, bob: 50}).split(100, people)


def test_an_exact_split_rejects_amounts_for_outsiders(people):
    alice, bob, carol = people
    outsider = User("dave")

    with pytest.raises(ValueError, match="not on the expense: dave"):
        ExactSplit({alice: 40, bob: 30, carol: 30, outsider: 0}).split(100, people)


def test_a_percentage_split_apportions_by_percent(people):
    alice, bob, carol = people
    strategy = PercentageSplit({alice: 50, bob: 25, carol: 25})

    assert strategy.split(1000, people) == {alice: 500, bob: 250, carol: 250}


def test_percentages_have_to_add_up_to_a_hundred(people):
    alice, bob, carol = people

    with pytest.raises(ValueError, match="add up to 100, got 90"):
        PercentageSplit({alice: 50, bob: 20, carol: 20}).split(100, people)


def test_a_percentage_split_with_an_awkward_total_still_balances(people):
    alice, bob, carol = people
    shares = PercentageSplit({alice: 33.33, bob: 33.33, carol: 33.34}).split(1000, people)

    assert sum(shares.values()) == 1000


def test_a_share_split_weights_by_share_count(people):
    alice, bob, carol = people
    # Alice has the big room.
    shares = ShareSplit({alice: 2, bob: 1, carol: 1}).split(400, people)

    assert shares == {alice: 200, bob: 100, carol: 100}


def test_a_share_split_can_give_someone_nothing(people):
    alice, bob, carol = people
    shares = ShareSplit({alice: 1, bob: 1, carol: 0}).split(100, people)

    assert shares[carol] == 0
    assert sum(shares.values()) == 100


def test_share_counts_cannot_all_be_zero(people):
    alice, bob, carol = people

    with pytest.raises(ValueError, match="cannot all be zero"):
        ShareSplit({alice: 0, bob: 0, carol: 0}).split(100, people)


def test_a_split_needs_participants():
    with pytest.raises(ValueError, match="at least one participant"):
        EqualSplit().split(100, [])


def test_the_same_person_cannot_appear_twice(people):
    alice = people[0]

    with pytest.raises(ValueError, match="cannot appear twice"):
        EqualSplit().split(100, [alice, alice])


# -- balances -------------------------------------------------------------


def test_the_payer_is_owed_everyone_elses_share(manager, people):
    alice, bob, carol = people
    manager.add_expense(alice, 90, people)

    assert manager.balance_of(alice) == 60
    assert manager.balance_of(bob) == -30
    assert manager.balance_of(carol) == -30


def test_balances_always_net_to_zero(manager, people):
    alice, bob, carol = people
    manager.add_expense(alice, 100, people)
    manager.add_expense(bob, 61, [bob, carol])
    manager.add_expense(carol, 17, people)

    assert sum(manager.balances.values()) == 0


def test_someone_can_pay_for_others_without_taking_part(manager, people):
    alice, bob, carol = people
    manager.add_expense(alice, 100, [bob, carol], description="gift")

    assert manager.balance_of(alice) == 100
    assert manager.balance_of(bob) == -50


def test_an_expense_has_to_be_positive(manager, people):
    with pytest.raises(ValueError, match="must be positive"):
        manager.add_expense(people[0], 0, people)


def test_shares_are_frozen_at_the_time_of_the_expense(manager, people):
    alice, bob, carol = people
    strategy = ExactSplit({alice: 50, bob: 30, carol: 20})
    expense = manager.add_expense(alice, 100, people, strategy)

    strategy.amounts[alice] = 999

    assert expense.shares[alice] == 50, "history must not change under you"


def test_a_user_cannot_be_added_twice(manager):
    with pytest.raises(KeyError, match="already in this group"):
        manager.add_user(User("alice"))


# -- settling up ----------------------------------------------------------


def test_a_settlement_clears_the_balance(manager, people):
    alice, bob, carol = people
    manager.add_expense(alice, 90, people)

    manager.settle(bob, alice, 30)

    assert manager.balance_of(bob) == 0
    assert manager.balance_of(alice) == 30


def test_simplify_produces_payments_that_clear_everyone(manager, people):
    alice, bob, carol = people
    manager.add_expense(alice, 90, people)
    manager.add_expense(bob, 60, people)

    for payer, payee, amount in manager.simplify():
        manager.settle(payer, payee, amount)

    assert all(balance == 0 for balance in manager.balances.values())


def test_simplify_cuts_out_the_middleman(manager, people):
    alice, bob, carol = people
    # Alice owes Bob 10, Bob owes Carol 10. One payment settles it, not two.
    manager.balances = {alice: -10, bob: 0, carol: 10}

    payments = manager.simplify()

    assert payments == [(alice, carol, 10)]


def test_simplify_needs_no_more_than_n_minus_one_payments(manager, people):
    alice, bob, carol = people
    manager.add_expense(alice, 100, people)
    manager.add_expense(bob, 55, people)
    manager.add_expense(carol, 31, people)

    assert len(manager.simplify()) <= len(people) - 1


def test_a_settled_group_needs_no_payments(manager, people):
    assert manager.simplify() == []
    assert manager.summary() == "Everyone is settled up."


def test_a_settlement_has_to_be_positive(manager, people):
    with pytest.raises(ValueError, match="must be positive"):
        manager.settle(people[0], people[1], 0)


# -- observers ------------------------------------------------------------


def test_observers_hear_about_new_expenses(manager, people):
    observer = Observer()
    manager.subscribe(observer)

    manager.add_expense(people[0], 90, people)

    assert observer.events[0][0] == "expense"


def test_observers_hear_about_settlements(manager, people):
    observer = Observer()
    manager.subscribe(observer)
    manager.add_expense(people[0], 90, people)

    manager.settle(people[1], people[0], 30)

    assert observer.events[-1][0] == "settlement"


def test_several_observers_all_get_told(manager, people):
    first, second = Observer(), Observer()
    manager.subscribe(first)
    manager.subscribe(second)

    manager.add_expense(people[0], 90, people)

    assert len(first.events) == len(second.events) == 1
