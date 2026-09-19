"""Command pattern: a move knows how to apply itself and how to take itself back.

Undo is not a nice-to-have here. Deciding whether a move is legal means playing
it, asking whether your own king is now attacked, and unplaying it. That happens
for every candidate move in every position, so `undo` is on the hot path of the
rules themselves -- not just behind a menu item.

Everything needed to reverse a move is captured when it is made: the piece
taken, whether it was the piece's first move, the en passant square that was
available, the rook that moved during castling. Recomputing any of that
afterwards is impossible, because the position it referred to is gone.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .pieces import Piece
from .square import Square


class MoveType(Enum):
    NORMAL = "normal"
    CAPTURE = "capture"
    CASTLE_KINGSIDE = "castle-kingside"
    CASTLE_QUEENSIDE = "castle-queenside"
    EN_PASSANT = "en-passant"
    PROMOTION = "promotion"

    def __str__(self) -> str:
        return self.value


@dataclass
class Move:
    """One move, and everything needed to reverse it."""

    origin: Square
    target: Square
    piece: Piece
    move_type: MoveType = MoveType.NORMAL

    captured: Piece | None = None
    captured_square: Square | None = None
    promoted_to: Piece | None = None

    # State restored on undo.
    piece_had_moved: bool = field(default=False)
    previous_en_passant: Square | None = None
    rook: Piece | None = None
    rook_origin: Square | None = None
    rook_target: Square | None = None
    rook_had_moved: bool = False

    @property
    def is_capture(self) -> bool:
        return self.captured is not None

    def notation(self) -> str:
        if self.move_type is MoveType.CASTLE_KINGSIDE:
            return "O-O"
        if self.move_type is MoveType.CASTLE_QUEENSIDE:
            return "O-O-O"

        text = f"{self.piece.symbol if self.piece.symbol != 'P' else ''}{self.origin}"
        text += "x" if self.is_capture else "-"
        text += str(self.target)

        if self.promoted_to is not None:
            text += f"={self.promoted_to.symbol}"
        if self.move_type is MoveType.EN_PASSANT:
            text += " e.p."
        return text

    def __str__(self) -> str:
        return self.notation()
