"""The board: placement, move generation, and the legality filter."""

from __future__ import annotations

from .move import Move, MoveType
from .pieces import Bishop, Color, King, Knight, Pawn, Piece, Queen, Rook
from .square import Square


class Board:
    """An 8x8 position, plus the rules that depend on the whole position.

    The division of labour is the point of the design: a piece knows how it
    moves, and the board knows whether moving it is allowed. A piece cannot
    answer the second question -- "does this leave my king in check?" needs the
    whole position, not one piece's geometry.
    """

    def __init__(self, empty: bool = False):
        self._squares: list[list[Piece | None]] = [[None] * 8 for _ in range(8)]
        #: The square a pawn could capture onto by en passant, this move only.
        self.en_passant_target: Square | None = None
        self.history: list[Move] = []

        if not empty:
            self.set_up()

    # -- placement --------------------------------------------------------

    def set_up(self) -> None:
        back = [Rook, Knight, Bishop, Queen, King, Bishop, Knight, Rook]

        for column, piece_class in enumerate(back):
            self.place(piece_class(Color.BLACK), Square(0, column))
            self.place(Pawn(Color.BLACK), Square(1, column))
            self.place(Pawn(Color.WHITE), Square(6, column))
            self.place(piece_class(Color.WHITE), Square(7, column))

    def place(self, piece: Piece | None, square: Square) -> None:
        if not square.is_on_board:
            raise ValueError(f"{square} is off the board")
        self._squares[square.row][square.column] = piece

    def piece_at(self, square: Square) -> Piece | None:
        if not square.is_on_board:
            return None
        return self._squares[square.row][square.column]

    def squares_with(self, color: Color) -> list[tuple[Square, Piece]]:
        return [
            (Square(row, column), piece)
            for row in range(8)
            for column in range(8)
            if (piece := self._squares[row][column]) is not None and piece.color is color
        ]

    def find_king(self, color: Color) -> Square | None:
        for square, piece in self.squares_with(color):
            if isinstance(piece, King):
                return square
        return None

    # -- attacks and check ------------------------------------------------

    def is_attacked(self, square: Square, by: Color) -> bool:
        """Whether `by` attacks `square`.

        Uses `attacks`, not `candidate_moves`. For every piece but the pawn
        they are the same; for the pawn they are emphatically not, and using
        the wrong one puts kings in check from pawns directly in front of them.
        """
        return any(square in piece.attacks(self, origin) for origin, piece in self.squares_with(by))

    def is_in_check(self, color: Color) -> bool:
        king_square = self.find_king(color)
        return king_square is not None and self.is_attacked(king_square, color.opponent)

    # -- move generation --------------------------------------------------

    def legal_moves(self, color: Color) -> list[Move]:
        """Every move `color` may actually play."""
        return [
            move
            for origin, piece in self.squares_with(color)
            for target in piece.candidate_moves(self, origin)
            if (move := self._build_move(piece, origin, target)) and self._is_safe(move)
        ]

    def legal_moves_from(self, origin: Square) -> list[Move]:
        piece = self.piece_at(origin)
        if piece is None:
            return []

        return [
            move
            for target in piece.candidate_moves(self, origin)
            if (move := self._build_move(piece, origin, target)) and self._is_safe(move)
        ]

    def _is_safe(self, move: Move) -> bool:
        """Play it, ask whether our own king is attacked, take it back.

        This is the only way to answer the question correctly. Trying to reason
        about pins and discovered checks without making the move means
        reimplementing move generation a second time, in a way that has to
        agree with the first.
        """
        color = move.piece.color
        # apply() fills in a default promotion piece. Checking legality must not
        # be what decides what a pawn promotes to, so that choice is put back
        # exactly as it was found.
        promoted_to = move.promoted_to

        self.apply(move)
        safe = not self.is_in_check(color)
        self.undo()

        move.promoted_to = promoted_to
        return safe

    def _build_move(self, piece: Piece, origin: Square, target: Square) -> Move | None:
        captured = self.piece_at(target)
        captured_square = target if captured else None
        move_type = MoveType.CAPTURE if captured else MoveType.NORMAL

        if isinstance(piece, Pawn):
            if target == self.en_passant_target and captured is None:
                move_type = MoveType.EN_PASSANT
                captured_square = Square(origin.row, target.column)
                captured = self.piece_at(captured_square)
            elif target.row == piece.color.promotion_rank:
                move_type = MoveType.PROMOTION

        move = Move(origin, target, piece, move_type, captured, captured_square)

        if isinstance(piece, King) and abs(target.column - origin.column) == 2:
            kingside = target.column > origin.column
            move.move_type = MoveType.CASTLE_KINGSIDE if kingside else MoveType.CASTLE_QUEENSIDE
            move.rook_origin = Square(origin.row, 7 if kingside else 0)
            move.rook_target = Square(origin.row, 5 if kingside else 3)
            move.rook = self.piece_at(move.rook_origin)
            if move.rook is None:
                return None

        return move

    # -- castling ---------------------------------------------------------

    def castling_targets(self, king: King, origin: Square) -> list[Square]:
        """Castling squares available to this king right now.

        Four conditions, and the third is the one people forget: the king may
        not pass *through* an attacked square, not merely end on a safe one.
        """
        if king.has_moved or self.is_in_check(king.color):
            return []
        if origin != Square(king.color.back_rank, 4):
            return []

        targets = []
        for rook_column, empty_columns, path_columns, target_column in (
            (7, (5, 6), (5, 6), 6),
            (0, (1, 2, 3), (2, 3), 2),
        ):
            rook = self.piece_at(Square(origin.row, rook_column))
            if not isinstance(rook, Rook) or rook.color is not king.color or rook.has_moved:
                continue
            if any(self.piece_at(Square(origin.row, c)) is not None for c in empty_columns):
                continue
            if any(
                self.is_attacked(Square(origin.row, c), king.color.opponent) for c in path_columns
            ):
                continue

            targets.append(Square(origin.row, target_column))

        return targets

    # -- applying and undoing ---------------------------------------------

    def apply(self, move: Move, promote_to: type[Piece] = Queen) -> None:
        move.previous_en_passant = self.en_passant_target
        move.piece_had_moved = move.piece.has_moved

        if move.captured is not None and move.captured_square is not None:
            self.place(None, move.captured_square)

        self.place(None, move.origin)
        self.place(move.piece, move.target)
        move.piece.has_moved = True

        if move.move_type is MoveType.PROMOTION:
            if move.promoted_to is None:
                move.promoted_to = promote_to(move.piece.color)
                move.promoted_to.has_moved = True
            self.place(move.promoted_to, move.target)

        if move.rook is not None:
            move.rook_had_moved = move.rook.has_moved
            self.place(None, move.rook_origin)
            self.place(move.rook, move.rook_target)
            move.rook.has_moved = True

        # A double pawn push is the only thing that creates an en passant
        # target, and it lasts exactly one move.
        if isinstance(move.piece, Pawn) and abs(move.target.row - move.origin.row) == 2:
            self.en_passant_target = Square(
                (move.origin.row + move.target.row) // 2, move.origin.column
            )
        else:
            self.en_passant_target = None

        self.history.append(move)

    def undo(self) -> Move | None:
        if not self.history:
            return None

        move = self.history.pop()

        self.place(move.piece, move.origin)
        self.place(None, move.target)
        move.piece.has_moved = move.piece_had_moved

        if move.captured is not None and move.captured_square is not None:
            self.place(move.captured, move.captured_square)

        if move.rook is not None:
            self.place(move.rook, move.rook_origin)
            self.place(None, move.rook_target)
            move.rook.has_moved = move.rook_had_moved

        self.en_passant_target = move.previous_en_passant
        return move

    # -- display ----------------------------------------------------------

    def render(self) -> str:
        lines = []
        for row in range(8):
            cells = " ".join(
                (piece.letter if (piece := self._squares[row][column]) else ".")
                for column in range(8)
            )
            lines.append(f"{8 - row} | {cells}")
        lines.append("  +" + "-" * 17)
        lines.append("    a b c d e f g h")
        return "\n".join(lines)

    def __str__(self) -> str:
        return self.render()
