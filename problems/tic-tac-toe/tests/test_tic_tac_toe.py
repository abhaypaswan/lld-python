"""Win detection, and a bot that must never lose."""

import random

import pytest

from tic_tac_toe import (
    BotPlayer,
    Cell,
    Game,
    GameStatus,
    MinimaxStrategy,
    RandomStrategy,
)
from tic_tac_toe.board import Board
from tic_tac_toe.game import GameOver
from tic_tac_toe.players import HumanPlayer


def play(game, *cells):
    for row, column in cells:
        game.play_turn(Cell(row, column))
    return game


# -- the board ------------------------------------------------------------


def test_a_fresh_board_is_empty():
    board = Board(3)

    assert len(board.free_cells()) == 9
    assert not board.is_full


def test_placing_reports_no_win_until_there_is_one():
    board = Board(3)

    assert board.place(Cell(0, 0), "X") is False
    assert board.place(Cell(0, 1), "X") is False
    assert board.place(Cell(0, 2), "X") is True


def test_a_full_column_wins():
    board = Board(3)
    assert board.place(Cell(0, 1), "X") is False
    assert board.place(Cell(1, 1), "X") is False
    assert board.place(Cell(2, 1), "X") is True


def test_the_main_diagonal_wins():
    board = Board(3)
    assert board.place(Cell(0, 0), "X") is False
    assert board.place(Cell(1, 1), "X") is False
    assert board.place(Cell(2, 2), "X") is True


def test_the_anti_diagonal_wins():
    board = Board(3)
    assert board.place(Cell(0, 2), "X") is False
    assert board.place(Cell(1, 1), "X") is False
    assert board.place(Cell(2, 0), "X") is True


def test_two_players_sharing_a_line_is_not_a_win():
    board = Board(3)
    board.place(Cell(0, 0), "X")
    board.place(Cell(0, 1), "O")

    assert board.place(Cell(0, 2), "X") is False


def test_a_taken_square_cannot_be_played_again():
    board = Board(3)
    board.place(Cell(1, 1), "X")

    with pytest.raises(ValueError, match="already taken by X"):
        board.place(Cell(1, 1), "O")


def test_a_square_off_the_board_is_rejected():
    with pytest.raises(ValueError, match="off a 3x3 board"):
        Board(3).place(Cell(3, 0), "X")


def test_a_board_must_be_at_least_three_squares_wide():
    with pytest.raises(ValueError, match="at least 3x3"):
        Board(2)


@pytest.mark.parametrize("size", [3, 4, 5, 8])
def test_win_detection_works_at_any_size(size):
    board = Board(size)

    for column in range(size - 1):
        assert board.place(Cell(0, column), "X") is False
    assert board.place(Cell(0, size - 1), "X") is True


def test_undo_takes_back_the_counters_too():
    """If undo only cleared the grid, minimax would see phantom wins."""
    board = Board(3)
    board.place(Cell(0, 0), "X")
    board.place(Cell(0, 1), "X")
    board.undo(Cell(0, 1))

    assert board.place(Cell(0, 2), "X") is False, "two Xs in a row is not a win"


def test_undoing_an_empty_square_is_an_error():
    with pytest.raises(ValueError, match="nothing to undo"):
        Board(3).undo(Cell(0, 0))


# -- the game -------------------------------------------------------------


@pytest.fixture
def game():
    return Game([BotPlayer("X"), BotPlayer("O")])


def test_players_alternate(game):
    assert game.current_player.symbol == "X"
    game.play_turn(Cell(0, 0))
    assert game.current_player.symbol == "O"


def test_a_won_game_reports_its_winner(game):
    play(game, (0, 0), (1, 0), (0, 1), (1, 1))
    result = game.play_turn(Cell(0, 2))

    assert result.status is GameStatus.WON
    assert game.winner.symbol == "X"


def test_a_full_board_with_no_line_is_a_draw(game):
    # X O X / X O O / O X X
    play(game, (0, 0), (0, 1), (0, 2), (1, 1), (1, 0), (1, 2), (2, 1), (2, 0))
    result = game.play_turn(Cell(2, 2))

    assert result.status is GameStatus.DRAWN
    assert game.winner is None


def test_playing_on_after_the_game_ends_is_an_error(game):
    play(game, (0, 0), (1, 0), (0, 1), (1, 1))
    game.play_turn(Cell(0, 2))

    with pytest.raises(GameOver, match="already won"):
        game.play_turn(Cell(2, 2))


def test_players_need_distinct_symbols():
    with pytest.raises(ValueError, match="distinct symbols"):
        Game([BotPlayer("X"), BotPlayer("X")])


def test_a_game_needs_two_players():
    with pytest.raises(ValueError, match="at least two players"):
        Game([BotPlayer("X")])


def test_a_symbol_is_a_single_character():
    with pytest.raises(ValueError, match="single character"):
        BotPlayer("XO")


def test_observers_see_every_move(game):
    seen = []
    game.subscribe(seen.append)

    play(game, (0, 0), (1, 1))

    assert len(seen) == 2


# -- the bots -------------------------------------------------------------


def test_a_random_bot_only_plays_free_squares():
    game = Game([BotPlayer("X", RandomStrategy(random.Random(1))),
                 BotPlayer("O", RandomStrategy(random.Random(2)))])

    game.play(show=False)

    assert game.is_over


def test_two_perfect_players_always_draw():
    for _ in range(3):
        game = Game([BotPlayer("X", MinimaxStrategy()), BotPlayer("O", MinimaxStrategy())])
        game.play(show=False)

        assert game.status is GameStatus.DRAWN, "tic tac toe is a solved draw"


@pytest.mark.parametrize("seed", range(8))
def test_a_perfect_player_never_loses_to_a_random_one(seed):
    game = Game([
        BotPlayer("X", RandomStrategy(random.Random(seed))),
        BotPlayer("O", MinimaxStrategy()),
    ])
    game.play(show=False)

    assert game.winner is None or game.winner.symbol == "O"


def test_a_perfect_player_takes_a_win_when_it_is_there():
    game = Game([BotPlayer("X", MinimaxStrategy()), BotPlayer("O", RandomStrategy())])
    # X has two in a row at (0,0) and (0,1); (0,2) wins now.
    play(game, (0, 0), (1, 0), (0, 1), (1, 1))

    result = game.play_turn()

    assert result.cell == Cell(0, 2)
    assert game.winner.symbol == "X"


def test_a_perfect_player_blocks_an_immediate_loss():
    game = Game([BotPlayer("X", RandomStrategy()), BotPlayer("O", MinimaxStrategy())])
    # X threatens (2,2) via the main diagonal.
    play(game, (0, 0), (0, 1), (1, 1))

    result = game.play_turn()

    assert result.cell == Cell(2, 2), "O must block the diagonal"


def test_a_perfect_player_prefers_the_faster_win():
    """Without depth in the score, a bot dawdles on a win it has already seen."""
    strategy = MinimaxStrategy()
    assert strategy._score_win(0) > strategy._score_win(4)


def test_alpha_beta_cuts_the_search_down():
    pruned = MinimaxStrategy()
    board = Board(3)
    board.place(Cell(0, 0), "X")

    pruned.choose(board, "O", "X")

    # A full 8-ply tree is 8! = 40,320 leaves. Pruning should be far under that.
    assert pruned.nodes_explored < 10_000


# -- the human player -----------------------------------------------------


def test_a_human_move_is_read_from_the_prompt():
    player = HumanPlayer("X", prompt=lambda _: "1 2")

    assert player.choose_move(Board(3), "O") == Cell(1, 2)


def test_a_human_is_asked_again_after_a_bad_answer(capsys):
    answers = iter(["nonsense", "9 9", "0 0"])
    player = HumanPlayer("X", prompt=lambda _: next(answers))

    assert player.choose_move(Board(3), "O") == Cell(0, 0)


def test_a_human_is_asked_again_for_a_taken_square(capsys):
    board = Board(3)
    board.place(Cell(0, 0), "O")
    answers = iter(["0 0", "1 1"])
    player = HumanPlayer("X", prompt=lambda _: next(answers))

    assert player.choose_move(board, "O") == Cell(1, 1)
