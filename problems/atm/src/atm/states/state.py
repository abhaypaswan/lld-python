"""State pattern: what the machine will accept right now.

Same shape as the vending machine, and for the same reason -- but the stakes
are different. An ATM that lets you withdraw before authenticating is not a
quirk, it is a security hole. Making each state list only what it permits means
"can this action happen here?" is answered by which class is in charge, not by
a condition somebody might forget to write.
"""

from __future__ import annotations

from abc import ABC


class InvalidOperation(Exception):
    """The machine cannot do that from the state it is in."""


class ATMState(ABC):
    """One state. Everything is refused unless a subclass allows it."""

    name: str = "state"
    prompt: str = ""

    def __init__(self, atm):
        self.atm = atm

    def insert_card(self, account_number: str) -> str:
        raise InvalidOperation(f"Cannot accept a card right now. {self.prompt}")

    def enter_pin(self, pin: str) -> str:
        raise InvalidOperation(f"Not expecting a PIN right now. {self.prompt}")

    def check_balance(self) -> int:
        raise InvalidOperation(f"Cannot check a balance right now. {self.prompt}")

    def withdraw(self, amount: int) -> dict:
        raise InvalidOperation(f"Cannot withdraw right now. {self.prompt}")

    def deposit(self, amount: int) -> int:
        raise InvalidOperation(f"Cannot accept a deposit right now. {self.prompt}")

    def transfer(self, target_account: str, amount: int) -> int:
        raise InvalidOperation(f"Cannot transfer right now. {self.prompt}")

    def eject_card(self) -> str:
        raise InvalidOperation(f"There is no card to return. {self.prompt}")

    def __str__(self) -> str:
        return self.name
