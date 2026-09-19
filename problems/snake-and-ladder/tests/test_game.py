"""The turn loop."""

import pytest
from snake_and_ladder.game_logic import GameOver, SnakeLadderGame
from snake_and_ladder.model import Ladder, Snake


def test_turns_alternate_between_players(scripted):
    game = SnakeLadderGame([], ["Alice", "Bob"], dice_strategy=scripted([1]))

    assert [game.play_turn().player for _ in range(4)] == ["Alice", "Bob", "Alice", "Bob"]


def test_the_game_ends_the_moment_someone_lands_on_the_last_square(scripted):
    # A tiny board makes the win reachable in one roll.
    game = SnakeLadderGame([], ["Alice", "Bob"], dice_strategy=scripted([5]), max_position=5)

    results = list(game.turns())

    assert len(results) == 1
    assert results[0].won
    assert game.winner.name == "Alice"


def test_playing_on_after_a_win_is_an_error(scripted):
    game = SnakeLadderGame([], ["Alice"], dice_strategy=scripted([5]), max_position=5)
    list(game.turns())

    with pytest.raises(GameOver, match="already won"):
        game.play_turn()


def test_a_game_nobody_can_win_gives_up_instead_of_hanging(scripted):
    # Always rolling 2 on a 5-square board means you sit on 4 forever: 4 + 2
    # overshoots, so every turn is skipped.
    game = SnakeLadderGame([], ["Alice"], dice_strategy=scripted([2]), max_position=5, max_turns=50)

    with pytest.raises(GameOver, match="No winner after 50 turns"):
        list(game.turns())


def test_a_chained_board_is_rejected_when_the_game_is_built():
    with pytest.raises(ValueError, match="both the end of one jump"):
        SnakeLadderGame([Ladder(4, 14), Snake(14, 2)], ["Alice"])


def test_players_need_unique_names():
    with pytest.raises(ValueError, match="unique"):
        SnakeLadderGame([], ["Alice", "Alice"])


def test_a_game_needs_at_least_one_player():
    with pytest.raises(ValueError, match="at least one player"):
        SnakeLadderGame([], [])
