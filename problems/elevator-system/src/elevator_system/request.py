"""The two kinds of request, which are genuinely different.

An **external** request is someone in a lobby pressing up or down. They have
stated a direction but not a destination, and any car in the bank could serve
them -- so it goes to the scheduler.

An **internal** request is someone inside a car pressing a floor button. They
have stated a destination but no direction, and only that car can serve it -- so
it goes straight to that car's stop list.

Collapsing them into one type is the most common mistake in this problem. It
throws away the direction on external requests, which is exactly the
information the LOOK algorithm needs to avoid picking someone up while
travelling the wrong way.
"""

from __future__ import annotations

from dataclasses import dataclass

from .elevator import Direction


@dataclass(frozen=True)
class ExternalRequest:
    """A hall call: a floor, and which way the person wants to go."""

    floor: int
    direction: Direction

    def __post_init__(self):
        if self.direction is Direction.IDLE:
            raise ValueError("A hall call must be up or down, not idle")

    def __str__(self) -> str:
        return f"floor {self.floor} going {self.direction}"


@dataclass(frozen=True)
class InternalRequest:
    """A car call: a destination pressed inside a specific elevator."""

    elevator_id: str
    floor: int

    def __str__(self) -> str:
        return f"{self.elevator_id} to floor {self.floor}"
