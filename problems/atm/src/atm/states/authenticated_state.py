"""Signed in. Everything is permitted here and nowhere else."""

from __future__ import annotations

from ..dispenser import InsufficientCash
from .state import ATMState


class AuthenticatedState(ATMState):
    name = "authenticated"
    prompt = "Choose a transaction."

    def check_balance(self) -> int:
        return self.atm.account.balance

    def withdraw(self, amount: int) -> dict:
        account = self.atm.account

        # Check the notes BEFORE touching the balance. Debiting first and then
        # discovering the machine cannot make the amount means the customer has
        # paid for cash they never received.
        plan = self.atm.dispenser.plan(amount)

        account.debit(amount)

        try:
            self.atm.dispenser.dispense(amount)
        except InsufficientCash:
            # Only reachable if another transaction drained the box between the
            # plan and the dispense. Put the money back rather than keeping it.
            account.credit(amount)
            account.withdrawn_today -= amount
            raise

        self.atm.set_state(self.atm.dispensing_state)
        self.atm.last_dispensed = plan
        return plan

    def deposit(self, amount: int) -> int:
        return self.atm.account.credit(amount)

    def transfer(self, target_account: str, amount: int) -> int:
        self.atm.bank.transfer(self.atm.account, target_account, amount)
        return self.atm.account.balance

    def eject_card(self) -> str:
        return self.atm.return_card()
