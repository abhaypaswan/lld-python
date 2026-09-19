"""A die that rolls exactly what the test tells it to."""

import pytest

from snake_and_ladder.game_logic import DiceRollStrategy


class ScriptedDice(DiceRollStrategy):
    """Rolls through a fixed list, then repeats the last value forever.

    Repeating rather than raising at the end keeps tests readable: you script
    only the rolls you care about and let the rest fall where they may.
    """

    def __init__(self, rolls):
        super().__init__()
        self.rolls = list(rolls)
        if not self.rolls:
            raise ValueError("ScriptedDice needs at least one roll")
        self.index = 0

    def roll(self) -> int:
        value = self.rolls[min(self.index, len(self.rolls) - 1)]
        self.index += 1
        return value


@pytest.fixture
def scripted():
    return ScriptedDice
