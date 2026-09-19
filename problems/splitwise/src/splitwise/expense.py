"""One expense: who paid, how much, and who it is shared between."""

from __future__ import annotations

import itertools
from collections.abc import Sequence
from dataclasses import dataclass, field

from .splits import EqualSplit, SplitStrategy
from .user import User

_expense_numbers = itertools.count(1)


@dataclass
class Expense:
    """A payment by one person on behalf of several.

    Shares are computed once at construction and stored. Recomputing them on
    every read would let a strategy mutated afterwards silently rewrite
    history -- and a ledger whose past changes is not a ledger.
    """

    payer: User
    amount: int
    participants: Sequence[User]
    strategy: SplitStrategy = field(default_factory=EqualSplit)
    description: str = ""
    expense_id: str = ""
    shares: dict[User, int] = field(init=False, default_factory=dict)

    def __post_init__(self):
        if self.amount <= 0:
            raise ValueError(f"An expense must be positive, got {self.amount}")

        self.participants = list(self.participants)
        if self.payer not in self.participants:
            # A payer who is not a participant paid entirely on others' behalf,
            # which is legitimate -- someone covering a bill they had no part in.
            pass

        if not self.expense_id:
            self.expense_id = f"E-{next(_expense_numbers):04d}"

        self.shares = self.strategy.split(self.amount, self.participants)

    def balance_deltas(self) -> dict[User, int]:
        """Net effect on each person's balance.

        Positive means the group owes them; negative means they owe the group.
        The payer is credited the whole amount and then debited their own
        share, which is what makes a payer who is also a participant come out
        owed only the others' portions.
        """
        deltas: dict[User, int] = {}
        for user, share in self.shares.items():
            deltas[user] = deltas.get(user, 0) - share

        deltas[self.payer] = deltas.get(self.payer, 0) + self.amount
        return {user: delta for user, delta in deltas.items() if delta}

    def __str__(self) -> str:
        what = self.description or "expense"
        return f"{self.expense_id}: {self.payer} paid {self.amount} for {what}"
