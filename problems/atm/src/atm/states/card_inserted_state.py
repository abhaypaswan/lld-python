"""Card in, waiting for a PIN."""

from __future__ import annotations

from ..bank import AuthenticationFailed
from .state import ATMState


class CardInsertedState(ATMState):
    name = "card-inserted"
    prompt = "Please enter your PIN."

    def enter_pin(self, pin: str) -> str:
        try:
            account = self.atm.bank.authenticate(self.atm.card_account_number, pin)
        except AuthenticationFailed:
            # A blocked or unknown card is returned; a merely wrong PIN can be
            # tried again. The bank decides which, and it is what raised.
            account = self.atm.bank.accounts.get(self.atm.card_account_number)
            if account is None or account.blocked:
                self.atm.return_card()
            raise

        self.atm.account = account
        self.atm.set_state(self.atm.authenticated_state)
        return f"Welcome. Balance: {account.balance}."

    def eject_card(self) -> str:
        return self.atm.return_card()
