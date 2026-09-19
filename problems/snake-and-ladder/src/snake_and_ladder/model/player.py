"""A player, and the record of what one turn did to them."""

from __future__ import annotations

from dataclasses import dataclass

from .board import Board
from .jump import Jump


@dataclass(frozen=True)
class MoveResult:
    """What happened on a single turn.

    Returning this instead of printing is the difference between a game you can
    test and a game you can only watch. The game loop renders it; the tests
    assert on it.
    """

    player: str
    dice_roll: int
    start: int
    end: int
    jump: Jump | None = None
    skipped: bool = False
    won: bool = False

    def render(self) -> str:
        lines = [f"{self.player} rolled {self.dice_roll}"]

        if self.skipped:
            lines.append(f"{self.player} would overshoot the last square, so the turn is skipped.")
        else:
            if self.jump is not None:
                lines.append(f"({self.jump.describe()})")
            lines.append(f"{self.player} is now on square {self.end}")

        if self.won:
            lines.append(f"{self.player} has won the game!")

        return "\n".join(lines)


class Player:
    """One player's position on the board."""

    def __init__(self, board: Board, name: str):
        if not name.strip():
            raise ValueError("A player needs a name")
        self.board = board
        self.name = name
        self.position = board.start

    def move(self, dice_roll: int) -> MoveResult:
        """Advance by `dice_roll`, then follow any jump we land on."""
        start = self.position
        target = start + dice_roll

        # Classic rule: you must land exactly on the final square, so a roll
        # that would take you past it does not move you at all.
        if target > self.board.size:
            return MoveResult(
                player=self.name,
                dice_roll=dice_roll,
                start=start,
                end=start,
                skipped=True,
            )

        jump = self.board.jump_at(target)
        if jump is not None:
            target = jump.end_position

        self.position = target
        return MoveResult(
            player=self.name,
            dice_roll=dice_roll,
            start=start,
            end=target,
            jump=jump,
            won=self.has_won(),
        )

    def has_won(self) -> bool:
        return self.position == self.board.size

    def __repr__(self) -> str:
        return f"Player({self.name!r}, position={self.position})"
