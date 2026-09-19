"""The pieces, and how each one moves.

Movement is the piece's own responsibility. `Board` never asks what kind of
piece it is holding -- it asks the piece where it could go. That is Strategy
expressed through the type system: adding a fairy piece is a new class and no
edit anywhere else.

The sliding pieces (queen, rook, bishop) share one walk that differs only in
which directions it follows, so that walk lives in a base class and each
subclass supplies its directions. Template Method, and it is why those three
classes are four lines each.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from .square import Square


class Color(Enum):
    WHITE = "white"
    BLACK = "black"

    @property
    def opponent(self) -> Color:
        return Color.BLACK if self is Color.WHITE else Color.WHITE

    @property
    def forward(self) -> int:
        """Which way this colour's pawns advance, in rows."""
        return -1 if self is Color.WHITE else 1

    @property
    def back_rank(self) -> int:
        return 7 if self is Color.WHITE else 0

    @property
    def promotion_rank(self) -> int:
        return 0 if self is Color.WHITE else 7

    def __str__(self) -> str:
        return self.value


class Piece(ABC):
    """A piece of a colour, which knows where it could move from a square."""

    symbol: str = "?"
    value: int = 0

    def __init__(self, color: Color):
        self.color = color
        #: Castling and the pawn double-step both depend on whether a piece has
        #: moved before. Storing it on the piece means Move.undo has to restore
        #: it -- which is exactly the kind of thing that breaks silently, so
        #: there are tests for it.
        self.has_moved = False

    @abstractmethod
    def candidate_moves(self, board, origin: Square) -> list[Square]:
        """Squares this piece could move to, ignoring whether the king is safe.

        These are *pseudo-legal*: they respect how the piece moves and what is
        in the way, but not whether making the move leaves your own king in
        check. That second filter belongs to the board, because it needs to
        look at the whole position.
        """

    def attacks(self, board, origin: Square) -> list[Square]:
        """Squares this piece attacks. Differs from movement only for pawns."""
        return self.candidate_moves(board, origin)

    @property
    def letter(self) -> str:
        return self.symbol.upper() if self.color is Color.WHITE else self.symbol.lower()

    def __str__(self) -> str:
        return f"{self.color} {type(self).__name__.lower()}"

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.color})"


class _SlidingPiece(Piece):
    """Walks outward along fixed directions until blocked."""

    directions: tuple[tuple[int, int], ...] = ()

    def candidate_moves(self, board, origin: Square) -> list[Square]:
        moves = []

        for row_step, column_step in self.directions:
            square = origin.offset(row_step, column_step)
            while square.is_on_board:
                occupant = board.piece_at(square)
                if occupant is None:
                    moves.append(square)
                else:
                    # A piece blocks the ray. We can take an enemy, never a
                    # friend, and either way we stop here.
                    if occupant.color is not self.color:
                        moves.append(square)
                    break
                square = square.offset(row_step, column_step)

        return moves


class _SteppingPiece(Piece):
    """Moves a fixed set of single steps."""

    steps: tuple[tuple[int, int], ...] = ()

    def candidate_moves(self, board, origin: Square) -> list[Square]:
        moves = []

        for row_step, column_step in self.steps:
            square = origin.offset(row_step, column_step)
            if not square.is_on_board:
                continue
            occupant = board.piece_at(square)
            if occupant is None or occupant.color is not self.color:
                moves.append(square)

        return moves


class Rook(_SlidingPiece):
    symbol = "R"
    value = 5
    directions = ((-1, 0), (1, 0), (0, -1), (0, 1))


class Bishop(_SlidingPiece):
    symbol = "B"
    value = 3
    directions = ((-1, -1), (-1, 1), (1, -1), (1, 1))


class Queen(_SlidingPiece):
    symbol = "Q"
    value = 9
    directions = Rook.directions + Bishop.directions


class Knight(_SteppingPiece):
    symbol = "N"
    value = 3
    steps = ((-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1))


class King(_SteppingPiece):
    symbol = "K"
    value = 0  # Never captured, so material value is meaningless.
    steps = ((-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1))

    def candidate_moves(self, board, origin: Square) -> list[Square]:
        return super().candidate_moves(board, origin) + board.castling_targets(self, origin)

    def attacks(self, board, origin: Square) -> list[Square]:
        """Castling is a move, not an attack.

        Including it here would make `attacks` recursive -- working out whether
        a king may castle requires knowing which squares the enemy attacks,
        which would require working out whether the enemy king may castle.
        """
        return super().candidate_moves(board, origin)


class Pawn(Piece):
    """The awkward one, and the reason `attacks` exists separately.

    A pawn moves straight forward but captures diagonally. Every other piece
    moves and attacks identically, so it is easy to write a check detector that
    treats the two as the same thing -- and then a pawn on e5 "attacks" e6 and
    a king on e6 is reported as in check when it is not.
    """

    symbol = "P"
    value = 1

    def candidate_moves(self, board, origin: Square) -> list[Square]:
        moves = []
        forward = self.color.forward

        one_ahead = origin.offset(forward, 0)
        if one_ahead.is_on_board and board.piece_at(one_ahead) is None:
            moves.append(one_ahead)

            two_ahead = origin.offset(2 * forward, 0)
            if not self.has_moved and two_ahead.is_on_board and board.piece_at(two_ahead) is None:
                moves.append(two_ahead)

        for column_step in (-1, 1):
            target = origin.offset(forward, column_step)
            if not target.is_on_board:
                continue

            occupant = board.piece_at(target)
            if occupant is not None and occupant.color is not self.color:
                moves.append(target)
            elif occupant is None and target == board.en_passant_target:
                # En passant: the only capture where the captured piece is not
                # on the destination square.
                moves.append(target)

        return moves

    def attacks(self, board, origin: Square) -> list[Square]:
        """Only the diagonals. Never the forward push."""
        forward = self.color.forward
        return [
            origin.offset(forward, step)
            for step in (-1, 1)
            if origin.offset(forward, step).is_on_board
        ]
