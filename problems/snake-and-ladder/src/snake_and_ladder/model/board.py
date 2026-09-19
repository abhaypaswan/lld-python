"""The board owns the squares and the jumps sitting on them."""

from __future__ import annotations

from collections.abc import Iterable

from .jump import Jump, Ladder, Snake


class Board:
    """A board of `size` squares with snakes and ladders placed on it.

    The board validates its own layout on construction. That matters more than
    it looks: an interviewer will ask what happens when a ladder lands on the
    mouth of a snake, and the honest answer is that you should refuse to build
    that board rather than discover it mid-game.
    """

    def __init__(self, jumps: Iterable[Jump], size: int = 100, start: int = 0):
        if size <= start:
            raise ValueError(f"Board size {size} must be greater than the start square {start}")

        self.size = size
        self.start = start
        self._jumps: dict[int, Jump] = {}

        for jump in jumps:
            self._add(jump)

    def _add(self, jump: Jump) -> None:
        for square in (jump.start, jump.end):
            if not self.start <= square <= self.size:
                raise ValueError(f"{jump!r} is off the board (squares {self.start}-{self.size})")

        if jump.start == self.size:
            raise ValueError(f"{jump!r} starts on the winning square")

        if jump.start in self._jumps:
            raise ValueError(f"Square {jump.start} already has {self._jumps[jump.start]!r}")

        self._jumps[jump.start] = jump

    def validate(self) -> None:
        """Reject layouts where one jump feeds straight into another.

        Chaining is not illegal in every house rule, but the classic statement
        forbids it, and silently allowing it turns a single roll into an
        unbounded sequence of jumps.
        """
        landings = {jump.end for jump in self._jumps.values()}
        conflicts = sorted(landings & set(self._jumps))
        if conflicts:
            raise ValueError(
                f"Squares {conflicts} are both the end of one jump and the start of another"
            )

    def jump_at(self, position: int) -> Jump | None:
        """Return the snake or ladder starting at `position`, if there is one."""
        return self._jumps.get(position)

    @property
    def snakes(self) -> list[Snake]:
        return [j for j in self._jumps.values() if isinstance(j, Snake)]

    @property
    def ladders(self) -> list[Ladder]:
        return [j for j in self._jumps.values() if isinstance(j, Ladder)]
