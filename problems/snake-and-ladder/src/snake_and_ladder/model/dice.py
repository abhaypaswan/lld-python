"""The die itself, which delegates every roll to its strategy."""

from __future__ import annotations

import random

from ..game_logic.dice_strategy import DiceRollStrategy, get_dice_strategy


class Dice:
    """A single six-sided die.

    Accepts either a strategy name (`Dice("crooked")`) or a strategy instance,
    which is the hook tests use to feed in a scripted sequence of rolls.
    """

    def __init__(
        self,
        strategy: str | DiceRollStrategy = "fair",
        rng: random.Random | None = None,
    ):
        if isinstance(strategy, DiceRollStrategy):
            self.strategy = strategy
        else:
            self.strategy = get_dice_strategy(strategy, rng)

    def roll(self) -> int:
        return self.strategy.roll()
