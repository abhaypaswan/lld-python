"""The game: turns, and how a position ends."""

from __future__ import annotations

from enum import Enum

from .board import Board
from .move import Move
from .pieces import Color, Piece, Queen
from .square import Square


class GameStatus(Enum):
    IN_PROGRESS = "in-progress"
    CHECK = "check"
    CHECKMATE = "checkmate"
    STALEMATE = "stalemate"
    DRAW_FIFTY_MOVE = "draw-fifty-move"
    DRAW_INSUFFICIENT_MATERIAL = "draw-insufficient-material"

    def __str__(self) -> str:
        return self.value


class IllegalMove(Exception):
    """The move is not legal in this position."""


class Game:
    """A game of chess between White and Black."""

    def __init__(self, board: Board | None = None, to_move: Color = Color.WHITE):
        self.board = board if board is not None else Board()
        self.to_move = to_move
        self.winner: Color | None = None
        #: Half-moves since the last capture or pawn move, for the fifty-move rule.
        self.halfmove_clock = 0
        self._observers: list = []

    def subscribe(self, observer) -> None:
        self._observers.append(observer)

    # -- status -----------------------------------------------------------

    @property
    def status(self) -> GameStatus:
        """Read from the position, never stored.

        Caching it means every code path that changes the board has to remember
        to refresh it, and one that forgets produces a game that thinks it is
        still running after checkmate.
        """
        has_moves = bool(self.board.legal_moves(self.to_move))
        in_check = self.board.is_in_check(self.to_move)

        if not has_moves:
            # No legal move plus check is checkmate; no legal move without
            # check is stalemate, and a draw. Conflating them is the classic
            # chess-engine bug.
            return GameStatus.CHECKMATE if in_check else GameStatus.STALEMATE

        if self.halfmove_clock >= 100:
            return GameStatus.DRAW_FIFTY_MOVE
        if self._insufficient_material():
            return GameStatus.DRAW_INSUFFICIENT_MATERIAL

        return GameStatus.CHECK if in_check else GameStatus.IN_PROGRESS

    @property
    def is_over(self) -> bool:
        return self.status in {
            GameStatus.CHECKMATE,
            GameStatus.STALEMATE,
            GameStatus.DRAW_FIFTY_MOVE,
            GameStatus.DRAW_INSUFFICIENT_MATERIAL,
        }

    def _insufficient_material(self) -> bool:
        """King versus king, or king and a single minor piece."""
        pieces = [
            piece
            for color in Color
            for _, piece in self.board.squares_with(color)
            if piece.symbol != "K"
        ]
        if not pieces:
            return True
        return len(pieces) == 1 and pieces[0].symbol in {"B", "N"}

    # -- moving -----------------------------------------------------------

    def legal_moves(self) -> list[Move]:
        return self.board.legal_moves(self.to_move)

    def move(self, origin: str | Square, target: str | Square, promote_to=Queen) -> Move:
        """Play a move, given as squares or as algebraic notation."""
        if self.is_over:
            raise IllegalMove(f"This game is already {self.status}")

        origin = Square.parse(origin) if isinstance(origin, str) else origin
        target = Square.parse(target) if isinstance(target, str) else target

        piece = self.board.piece_at(origin)
        if piece is None:
            raise IllegalMove(f"There is no piece on {origin}")
        if piece.color is not self.to_move:
            raise IllegalMove(f"It is {self.to_move}'s turn, and {origin} holds a {piece}")

        for candidate in self.board.legal_moves_from(origin):
            if candidate.target == target:
                break
        else:
            reason = (
                " (your king is in check)"
                if self.board.is_in_check(self.to_move)
                else ""
            )
            raise IllegalMove(f"{piece} cannot move from {origin} to {target}{reason}")

        is_reset = candidate.is_capture or piece.symbol == "P"
        candidate.halfmove_clock_before = self.halfmove_clock

        self.board.apply(candidate, promote_to)
        self.halfmove_clock = 0 if is_reset else self.halfmove_clock + 1
        self.to_move = self.to_move.opponent

        if self.status is GameStatus.CHECKMATE:
            self.winner = self.to_move.opponent

        for observer in self._observers:
            observer(candidate, self)
        return candidate

    def undo(self) -> Move | None:
        move = self.board.undo()
        if move is None:
            return None

        self.to_move = self.to_move.opponent
        self.winner = None
        self.halfmove_clock = getattr(move, "halfmove_clock_before", 0)
        return move

    # -- display ----------------------------------------------------------

    def material(self, color: Color) -> int:
        return sum(piece.value for _, piece in self.board.squares_with(color))

    def render(self) -> str:
        lines = [self.board.render(), "", f"{self.to_move} to move — {self.status}"]
        if self.winner is not None:
            lines.append(f"{self.winner} wins.")
        return "\n".join(lines)
