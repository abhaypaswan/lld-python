"""Strategy pattern: how a die decides what it rolls.

The point of the pattern here is that `Dice` never learns what kind of die it
is holding. Adding a loaded die, a two-dice-summed die, or a scripted die for
tests means adding a class, not editing an if/else that every other roll has to
walk through.

Every strategy takes an optional `random.Random`. Passing a seeded one is what
makes a game reproducible, which is the only sane way to test a dice game.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod

FACES = (1, 2, 3, 4, 5, 6)


class DiceRollStrategy(ABC):
    """How one roll of the die is decided."""

    def __init__(self, rng: random.Random | None = None):
        # Falling back to the `random` module's shared generator keeps the
        # no-argument case feeling like plain `random.randint`.
        self._rng = rng or random.Random()

    @abstractmethod
    def roll(self) -> int:
        """Return a face value, 1 through 6."""


class FairDiceRollStrategy(DiceRollStrategy):
    """A normal die. Every face equally likely."""

    def roll(self) -> int:
        return self._rng.randint(1, 6)


class CrookedDiceRollStrategy(DiceRollStrategy):
    """A die weighted towards even numbers.

    `odd_probability` is the chance of getting an odd face at all. At the
    default of 0.2, four rolls in five come back even.
    """

    def __init__(self, rng: random.Random | None = None, odd_probability: float = 0.2):
        if not 0.0 <= odd_probability <= 1.0:
            raise ValueError(f"odd_probability must be between 0 and 1, got {odd_probability}")
        super().__init__(rng)
        self.odd_probability = odd_probability

    def roll(self) -> int:
        if self._rng.random() < self.odd_probability:
            return self._rng.choice([1, 3, 5])
        return self._rng.choice([2, 4, 6])


#: Name -> strategy class, so callers can say `Dice("crooked")` without
#: importing the class. Register a new die by adding one entry.
STRATEGIES: dict[str, type[DiceRollStrategy]] = {
    "fair": FairDiceRollStrategy,
    "crooked": CrookedDiceRollStrategy,
}


def get_dice_strategy(
    name: str, rng: random.Random | None = None
) -> DiceRollStrategy:
    """Build the named strategy, or explain which names exist."""
    try:
        strategy_class = STRATEGIES[name]
    except KeyError:
        known = ", ".join(sorted(STRATEGIES))
        raise ValueError(f"{name!r} is not a dice strategy. Try one of: {known}") from None
    return strategy_class(rng)
