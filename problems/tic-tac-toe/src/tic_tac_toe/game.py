"""The turn loop, and the result of each move."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from enum import Enum

from .board import Board, Cell
from .players import Player


class GameStatus(Enum):
    IN_PROGRESS = "in-progress"
    WON = "won"
    DRAWN = "drawn"

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class MoveResult:
    """What one turn did. Returned rather than printed, so tests can assert."""

    player: Player
    cell: Cell
    status: GameStatus
    winner: Player | None = None

    def render(self) -> str:
        line = f"{self.player} plays {self.cell}"
        if self.status is GameStatus.WON:
            line += f"\n{self.winner} wins!"
        elif self.status is GameStatus.DRAWN:
            line += "\nDraw."
        return line


class GameOver(Exception):
    """A move was requested after the game finished."""


class Game:
    """Alternates between players until someone wins or the board fills."""

    def __init__(self, players: Iterable[Player], size: int = 3):
        self.players = list(players)
        if len(self.players) < 2:
            raise ValueError("A game needs at least two players")

        symbols = [player.symbol for player in self.players]
        if len(set(symbols)) != len(symbols):
            raise ValueError(f"Players need distinct symbols, got {symbols}")

        self.board = Board(size)
        self.status = GameStatus.IN_PROGRESS
        self.winner: Player | None = None
        self.history: list[MoveResult] = []
        self._turn = 0
        self._observers: list = []

    def subscribe(self, observer) -> None:
        self._observers.append(observer)

    @property
    def current_player(self) -> Player:
        return self.players[self._turn % len(self.players)]

    @property
    def is_over(self) -> bool:
        return self.status is not GameStatus.IN_PROGRESS

    def play_turn(self, cell: Cell | None = None) -> MoveResult:
        """Play one turn. Pass `cell` to place a specific move."""
        if self.is_over:
            raise GameOver(f"This game is already {self.status}")

        player = self.current_player
        if cell is None:
            opponent = self.players[(self._turn + 1) % len(self.players)]
            cell = player.choose_move(self.board, opponent.symbol)

        won = self.board.place(cell, player.symbol)

        if won:
            self.status = GameStatus.WON
            self.winner = player
        elif self.board.is_full:
            self.status = GameStatus.DRAWN

        result = MoveResult(player, cell, self.status, self.winner)
        self.history.append(result)
        self._turn += 1

        for observer in self._observers:
            observer(result)
        return result

    def turns(self) -> Iterator[MoveResult]:
        while not self.is_over:
            yield self.play_turn()

    def play(self, show: bool = True) -> Player | None:
        """Run to completion. Returns the winner, or None on a draw."""
        for result in self.turns():
            if show:
                print(result.render())
                print(self.board.render())
                print()
        return self.winner
