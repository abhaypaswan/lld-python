"""State pattern: the machine's behaviour is its current state object.

Every state implements the same five actions. What changes between them is what
each action *does* -- and crucially, which ones are refused. `select` in the
Idle state is an error; `select` in HasMoney is the main path.

The alternative, an `if self.status == ...` at the top of every method, means
adding a sixth state (a card-payment state, a maintenance state) forces you to
revisit every method and hope you found them all. Here, adding a state is
adding a class.
"""

from __future__ import annotations

from abc import ABC

from ..model.coin import Coin
from ..model.item import Item


class InvalidAction(Exception):
    """The machine cannot do that from the state it is currently in."""


class VendingMachineState(ABC):  # noqa: B024 - see below
    """One state of the machine.

    Every action defaults to refusing, with a message that says what the
    machine *is* waiting for. A state then overrides only the actions it
    actually supports, which keeps each state short and makes the refusals
    informative rather than generic.
    """

    name: str = "state"
    #: What a user sees when they ask the machine what it wants.
    prompt: str = ""

    #: No method here is abstract, which is the design and not an oversight.
    #: Every action defaults to refusing, so a concrete state only has to write
    #: the ones it permits. Marking them abstract would force each state to
    #: reimplement every refusal it does not want to change.

    def __init__(self, machine):
        self.machine = machine

    def insert_coin(self, coin: Coin) -> str:
        raise InvalidAction(f"Cannot insert coins right now. {self.prompt}")

    def select_item(self, code: str) -> str:
        raise InvalidAction(f"Cannot select an item right now. {self.prompt}")

    def dispense(self) -> Item:
        raise InvalidAction(f"Nothing to dispense right now. {self.prompt}")

    def refund(self) -> list[Coin]:
        raise InvalidAction(f"Nothing to refund right now. {self.prompt}")

    def __str__(self) -> str:
        return self.name
