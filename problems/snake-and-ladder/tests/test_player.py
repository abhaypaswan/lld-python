"""Movement rules, including the ones people get wrong in interviews."""

from snake_and_ladder.model import Board, Ladder, Player, Snake


def make_player(jumps=(), size=100, name="Alice"):
    return Player(Board(list(jumps), size=size), name)


def test_a_plain_move_just_advances():
    player = make_player()

    result = player.move(5)

    assert player.position == 5
    assert result.end == 5
    assert result.jump is None
    assert not result.skipped


def test_landing_on_a_ladder_carries_the_player_up():
    player = make_player([Ladder(4, 14)])

    result = player.move(4)

    assert player.position == 14
    assert result.jump.end_position == 14


def test_landing_on_a_snake_drops_the_player_down():
    player = make_player([Snake(10, 2)])
    player.position = 5

    result = player.move(5)

    assert player.position == 2
    assert result.jump.end_position == 2


def test_a_roll_that_would_overshoot_the_end_is_skipped():
    player = make_player(size=100)
    player.position = 98

    result = player.move(4)

    assert result.skipped
    assert player.position == 98, "an overshooting roll must not move the player at all"


def test_landing_exactly_on_the_last_square_wins():
    player = make_player(size=100)
    player.position = 96

    result = player.move(4)

    assert result.won
    assert player.has_won()


def test_a_jump_is_only_taken_on_the_square_it_starts_from():
    # Passing over a snake's mouth must not trigger it.
    player = make_player([Snake(10, 2)])
    player.position = 8

    player.move(4)

    assert player.position == 12
