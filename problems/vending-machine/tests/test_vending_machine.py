"""The state machine, one transition at a time."""

import pytest
from vending_machine import VendingMachine
from vending_machine.model import CannotMakeChange, Coin, SoldOut
from vending_machine.states import InvalidAction


@pytest.fixture
def machine():
    m = VendingMachine()
    m.add_item("A1", "Coke", 75, quantity=2)
    m.add_item("A2", "Chips", 50, quantity=1)
    m.load_coins(quarter=4, dime=4, nickel=4)
    return m


# -- transitions ----------------------------------------------------------


def test_a_new_machine_is_idle(machine):
    assert str(machine.state) == "idle"


def test_inserting_a_coin_moves_to_has_money(machine):
    machine.insert_coin("quarter")

    assert str(machine.state) == "has-money"
    assert machine.balance == 25


def test_selecting_an_affordable_item_moves_to_dispensing(machine):
    machine.insert_coin("dollar")
    machine.select_item("A1")

    assert str(machine.state) == "dispensing"


def test_dispensing_returns_to_idle(machine):
    machine.insert_coin("dollar")
    machine.select_item("A1")
    machine.dispense()

    assert str(machine.state) == "idle"
    assert machine.balance == 0


def test_the_machine_goes_sold_out_when_the_last_item_leaves(machine):
    for code, coins in (("A1", 3), ("A1", 3), ("A2", 2)):
        for _ in range(coins):
            machine.insert_coin("quarter")
        machine.select_item(code)
        machine.dispense()

    assert str(machine.state) == "sold-out"


def test_restocking_brings_a_sold_out_machine_back(machine):
    machine.inventory.get_slot("A1").quantity = 0
    machine.inventory.get_slot("A2").quantity = 0
    machine.refresh_availability()
    assert str(machine.state) == "sold-out"

    machine.restock("A1", 5)

    assert str(machine.state) == "idle"


# -- actions each state refuses -------------------------------------------


def test_you_cannot_select_before_paying(machine):
    with pytest.raises(InvalidAction, match="Insert a coin"):
        machine.select_item("A1")


def test_you_cannot_dispense_before_selecting(machine):
    machine.insert_coin("dollar")

    with pytest.raises(InvalidAction, match="select an item"):
        machine.dispense()


def test_you_cannot_refund_when_you_have_paid_nothing(machine):
    with pytest.raises(InvalidAction, match="Nothing to refund"):
        machine.refund()


def test_a_sold_out_machine_takes_no_money(machine):
    machine.inventory.get_slot("A1").quantity = 0
    machine.inventory.get_slot("A2").quantity = 0
    machine.refresh_availability()

    with pytest.raises(InvalidAction, match="sold out"):
        machine.insert_coin("quarter")


def test_a_sold_out_machine_still_refunds_money_already_in_it(machine):
    machine.insert_coin("dollar")
    machine.inventory.get_slot("A1").quantity = 0
    machine.inventory.get_slot("A2").quantity = 0
    machine.set_state(machine.sold_out_state)

    assert machine.refund() == [Coin.DOLLAR]


# -- money ----------------------------------------------------------------


def test_too_little_money_says_how_much_is_missing(machine):
    machine.insert_coin("quarter")

    with pytest.raises(ValueError, match="you are 50 short"):
        machine.select_item("A1")


def test_too_little_money_keeps_the_balance_and_the_state(machine):
    machine.insert_coin("quarter")

    with pytest.raises(ValueError):
        machine.select_item("A1")

    assert machine.balance == 25
    assert str(machine.state) == "has-money"


def test_change_is_made_from_the_largest_coins_first(machine):
    machine.insert_coin("dollar")
    machine.select_item("A2")  # 50c
    machine.dispense()

    assert machine.last_change == [Coin.QUARTER, Coin.QUARTER]


def test_exact_money_gives_no_change(machine):
    for _ in range(3):
        machine.insert_coin("quarter")
    machine.select_item("A1")
    machine.dispense()

    assert machine.last_change == []


def test_a_machine_that_cannot_make_change_keeps_the_item_and_the_money():
    machine = VendingMachine()
    machine.add_item("A1", "Coke", 75, quantity=1)
    # Empty float, so 25c of change is impossible.
    machine.insert_coin("dollar")
    machine.select_item("A1")

    with pytest.raises(CannotMakeChange, match="short by 25"):
        machine.dispense()

    assert machine.inventory.get_slot("A1").quantity == 1, "the item must stay on the shelf"
    assert machine.balance == 100, "the buyer's money must not vanish"


def test_a_refund_returns_the_exact_coins_that_went_in(machine):
    machine.insert_coin("dollar")
    machine.insert_coin("nickel")

    assert machine.refund() == [Coin.DOLLAR, Coin.NICKEL]
    assert machine.balance == 0
    assert str(machine.state) == "idle"


def test_you_can_change_your_mind_after_selecting(machine):
    machine.insert_coin("dollar")
    machine.select_item("A1")

    assert machine.refund() == [Coin.DOLLAR]
    assert machine.inventory.get_slot("A1").quantity == 2


def test_paid_coins_join_the_float_so_later_change_can_use_them(machine):
    before = machine.coin_box.total

    machine.insert_coin("dollar")
    machine.select_item("A1")
    machine.dispense()

    assert machine.coin_box.total == before + 100 - 25


# -- input validation -----------------------------------------------------


def test_an_unaccepted_denomination_lists_the_accepted_ones(machine):
    with pytest.raises(ValueError, match="quarter"):
        machine.insert_coin(7)


def test_an_unknown_slot_lists_the_real_ones(machine):
    machine.insert_coin("dollar")

    with pytest.raises(KeyError, match="A1, A2"):
        machine.select_item("Z9")


def test_selecting_a_sold_out_slot_keeps_your_money(machine):
    machine.inventory.get_slot("A2").quantity = 0
    machine.insert_coin("dollar")

    with pytest.raises(SoldOut, match="Chips is sold out"):
        machine.select_item("A2")

    assert machine.balance == 100
    assert str(machine.state) == "has-money"


def test_an_item_needs_a_positive_price():
    with pytest.raises(ValueError, match="positive price"):
        VendingMachine().add_item("A1", "Free Coke", 0)


def test_a_slot_code_cannot_be_reused(machine):
    with pytest.raises(KeyError, match="already taken by Coke"):
        machine.add_item("A1", "Pepsi", 75)
