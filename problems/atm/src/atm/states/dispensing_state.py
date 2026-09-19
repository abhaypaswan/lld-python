"""Notes are in the tray, waiting to be taken."""

from __future__ import annotations

from .state import ATMState


class DispensingState(ATMState):
    name = "dispensing"
    prompt = "Please take your cash."

    def collect_cash(self) -> dict:
        notes = self.atm.last_dispensed
        self.atm.last_dispensed = {}
        self.atm.set_state(self.atm.authenticated_state)
        return notes

    def check_balance(self) -> int:
        return self.atm.account.balance

    def eject_card(self) -> str:
        """Returning the card also releases any cash still sitting in the tray."""
        return self.atm.return_card()
