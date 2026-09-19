"""Snakes and ladders are the same shape: land here, end up there.

They are modelled as one base class with two subclasses rather than a single
class with a direction flag, because the two read differently in output and an
interviewer will almost always ask you to give them different behaviour later
(a snake that only bites on an odd roll, a ladder that can be used once).
"""

from __future__ import annotations


class Jump:
    """A one-way move between two squares."""

    #: Shown when a player lands on the start square.
    verb = "jumps"

    def __init__(self, start: int, end: int):
        if start == end:
            raise ValueError(f"A jump cannot start and end on the same square ({start})")
        self.start = start
        self.end = end

    @property
    def end_position(self) -> int:
        return self.end

    def describe(self) -> str:
        return f"{self.verb} from {self.start} to {self.end}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.start}, {self.end})"


class Ladder(Jump):
    """Carries a player up the board."""

    verb = "climbs a ladder"

    def __init__(self, start: int, end: int):
        if end < start:
            raise ValueError(f"A ladder must go up, but {start} -> {end} goes down")
        super().__init__(start, end)


class Snake(Jump):
    """Drops a player down the board."""

    verb = "slides down a snake"

    def __init__(self, start: int, end: int):
        if end > start:
            raise ValueError(f"A snake must go down, but {start} -> {end} goes up")
        super().__init__(start, end)
