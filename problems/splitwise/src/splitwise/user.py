"""A person in a group."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """Identified by `user_id`, which is what every balance is keyed on.

    Frozen and hashable so users can be dictionary keys directly, rather than
    every balance map being keyed on a string that has to be looked back up.
    """

    user_id: str
    name: str = ""
    email: str = ""

    def __post_init__(self):
        if not self.user_id.strip():
            raise ValueError("A user needs an id")
        if not self.name:
            object.__setattr__(self, "name", self.user_id)

    def __str__(self) -> str:
        return self.name


@dataclass
class Observer:
    """Anything that wants to hear about new expenses and settlements."""

    events: list = field(default_factory=list)

    def on_expense_added(self, expense) -> None:
        self.events.append(("expense", expense))

    def on_settlement(self, payer: User, payee: User, amount: int) -> None:
        self.events.append(("settlement", payer, payee, amount))
