"""The turn loop that ties board, dice and players together."""

from __future__ import annotations

import random
from collections.abc import Iterable, Iterator

from ..model.board import Board
from ..model.dice import Dice
from ..model.jump import Jump
from ..model.player import MoveResult, Player
from .dice_strategy import DiceRollStrategy


class GameOver(Exception):
    """Raised when a turn is requested after somebody has already won."""


class SnakeLadderGame:
    """A full game.

    `turns()` yields one MoveResult per turn and stops when someone wins, so
    the game is driveable from a test without touching stdout. `play()` is the
    thin wrapper that prints those results for the CLI.
    """

    def __init__(
        self,
        jumps: Iterable[Jump],
        player_names: Iterable[str],
        dice_strategy: str | DiceRollStrategy = "fair",
        max_position: int = 100,
        start_position: int = 0,
        rng: random.Random | None = None,
        max_turns: int = 10_000,
    ):
        names = list(player_names)
        if not names:
            raise ValueError("A game needs at least one player")
        if len(set(names)) != len(names):
            raise ValueError("Player names must be unique")

        self.board = Board(jumps, size=max_position, start=start_position)
        self.board.validate()

        self.dice = Dice(dice_strategy, rng)
        self.players = [Player(self.board, name) for name in names]
        self.winner: Player | None = None

        # A crooked die on an unlucky board can in principle never land exactly
        # on the last square. Bounding the loop turns a hang into an error.
        self.max_turns = max_turns
        self._turn_index = 0

    @property
    def is_over(self) -> bool:
        return self.winner is not None

    def play_turn(self) -> MoveResult:
        """Play one turn for whoever is next, and return what happened."""
        if self.is_over:
            raise GameOver(f"{self.winner.name} already won this game")

        player = self.players[self._turn_index % len(self.players)]
        self._turn_index += 1

        result = player.move(self.dice.roll())
        if result.won:
            self.winner = player
        return result

    def turns(self) -> Iterator[MoveResult]:
        """Yield every turn until somebody wins."""
        for _ in range(self.max_turns):
            yield self.play_turn()
            if self.is_over:
                return

        raise GameOver(
            f"No winner after {self.max_turns} turns. "
            f"Check that the board is actually winnable with this die."
        )

    def play(self) -> Player:
        """Run the game to completion, printing each turn. Returns the winner."""
        for result in self.turns():
            print(result.render())
            print()

        return self.winner
