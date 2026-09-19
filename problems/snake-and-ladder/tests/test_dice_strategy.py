"""The dice strategies, pinned down with a seeded generator."""

import random

import pytest

from snake_and_ladder.game_logic import (
    CrookedDiceRollStrategy,
    FairDiceRollStrategy,
    get_dice_strategy,
)
from snake_and_ladder.model import Dice


def test_a_fair_die_only_ever_shows_one_through_six():
    die = FairDiceRollStrategy(random.Random(1))

    assert {die.roll() for _ in range(500)} == {1, 2, 3, 4, 5, 6}


def test_a_crooked_die_mostly_rolls_even():
    die = CrookedDiceRollStrategy(random.Random(1), odd_probability=0.2)

    rolls = [die.roll() for _ in range(2000)]
    even_share = sum(1 for r in rolls if r % 2 == 0) / len(rolls)

    assert 0.75 < even_share < 0.85


def test_a_crooked_die_still_rolls_odd_sometimes():
    die = CrookedDiceRollStrategy(random.Random(1))

    assert any(die.roll() % 2 for _ in range(200))


def test_odd_probability_has_to_be_a_probability():
    with pytest.raises(ValueError, match="between 0 and 1"):
        CrookedDiceRollStrategy(odd_probability=1.5)


def test_an_unknown_strategy_name_lists_the_known_ones():
    with pytest.raises(ValueError, match="fair, crooked|crooked, fair"):
        get_dice_strategy("loaded")


def test_the_same_seed_replays_the_same_game():
    first = [Dice("fair", random.Random(42)).roll() for _ in range(10)]
    second = [Dice("fair", random.Random(42)).roll() for _ in range(10)]

    assert first == second


def test_dice_accepts_a_strategy_instance_directly():
    die = Dice(FairDiceRollStrategy(random.Random(3)))

    assert 1 <= die.roll() <= 6
