"""The state machine, the dispenser chain, and the all-or-nothing guarantee."""

import pytest
from atm import ATM, Bank, CashDispenser, Denomination, InsufficientCash, InsufficientFunds
from atm.bank import AuthenticationFailed
from atm.states import InvalidOperation


@pytest.fixture
def bank():
    b = Bank()
    b.open_account("111", "1234", balance=50_000)
    b.open_account("222", "4321", balance=10_000)
    return b


@pytest.fixture
def dispenser():
    d = CashDispenser()
    d.load(two_thousand=10, five_hundred=10, two_hundred=10, hundred=10)
    return d


@pytest.fixture
def machine(bank, dispenser):
    return ATM(bank, dispenser)


@pytest.fixture
def signed_in(machine):
    machine.insert_card("111")
    machine.enter_pin("1234")
    return machine


# -- the dispenser chain --------------------------------------------------


def test_the_chain_uses_the_largest_notes_first(dispenser):
    plan = dispenser.plan(4700)

    # 4700 is exactly 2x2000 + 1x500 + 1x200, so the chain stops before the
    # hundred handler is ever asked.
    assert plan == {
        Denomination.TWO_THOUSAND: 2,
        Denomination.FIVE_HUNDRED: 1,
        Denomination.TWO_HUNDRED: 1,
    }


def test_the_chain_falls_back_when_a_note_runs_out():
    dispenser = CashDispenser()
    dispenser.load(two_thousand=1, five_hundred=10)

    plan = dispenser.plan(4000)

    assert plan[Denomination.TWO_THOUSAND] == 1
    assert plan[Denomination.FIVE_HUNDRED] == 4


def test_dispensing_removes_the_notes(dispenser):
    before = dispenser.total

    dispenser.dispense(2000)

    assert dispenser.total == before - 2000
    assert dispenser.inventory[Denomination.TWO_THOUSAND] == 9


def test_an_amount_the_notes_cannot_make_is_refused():
    dispenser = CashDispenser()
    dispenser.load(two_thousand=5)

    with pytest.raises(InsufficientCash):
        dispenser.plan(3000)


def test_a_refused_amount_takes_nothing_from_the_box():
    """The guarantee that matters: all of it, or none of it."""
    dispenser = CashDispenser()
    dispenser.load(two_thousand=5)
    before = dict(dispenser.inventory)

    with pytest.raises(InsufficientCash):
        dispenser.dispense(3000)

    assert dispenser.inventory == before, "a failed dispense must not eat notes"


def test_an_amount_beyond_the_machines_cash_is_refused(dispenser):
    with pytest.raises(InsufficientCash, match="less than"):
        dispenser.plan(dispenser.total + 100)


def test_an_amount_that_is_not_a_multiple_of_the_smallest_note_is_refused(dispenser):
    with pytest.raises(ValueError, match="smallest note is 100"):
        dispenser.plan(150)


def test_a_negative_amount_is_refused(dispenser):
    with pytest.raises(ValueError, match="must be positive"):
        dispenser.plan(-100)


def test_can_dispense_answers_without_taking_anything(dispenser):
    before = dict(dispenser.inventory)

    assert dispenser.can_dispense(4700)
    assert not dispenser.can_dispense(150)
    assert dispenser.inventory == before


# -- states ---------------------------------------------------------------


def test_a_new_machine_is_idle(machine):
    assert str(machine.state) == "idle"


def test_a_card_moves_the_machine_on(machine):
    machine.insert_card("111")

    assert str(machine.state) == "card-inserted"


def test_a_correct_pin_signs_you_in(machine):
    machine.insert_card("111")
    machine.enter_pin("1234")

    assert str(machine.state) == "authenticated"


def test_you_cannot_withdraw_before_inserting_a_card(machine):
    with pytest.raises(InvalidOperation, match="insert your card"):
        machine.withdraw(2000)


def test_you_cannot_withdraw_before_entering_a_pin(machine):
    machine.insert_card("111")

    with pytest.raises(InvalidOperation, match="enter your PIN"):
        machine.withdraw(2000)


def test_you_cannot_check_a_balance_before_signing_in(machine):
    machine.insert_card("111")

    with pytest.raises(InvalidOperation, match="enter your PIN"):
        machine.check_balance()


def test_you_cannot_insert_a_second_card(machine):
    machine.insert_card("111")

    with pytest.raises(InvalidOperation, match="Cannot accept a card"):
        machine.insert_card("222")


def test_ejecting_the_card_ends_the_session(signed_in):
    signed_in.eject_card()

    assert str(signed_in.state) == "idle"
    assert signed_in.account is None
    assert signed_in.card_account_number is None


# -- authentication -------------------------------------------------------


def test_a_wrong_pin_says_how_many_tries_are_left(machine):
    machine.insert_card("111")

    with pytest.raises(AuthenticationFailed, match="2 attempt"):
        machine.enter_pin("0000")


def test_a_wrong_pin_leaves_you_able_to_try_again(machine):
    machine.insert_card("111")
    with pytest.raises(AuthenticationFailed):
        machine.enter_pin("0000")

    assert machine.enter_pin("1234").startswith("Welcome")


def test_three_wrong_pins_block_the_card(machine, bank):
    machine.insert_card("111")
    for _ in range(2):
        with pytest.raises(AuthenticationFailed):
            machine.enter_pin("0000")

    with pytest.raises(AuthenticationFailed, match="blocked"):
        machine.enter_pin("0000")

    assert bank.accounts["111"].blocked


def test_a_blocked_card_is_returned(machine):
    machine.insert_card("111")
    for _ in range(3):
        with pytest.raises(AuthenticationFailed):
            machine.enter_pin("0000")

    assert str(machine.state) == "idle", "a blocked card must not stay in the machine"


def test_a_correct_pin_clears_the_failure_count(machine, bank):
    machine.insert_card("111")
    with pytest.raises(AuthenticationFailed):
        machine.enter_pin("0000")
    machine.enter_pin("1234")
    machine.eject_card()

    machine.insert_card("111")
    with pytest.raises(AuthenticationFailed, match="2 attempt"):
        machine.enter_pin("0000")


def test_an_unknown_card_is_returned(machine):
    machine.insert_card("999")

    with pytest.raises(AuthenticationFailed, match="No account"):
        machine.enter_pin("1234")

    assert str(machine.state) == "idle"


# -- withdrawals ----------------------------------------------------------


def test_a_withdrawal_debits_the_account(signed_in):
    signed_in.withdraw(2000)

    assert signed_in.account.balance == 48_000


def test_a_withdrawal_hands_over_notes(signed_in, dispenser):
    plan = signed_in.withdraw(4700)

    assert sum(int(note) * count for note, count in plan.items()) == 4700


def test_withdrawing_more_than_the_balance_is_refused(machine, bank):
    machine.insert_card("222")
    machine.enter_pin("4321")

    with pytest.raises(InsufficientFunds, match="will not cover"):
        machine.withdraw(20_000)


def test_a_refused_withdrawal_leaves_the_balance_alone(machine, bank):
    machine.insert_card("222")
    machine.enter_pin("4321")

    with pytest.raises(InsufficientFunds):
        machine.withdraw(20_000)

    assert bank.accounts["222"].balance == 10_000


def test_the_daily_limit_is_enforced(bank, dispenser):
    bank.open_account("333", "1111", balance=100_000, daily_limit=10_000)
    machine = ATM(bank, dispenser)
    machine.insert_card("333")
    machine.enter_pin("1111")
    machine.withdraw(8000)
    machine.collect_cash()

    with pytest.raises(InsufficientFunds, match="Daily limit"):
        machine.withdraw(4000)


def test_the_daily_limit_resets(bank, dispenser):
    bank.open_account("333", "1111", balance=100_000, daily_limit=10_000)
    machine = ATM(bank, dispenser)
    machine.insert_card("333")
    machine.enter_pin("1111")
    machine.withdraw(8000)
    machine.collect_cash()

    bank.accounts["333"].start_new_day()

    assert machine.withdraw(8000)


def test_a_withdrawal_the_machine_cannot_make_leaves_the_balance_alone(bank):
    """Debiting before checking the notes is how a customer pays for nothing."""
    dispenser = CashDispenser()
    dispenser.load(two_thousand=5)
    machine = ATM(bank, dispenser)
    machine.insert_card("111")
    machine.enter_pin("1234")

    with pytest.raises(InsufficientCash):
        machine.withdraw(3000)

    assert bank.accounts["111"].balance == 50_000
    assert dispenser.total == 10_000


def test_cash_has_to_be_collected_before_the_next_withdrawal(signed_in):
    signed_in.withdraw(2000)

    with pytest.raises(InvalidOperation, match="take your cash"):
        signed_in.withdraw(2000)


def test_collecting_cash_returns_to_the_menu(signed_in):
    signed_in.withdraw(2000)

    signed_in.collect_cash()

    assert str(signed_in.state) == "authenticated"


# -- other transactions ---------------------------------------------------


def test_a_deposit_credits_the_account(signed_in):
    assert signed_in.deposit(5000) == 55_000


def test_a_transfer_moves_money_between_accounts(signed_in, bank):
    signed_in.transfer("222", 5000)

    assert bank.accounts["111"].balance == 45_000
    assert bank.accounts["222"].balance == 15_000


def test_a_transfer_beyond_the_balance_moves_nothing(machine, bank):
    machine.insert_card("222")
    machine.enter_pin("4321")

    with pytest.raises(InsufficientFunds):
        machine.transfer("111", 20_000)

    assert bank.accounts["111"].balance == 50_000
    assert bank.accounts["222"].balance == 10_000


def test_you_cannot_transfer_to_yourself(signed_in):
    with pytest.raises(ValueError, match="same account"):
        signed_in.transfer("111", 1000)


def test_a_transfer_to_an_unknown_account_is_refused(signed_in):
    with pytest.raises(AuthenticationFailed, match="No account"):
        signed_in.transfer("999", 1000)
