"""Movement, legality, and the endings people get wrong."""

import pytest

from chess import (
    Bishop,
    Board,
    Color,
    Game,
    GameStatus,
    King,
    Knight,
    MoveType,
    Pawn,
    Queen,
    Rook,
    Square,
)
from chess.game import IllegalMove


def empty_board(**placements):
    """`empty_board(e1=King(Color.WHITE))` builds a position from scratch."""
    board = Board(empty=True)
    for notation, piece in placements.items():
        board.place(piece, Square.parse(notation))
    return board


def targets(board, square):
    return {str(move.target) for move in board.legal_moves_from(Square.parse(square))}


# -- squares --------------------------------------------------------------


def test_algebraic_notation_round_trips():
    for notation in ("a1", "e4", "h8", "d5"):
        assert Square.parse(notation).name == notation


def test_a1_is_the_bottom_left():
    assert Square.parse("a1") == Square(7, 0)
    assert Square.parse("h8") == Square(0, 7)


def test_nonsense_notation_is_rejected():
    with pytest.raises(ValueError, match="not a square"):
        Square.parse("z9")


def test_a_rank_off_the_board_is_rejected():
    with pytest.raises(ValueError, match="off the board"):
        Square.parse("e9")


# -- how the pieces move --------------------------------------------------


def test_a_rook_slides_along_rank_and_file():
    board = empty_board(e1=King(Color.WHITE), d4=Rook(Color.WHITE), e8=King(Color.BLACK))

    assert len(targets(board, "d4")) == 14


def test_a_rook_stops_at_a_friendly_piece():
    board = empty_board(
        e1=King(Color.WHITE), d4=Rook(Color.WHITE), d6=Pawn(Color.WHITE), e8=King(Color.BLACK)
    )

    assert "d6" not in targets(board, "d4")
    assert "d5" in targets(board, "d4")
    assert "d7" not in targets(board, "d4")


def test_a_rook_captures_an_enemy_and_stops():
    board = empty_board(
        e1=King(Color.WHITE), d4=Rook(Color.WHITE), d6=Pawn(Color.BLACK), e8=King(Color.BLACK)
    )

    assert "d6" in targets(board, "d4")
    assert "d7" not in targets(board, "d4")


def test_a_bishop_moves_diagonally():
    board = empty_board(e1=King(Color.WHITE), d4=Bishop(Color.WHITE), e8=King(Color.BLACK))

    assert len(targets(board, "d4")) == 13


def test_a_queen_covers_both():
    board = empty_board(e1=King(Color.WHITE), d4=Queen(Color.WHITE), h8=King(Color.BLACK))

    assert len(targets(board, "d4")) == 27


def test_a_knight_jumps_over_pieces():
    board = Board()

    assert targets(board, "b1") == {"a3", "c3"}


def test_a_knight_in_the_centre_has_eight_squares():
    board = empty_board(e1=King(Color.WHITE), d4=Knight(Color.WHITE), h8=King(Color.BLACK))

    assert len(targets(board, "d4")) == 8


def test_a_knight_in_the_corner_has_two():
    board = empty_board(e1=King(Color.WHITE), a1=Knight(Color.WHITE), h8=King(Color.BLACK))

    assert len(targets(board, "a1")) == 2


# -- pawns ----------------------------------------------------------------


def test_a_pawn_may_step_one_or_two_from_its_start():
    assert targets(Board(), "e2") == {"e3", "e4"}


def test_a_pawn_may_only_step_one_after_moving():
    game = Game()
    game.move("e2", "e3")
    game.move("e7", "e6")

    assert targets(game.board, "e3") == {"e4"}


def test_a_pawn_cannot_move_through_a_piece():
    board = empty_board(
        e1=King(Color.WHITE), e2=Pawn(Color.WHITE), e3=Pawn(Color.BLACK), a8=King(Color.BLACK)
    )

    assert targets(board, "e2") == set()


def test_a_pawn_captures_diagonally_but_not_forward():
    board = empty_board(
        e1=King(Color.WHITE), e4=Pawn(Color.WHITE), d5=Pawn(Color.BLACK),
        e5=Pawn(Color.BLACK), a8=King(Color.BLACK),
    )

    assert targets(board, "e4") == {"d5"}, "e5 is blocked, d5 is a capture"


def test_a_pawn_does_not_attack_the_square_in_front_of_it():
    """The bug this prevents: a king reported in check by the pawn ahead of it."""
    board = empty_board(e5=Pawn(Color.WHITE), e6=King(Color.BLACK), e1=King(Color.WHITE))

    assert not board.is_in_check(Color.BLACK)
    assert board.is_attacked(Square.parse("d6"), Color.WHITE)


def test_a_pawn_promotes_on_the_last_rank():
    board = empty_board(e1=King(Color.WHITE), b7=Pawn(Color.WHITE), h8=King(Color.BLACK))
    game = Game(board)

    move = game.move("b7", "b8")

    assert move.move_type is MoveType.PROMOTION
    assert isinstance(game.board.piece_at(Square.parse("b8")), Queen)


def test_a_pawn_can_promote_to_something_other_than_a_queen():
    board = empty_board(e1=King(Color.WHITE), b7=Pawn(Color.WHITE), h8=King(Color.BLACK))
    game = Game(board)

    game.move("b7", "b8", promote_to=Knight)

    assert isinstance(game.board.piece_at(Square.parse("b8")), Knight)


# -- en passant -----------------------------------------------------------


def test_en_passant_is_available_right_after_a_double_step():
    board = empty_board(
        e1=King(Color.WHITE), e5=Pawn(Color.WHITE), d7=Pawn(Color.BLACK), h8=King(Color.BLACK)
    )
    game = Game(board, to_move=Color.BLACK)
    game.move("d7", "d5")

    assert "d6" in targets(game.board, "e5")


def test_en_passant_removes_the_pawn_beside_you_not_in_front():
    board = empty_board(
        e1=King(Color.WHITE), e5=Pawn(Color.WHITE), d7=Pawn(Color.BLACK), h8=King(Color.BLACK)
    )
    game = Game(board, to_move=Color.BLACK)
    game.move("d7", "d5")

    move = game.move("e5", "d6")

    assert move.move_type is MoveType.EN_PASSANT
    assert game.board.piece_at(Square.parse("d5")) is None, "the captured pawn was on d5"
    assert game.board.piece_at(Square.parse("d6")) is not None


def test_en_passant_expires_after_one_move():
    board = empty_board(
        e1=King(Color.WHITE), e5=Pawn(Color.WHITE), d7=Pawn(Color.BLACK),
        a7=Pawn(Color.BLACK), h8=King(Color.BLACK),
    )
    game = Game(board, to_move=Color.BLACK)
    game.move("d7", "d5")
    game.move("e1", "e2")
    game.move("a7", "a6")

    assert "d6" not in targets(game.board, "e5"), "the window is one move wide"


def test_undoing_en_passant_puts_the_pawn_back():
    board = empty_board(
        e1=King(Color.WHITE), e5=Pawn(Color.WHITE), d7=Pawn(Color.BLACK), h8=King(Color.BLACK)
    )
    game = Game(board, to_move=Color.BLACK)
    game.move("d7", "d5")
    game.move("e5", "d6")

    game.undo()

    assert isinstance(game.board.piece_at(Square.parse("d5")), Pawn)
    assert game.board.piece_at(Square.parse("d6")) is None


# -- castling -------------------------------------------------------------


def castling_position(**extra):
    return empty_board(
        e1=King(Color.WHITE), a1=Rook(Color.WHITE), h1=Rook(Color.WHITE),
        e8=King(Color.BLACK), **extra,
    )


def test_a_king_may_castle_on_both_sides():
    assert {"g1", "c1"} <= targets(castling_position(), "e1")


def test_castling_moves_the_rook_too():
    game = Game(castling_position())

    game.move("e1", "g1")

    assert isinstance(game.board.piece_at(Square.parse("f1")), Rook)
    assert game.board.piece_at(Square.parse("h1")) is None


def test_a_king_that_has_moved_may_not_castle():
    board = castling_position()
    board.piece_at(Square.parse("e1")).has_moved = True

    assert "g1" not in targets(board, "e1")


def test_a_rook_that_has_moved_may_not_castle():
    board = castling_position()
    board.piece_at(Square.parse("h1")).has_moved = True

    assert "g1" not in targets(board, "e1")
    assert "c1" in targets(board, "e1"), "the other rook is still eligible"


def test_a_king_may_not_castle_through_a_piece():
    board = castling_position(f1=Bishop(Color.WHITE))

    assert "g1" not in targets(board, "e1")


def test_a_king_in_check_may_not_castle():
    board = castling_position(e5=Rook(Color.BLACK))

    assert "g1" not in targets(board, "e1")


def test_a_king_may_not_castle_through_an_attacked_square():
    """The condition people forget: through, not merely into."""
    board = castling_position(f5=Rook(Color.BLACK))

    assert "g1" not in targets(board, "e1"), "f1 is attacked, and the king passes over it"


def test_a_king_may_not_castle_into_an_attacked_square():
    board = castling_position(g5=Rook(Color.BLACK))

    assert "g1" not in targets(board, "e1")


def test_queenside_castling_is_allowed_over_an_attacked_b_file():
    """b1 is not on the king's path, so an attack there does not prevent it."""
    board = castling_position(b5=Rook(Color.BLACK))

    assert "c1" in targets(board, "e1")


def test_undoing_castling_restores_both_pieces():
    game = Game(castling_position())
    game.move("e1", "g1")

    game.undo()

    assert isinstance(game.board.piece_at(Square.parse("e1")), King)
    assert isinstance(game.board.piece_at(Square.parse("h1")), Rook)
    assert game.board.piece_at(Square.parse("e1")).has_moved is False


# -- check and legality ---------------------------------------------------


def test_a_king_is_in_check_when_attacked():
    board = empty_board(e1=King(Color.WHITE), e8=Rook(Color.BLACK), a8=King(Color.BLACK))

    assert board.is_in_check(Color.WHITE)


def test_a_pinned_rook_may_only_move_along_the_pin():
    board = empty_board(
        e1=King(Color.WHITE), e2=Rook(Color.WHITE), e8=Rook(Color.BLACK), a8=King(Color.BLACK)
    )

    assert targets(board, "e2") == {"e3", "e4", "e5", "e6", "e7", "e8"}, (
        "it may slide up and down the file, including taking the pinning rook"
    )


def test_a_pinned_bishop_cannot_move_at_all():
    # Pinned along a file, and a bishop has no move along a file.
    board = empty_board(
        e1=King(Color.WHITE), e2=Bishop(Color.WHITE), e8=Rook(Color.BLACK), a8=King(Color.BLACK)
    )

    assert targets(board, "e2") == set()


def test_a_king_may_not_move_into_check():
    board = empty_board(e1=King(Color.WHITE), d8=Rook(Color.BLACK), a8=King(Color.BLACK))

    assert "d1" not in targets(board, "e1")
    assert "d2" not in targets(board, "e1")


def test_in_check_only_moves_that_answer_it_are_legal():
    board = empty_board(
        e1=King(Color.WHITE), a2=Rook(Color.WHITE), e8=Rook(Color.BLACK), h8=King(Color.BLACK)
    )
    game = Game(board)

    for move in game.legal_moves():
        assert str(move.origin) in {"e1", "a2"}


def test_checking_legality_leaves_the_board_untouched():
    """_is_safe plays and unplays every candidate; a leak here is invisible."""
    board = Board()
    before = board.render()

    board.legal_moves(Color.WHITE)

    assert board.render() == before
    assert board.history == []


# -- endings --------------------------------------------------------------


def test_fools_mate():
    game = Game()
    for origin, target in (("f2", "f3"), ("e7", "e5"), ("g2", "g4"), ("d8", "h4")):
        game.move(origin, target)

    assert game.status is GameStatus.CHECKMATE
    assert game.winner is Color.BLACK


def test_scholars_mate():
    game = Game()
    for origin, target in (
        ("e2", "e4"), ("e7", "e5"), ("f1", "c4"), ("b8", "c6"),
        ("d1", "h5"), ("g8", "f6"), ("h5", "f7"),
    ):
        game.move(origin, target)

    assert game.status is GameStatus.CHECKMATE
    assert game.winner is Color.WHITE


def test_stalemate_is_not_checkmate():
    """No legal move, but not in check. It is a draw, and nobody wins."""
    board = empty_board(a8=King(Color.BLACK), c7=Queen(Color.WHITE), h1=King(Color.WHITE))
    game = Game(board, to_move=Color.BLACK)

    assert game.status is GameStatus.STALEMATE
    assert game.winner is None
    assert not game.board.is_in_check(Color.BLACK)


def test_king_against_king_is_a_draw():
    game = Game(empty_board(e1=King(Color.WHITE), e8=King(Color.BLACK)))

    assert game.status is GameStatus.DRAW_INSUFFICIENT_MATERIAL


def test_king_and_bishop_against_king_is_a_draw():
    game = Game(empty_board(e1=King(Color.WHITE), c1=Bishop(Color.WHITE), e8=King(Color.BLACK)))

    assert game.status is GameStatus.DRAW_INSUFFICIENT_MATERIAL


def test_king_and_rook_against_king_is_not_a_draw():
    game = Game(empty_board(e1=King(Color.WHITE), a1=Rook(Color.WHITE), e8=King(Color.BLACK)))

    assert game.status is not GameStatus.DRAW_INSUFFICIENT_MATERIAL


def test_a_game_cannot_continue_after_checkmate():
    game = Game()
    for origin, target in (("f2", "f3"), ("e7", "e5"), ("g2", "g4"), ("d8", "h4")):
        game.move(origin, target)

    with pytest.raises(IllegalMove, match="already checkmate"):
        game.move("e1", "f2")


# -- turns and errors -----------------------------------------------------


def test_white_moves_first():
    assert Game().to_move is Color.WHITE


def test_you_cannot_move_your_opponents_piece():
    with pytest.raises(IllegalMove, match="white's turn"):
        Game().move("e7", "e5")


def test_you_cannot_move_from_an_empty_square():
    with pytest.raises(IllegalMove, match="no piece on e4"):
        Game().move("e4", "e5")


def test_an_illegal_destination_is_refused():
    with pytest.raises(IllegalMove, match="cannot move"):
        Game().move("e2", "e5")


def test_undo_restores_the_position_and_the_turn():
    game = Game()
    before = game.board.render()
    game.move("e2", "e4")

    game.undo()

    assert game.board.render() == before
    assert game.to_move is Color.WHITE


def test_undo_on_a_fresh_game_does_nothing():
    assert Game().undo() is None


def test_observers_see_every_move():
    game = Game()
    seen = []
    game.subscribe(lambda move, g: seen.append(move))

    game.move("e2", "e4")

    assert len(seen) == 1


# -- move counts ----------------------------------------------------------


def test_the_opening_position_has_twenty_legal_moves():
    """Perft(1). A wrong number here means move generation is broken."""
    assert len(Board().legal_moves(Color.WHITE)) == 20


def test_perft_two():
    """Perft(2) = 400. Catches asymmetries between the two colours."""
    board = Board()
    total = 0

    for move in board.legal_moves(Color.WHITE):
        board.apply(move)
        total += len(board.legal_moves(Color.BLACK))
        board.undo()

    assert total == 400


def test_perft_three():
    """Perft(3) = 8902. This one fails loudly if undo does not fully reverse."""
    board = Board()
    total = 0

    for first in board.legal_moves(Color.WHITE):
        board.apply(first)
        for second in board.legal_moves(Color.BLACK):
            board.apply(second)
            total += len(board.legal_moves(Color.WHITE))
            board.undo()
        board.undo()

    assert total == 8902
