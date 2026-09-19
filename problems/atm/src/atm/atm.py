"""The machine: a context holding whichever state is in charge."""

from __future__ import annotations

from .bank import Bank
from .dispenser import CashDispenser, Denomination
from .states import AuthenticatedState, CardInsertedState, DispensingState, IdleState


class ATM:
    """Card slot, keypad, cash box and a state machine tying them together."""

    def __init__(self, bank: Bank, dispenser: CashDispenser | None = None):
        self.bank = bank
        self.dispenser = dispenser or CashDispenser()

        self.card_account_number: str | None = None
        self.account = None
        self.last_dispensed: dict[Denomination, int] = {}

        self.idle_state = IdleState(self)
        self.card_inserted_state = CardInsertedState(self)
        self.authenticated_state = AuthenticatedState(self)
        self.dispensing_state = DispensingState(self)

        self.state = self.idle_state

    def set_state(self, state) -> None:
        self.state = state

    # -- what a customer can do -------------------------------------------

    def insert_card(self, account_number: str) -> str:
        return self.state.insert_card(account_number)

    def enter_pin(self, pin: str) -> str:
        return self.state.enter_pin(pin)

    def check_balance(self) -> int:
        return self.state.check_balance()

    def withdraw(self, amount: int) -> dict[Denomination, int]:
        return self.state.withdraw(amount)

    def deposit(self, amount: int) -> int:
        return self.state.deposit(amount)

    def transfer(self, target_account: str, amount: int) -> int:
        return self.state.transfer(target_account, amount)

    def collect_cash(self) -> dict[Denomination, int]:
        return self.state.collect_cash()

    def eject_card(self) -> str:
        return self.state.eject_card()

    # -- shared -----------------------------------------------------------

    def return_card(self) -> str:
        """Always available to the states. Clears every trace of the session."""
        self.card_account_number = None
        self.account = None
        self.last_dispensed = {}
        self.state = self.idle_state
        return "Card returned. Thank you."

    def status(self) -> str:
        return (
            f"State: {self.state} — {self.state.prompt}\n"
            f"Cash in machine: {self.dispenser.total} "
            f"({self.dispenser.describe(self.dispenser.inventory)})"
        )
