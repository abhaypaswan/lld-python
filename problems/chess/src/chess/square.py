"""A square, addressable as coordinates or as algebraic notation."""

from __future__ import annotations

from dataclasses import dataclass

FILES = "abcdefgh"


@dataclass(frozen=True)
class Square:
    """Row 0 is rank 8 (Black's back rank); row 7 is rank 1 (White's).

    Rows increase downward so the board prints the way a player sees it with
    White at the bottom, without the render function reversing anything. It is
    worth writing this down, because off-by-one and upside-down bugs in chess
    code almost all trace back to an unstated convention.
    """

    row: int
    column: int

    @classmethod
    def parse(cls, notation: str) -> Square:
        """`e4` -> Square(4, 4)."""
        text = notation.strip().lower()
        if len(text) != 2 or text[0] not in FILES or not text[1].isdigit():
            raise ValueError(f"{notation!r} is not a square, expected something like 'e4'")

        column = FILES.index(text[0])
        rank = int(text[1])
        if not 1 <= rank <= 8:
            raise ValueError(f"{notation!r} is off the board")

        return cls(8 - rank, column)

    @property
    def is_on_board(self) -> bool:
        return 0 <= self.row < 8 and 0 <= self.column < 8

    def offset(self, rows: int, columns: int) -> Square:
        return Square(self.row + rows, self.column + columns)

    @property
    def name(self) -> str:
        return f"{FILES[self.column]}{8 - self.row}"

    def __str__(self) -> str:
        return self.name
