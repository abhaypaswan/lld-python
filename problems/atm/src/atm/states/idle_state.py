"""No card in the slot."""

from __future__ import annotations

from .state import ATMState


class IdleState(ATMState):
    name = "idle"
    prompt = "Please insert your card."

    def insert_card(self, account_number: str) -> str:
        # The card is only read here. Nothing is checked against the bank until
        # a PIN arrives, so an unknown card looks identical to a known one --
        # which is what stops the machine being used to enumerate accounts.
        self.atm.card_account_number = account_number
        self.atm.set_state(self.atm.card_inserted_state)
        return "Card accepted. Please enter your PIN."
