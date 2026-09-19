"""The board is where the fiddly rules live, so it gets the most tests."""

import pytest

from snake_and_ladder.model import Board, Ladder, Snake


def test_jump_at_finds_the_jump_starting_on_a_square():
    board = Board([Ladder(4, 14), Snake(49, 11)])

    assert board.jump_at(4).end_position == 14
    assert board.jump_at(49).end_position == 11
    assert board.jump_at(5) is None


def test_ladders_and_snakes_are_kept_apart():
    board = Board([Ladder(4, 14), Ladder(9, 31), Snake(49, 11)])

    assert len(board.ladders) == 2
    assert len(board.snakes) == 1


def test_a_ladder_may_not_go_down():
    with pytest.raises(ValueError, match="must go up"):
        Ladder(40, 10)


def test_a_snake_may_not_go_up():
    with pytest.raises(ValueError, match="must go down"):
        Snake(10, 40)


def test_a_jump_may_not_start_and_end_on_the_same_square():
    with pytest.raises(ValueError, match="same square"):
        Ladder(10, 10)


def test_two_jumps_may_not_share_a_starting_square():
    with pytest.raises(ValueError, match="already has"):
        Board([Ladder(4, 14), Snake(4, 1)])


def test_a_jump_may_not_hang_off_the_board():
    with pytest.raises(ValueError, match="off the board"):
        Board([Ladder(95, 140)])


def test_a_jump_may_not_start_on_the_winning_square():
    with pytest.raises(ValueError, match="winning square"):
        Board([Snake(100, 20)])


def test_validate_rejects_a_ladder_feeding_into_a_snake():
    # Landing on 14 would send you up to 14 and then straight down to 2, which
    # the classic statement forbids.
    board = Board([Ladder(4, 14), Snake(14, 2)])

    with pytest.raises(ValueError, match="both the end of one jump"):
        board.validate()


def test_validate_accepts_a_board_with_no_chains():
    Board([Ladder(4, 14), Snake(49, 11), Ladder(21, 42)]).validate()
