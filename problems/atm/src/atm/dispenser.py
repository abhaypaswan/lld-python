"""Chain of Responsibility: dispense an amount in notes.

Each link handles one denomination. It takes as many of its own notes as fit,
then passes the remainder down the chain. The 100 handler at the end either
finds the remainder is zero or the amount cannot be made at all.

This is the textbook chain, used the way the textbook means it: one request,
passed along, each handler doing the part it can.

The part the textbook does not cover is the one that matters here. The chain
must either dispense the whole amount or dispense nothing -- an ATM that hands
over 4,500 of a 5,000 withdrawal and then discovers it is out of notes has
stolen 500. So the chain plans against a copy of the inventory and only commits
once it knows the full amount is makeable.
"""

from __future__ import annotations

from enum import IntEnum


class InsufficientCash(Exception):
    """The machine cannot make this amount from the notes it holds."""


class Denomination(IntEnum):
    """Note values, largest first when sorted in reverse."""

    HUNDRED = 100
    TWO_HUNDRED = 200
    FIVE_HUNDRED = 500
    TWO_THOUSAND = 2000

    def __str__(self) -> str:
        return str(self.value)


class DenominationHandler:
    """One link: hands out notes of a single value, then delegates."""

    def __init__(self, denomination: Denomination, next_handler: DenominationHandler | None = None):
        self.denomination = denomination
        self.next_handler = next_handler

    def set_next(self, handler: DenominationHandler) -> DenominationHandler:
        self.next_handler = handler
        return handler

    def plan(self, amount: int, inventory: dict[Denomination, int]) -> dict[Denomination, int]:
        """Work out which notes to use, without taking any.

        Greedy: take as many of this note as fit and as we hold. Greedy is
        correct for any canonical set of denominations, which 100/200/500/2000
        is. It is not correct in general -- see the note in the README.
        """
        value = int(self.denomination)
        wanted = min(amount // value, inventory.get(self.denomination, 0))

        plan = {self.denomination: wanted} if wanted else {}
        remaining = amount - wanted * value

        if remaining == 0:
            return plan

        if self.next_handler is None:
            raise InsufficientCash(
                f"Cannot make {amount} from the notes in this machine ({remaining} left over)"
            )

        return {**plan, **self.next_handler.plan(remaining, inventory)}


class CashDispenser:
    """The cash box, and the handler chain in front of it."""

    def __init__(self, inventory: dict[Denomination, int] | None = None):
        self.inventory: dict[Denomination, int] = dict(inventory or {})
        self._head = self._build_chain()

    @staticmethod
    def _build_chain() -> DenominationHandler:
        handlers = [
            DenominationHandler(denomination) for denomination in sorted(Denomination, reverse=True)
        ]
        for current, following in zip(handlers, handlers[1:], strict=False):
            current.set_next(following)
        return handlers[0]

    @property
    def total(self) -> int:
        return sum(int(note) * count for note, count in self.inventory.items())

    def load(self, **notes: int) -> None:
        """Refill, e.g. `load(two_thousand=10, five_hundred=20)`."""
        for name, count in notes.items():
            denomination = Denomination[name.upper()]
            self.inventory[denomination] = self.inventory.get(denomination, 0) + count

    def can_dispense(self, amount: int) -> bool:
        try:
            self.plan(amount)
        except (InsufficientCash, ValueError):
            return False
        return True

    def plan(self, amount: int) -> dict[Denomination, int]:
        """Which notes would be used, without taking them."""
        if amount <= 0:
            raise ValueError(f"Amount must be positive, got {amount}")

        smallest = min(Denomination)
        if amount % int(smallest) != 0:
            raise ValueError(f"{amount} cannot be paid in notes; the smallest note is {smallest}")
        if amount > self.total:
            raise InsufficientCash(f"This machine holds {self.total}, less than {amount}")

        return self._head.plan(amount, self.inventory)

    def dispense(self, amount: int) -> dict[Denomination, int]:
        """Take the notes out. Either the full amount, or nothing at all."""
        plan = self.plan(amount)

        # Only now, once the whole amount is known to be makeable, does the
        # real inventory change. Everything above this line was a rehearsal.
        for denomination, count in plan.items():
            self.inventory[denomination] -= count

        return plan

    def describe(self, plan: dict[Denomination, int]) -> str:
        return ", ".join(
            f"{count} x {denomination}"
            for denomination, count in sorted(plan.items(), reverse=True)
            if count
        )
