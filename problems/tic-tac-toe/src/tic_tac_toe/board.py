"""The board, and the counters that make a win check O(1)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Cell:
    row: int
    column: int

    def __str__(self) -> str:
        return f"({self.row},{self.column})"


class Board:
    """An N x N grid that knows whether the last move won, without scanning.

    The naive win check walks the row, the column and both diagonals after
    every move: O(n) per move, and easy to get subtly wrong on the diagonals.

    Instead, each symbol keeps a running count per row, per column and for each
    diagonal. Placing a symbol bumps at most four counters, and a win is any
    counter reaching n. That is O(1) per move and the same code works for
    3x3 and 19x19 -- which is the property that makes the generalisation
    follow-up a non-event.
    """

    def __init__(self, size: int = 3):
        if size < 3:
            raise ValueError(f"A board must be at least 3x3, got {size}x{size}")

        self.size = size
        self._grid: list[list[str | None]] = [[None] * size for _ in range(size)]
        self._moves = 0

        # symbol -> counts. Diagonals are single integers, not lists.
        self._rows: dict[str, list[int]] = {}
        self._columns: dict[str, list[int]] = {}
        self._diagonal: dict[str, int] = {}
        self._anti_diagonal: dict[str, int] = {}

    # -- reading ----------------------------------------------------------

    def __getitem__(self, cell: Cell) -> str | None:
        return self._grid[cell.row][cell.column]

    def is_valid(self, cell: Cell) -> bool:
        return 0 <= cell.row < self.size and 0 <= cell.column < self.size

    def is_free(self, cell: Cell) -> bool:
        return self.is_valid(cell) and self._grid[cell.row][cell.column] is None

    def free_cells(self) -> list[Cell]:
        return [
            Cell(row, column)
            for row in range(self.size)
            for column in range(self.size)
            if self._grid[row][column] is None
        ]

    @property
    def is_full(self) -> bool:
        return self._moves == self.size * self.size

    # -- writing ----------------------------------------------------------

    def place(self, cell: Cell, symbol: str) -> bool:
        """Place a symbol. Returns whether that move won the game."""
        if not self.is_valid(cell):
            raise ValueError(f"{cell} is off a {self.size}x{self.size} board")
        if self._grid[cell.row][cell.column] is not None:
            raise ValueError(f"{cell} is already taken by {self._grid[cell.row][cell.column]}")

        self._grid[cell.row][cell.column] = symbol
        self._moves += 1
        return self._bump(cell, symbol, +1)

    def undo(self, cell: Cell) -> None:
        """Take a move back, counters and all.

        Needed by minimax, which explores by playing a move and unplaying it.
        Copying the whole board per node would work and would be far slower.
        """
        symbol = self._grid[cell.row][cell.column]
        if symbol is None:
            raise ValueError(f"{cell} is empty, there is nothing to undo")

        self._grid[cell.row][cell.column] = None
        self._moves -= 1
        self._bump(cell, symbol, -1)

    def _bump(self, cell: Cell, symbol: str, delta: int) -> bool:
        """Adjust the four counters this cell belongs to. Returns True on a win."""
        size = self.size
        rows = self._rows.setdefault(symbol, [0] * size)
        columns = self._columns.setdefault(symbol, [0] * size)

        rows[cell.row] += delta
        columns[cell.column] += delta

        if cell.row == cell.column:
            self._diagonal[symbol] = self._diagonal.get(symbol, 0) + delta
        if cell.row + cell.column == size - 1:
            self._anti_diagonal[symbol] = self._anti_diagonal.get(symbol, 0) + delta

        return (
            rows[cell.row] == size
            or columns[cell.column] == size
            or self._diagonal.get(symbol, 0) == size
            or self._anti_diagonal.get(symbol, 0) == size
        )

    # -- display ----------------------------------------------------------

    def render(self) -> str:
        divider = "\n" + "---+" * (self.size - 1) + "---\n"
        return divider.join("|".join(f" {value or ' '} " for value in row) for row in self._grid)

    def __str__(self) -> str:
        return self.render()
