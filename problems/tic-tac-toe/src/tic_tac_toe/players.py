"""Players, and the strategies bots use to choose a move.

Two layers of Strategy sit here, and keeping them apart is the point:

- `Player` is *who* is moving. A human reads from a prompt; a bot computes.
- `MoveStrategy` is *how* a bot decides. Random, minimax, or anything else.

Folding them together would mean a class per (kind of player x difficulty)
combination. Apart, adding a "medium" bot is one strategy class.
"""

from __future__ import annotations

import random
from abc import ABC, abstractmethod
from collections.abc import Callable

from .board import Board, Cell


class Player(ABC):
    """Someone taking turns with a symbol."""

    def __init__(self, symbol: str, name: str = ""):
        if len(symbol) != 1:
            raise ValueError(f"A symbol must be a single character, got {symbol!r}")
        self.symbol = symbol
        self.name = name or symbol

    @abstractmethod
    def choose_move(self, board: Board, opponent_symbol: str) -> Cell:
        """Pick a free cell to play."""

    def __str__(self) -> str:
        return f"{self.name} ({self.symbol})"


class MoveStrategy(ABC):
    """How a bot picks its move."""

    name: str = "strategy"

    @abstractmethod
    def choose(self, board: Board, symbol: str, opponent_symbol: str) -> Cell:
        """Pick a free cell for `symbol`."""


class RandomStrategy(MoveStrategy):
    """Plays anywhere. The easy difficulty setting."""

    name = "random"

    def __init__(self, rng: random.Random | None = None):
        self._rng = rng or random.Random()

    def choose(self, board: Board, symbol: str, opponent_symbol: str) -> Cell:
        free = board.free_cells()
        if not free:
            raise ValueError("There are no free cells left")
        return self._rng.choice(free)


class MinimaxStrategy(MoveStrategy):
    """Plays perfectly. Never loses.

    Explores by placing a move, recursing, and undoing it -- which is why
    `Board.undo` exists. Copying the board at every node would be correct and
    considerably slower.

    Depth is folded into the score so the bot prefers a win in two moves over a
    win in four, and a loss in four over a loss in two. Without that, a bot that
    has already decided it will lose plays as though it does not matter, which
    looks like a bug to anyone watching.

    Alpha-beta pruning is what makes this viable past 3x3. Even so, `max_depth`
    exists because on larger boards the tree is too big regardless -- beyond it,
    the bot falls back to a positional heuristic.
    """

    name = "minimax"

    def __init__(self, max_depth: int = 9):
        self.max_depth = max_depth
        self.nodes_explored = 0

    def choose(self, board: Board, symbol: str, opponent_symbol: str) -> Cell:
        free = board.free_cells()
        if not free:
            raise ValueError("There are no free cells left")

        # An empty board has no distinguishable moves and the widest tree.
        if len(free) == board.size * board.size:
            centre = board.size // 2
            return Cell(centre, centre)

        self.nodes_explored = 0
        best_score = float("-inf")
        best_cell = free[0]

        for cell in free:
            won = board.place(cell, symbol)
            score = (
                self._score_win(0)
                if won
                else self._minimax(
                    board,
                    symbol,
                    opponent_symbol,
                    depth=1,
                    maximising=False,
                    alpha=float("-inf"),
                    beta=float("inf"),
                )
            )
            board.undo(cell)

            if score > best_score:
                best_score, best_cell = score, cell

        return best_cell

    def _score_win(self, depth: int) -> float:
        """A win is better the sooner it comes."""
        return 10.0 - depth

    def _minimax(self, board, symbol, opponent, depth, maximising, alpha, beta) -> float:
        self.nodes_explored += 1

        if board.is_full or depth >= self.max_depth:
            return 0.0

        mover = symbol if maximising else opponent
        best = float("-inf") if maximising else float("inf")

        for cell in board.free_cells():
            won = board.place(cell, mover)

            if won:
                score = self._score_win(depth) if maximising else -self._score_win(depth)
            else:
                score = self._minimax(
                    board, symbol, opponent, depth + 1, not maximising, alpha, beta
                )
            board.undo(cell)

            if maximising:
                best = max(best, score)
                alpha = max(alpha, best)
            else:
                best = min(best, score)
                beta = min(beta, best)

            if beta <= alpha:
                # This branch cannot change the decision above it.
                break

        return best


class BotPlayer(Player):
    """A player that delegates its choice to a strategy."""

    def __init__(self, symbol: str, strategy: MoveStrategy | None = None, name: str = ""):
        super().__init__(symbol, name or f"Bot-{symbol}")
        self.strategy = strategy or RandomStrategy()

    def choose_move(self, board: Board, opponent_symbol: str) -> Cell:
        return self.strategy.choose(board, self.symbol, opponent_symbol)


class HumanPlayer(Player):
    """A player whose move comes from outside.

    `prompt` is a callable rather than a hard-coded `input()` so the same class
    works at a terminal, in a test, and behind an HTTP handler.
    """

    def __init__(self, symbol: str, name: str = "", prompt: Callable[[str], str] | None = None):
        super().__init__(symbol, name)
        self.prompt = prompt or input

    def choose_move(self, board: Board, opponent_symbol: str) -> Cell:
        while True:
            raw = self.prompt(f"{self.name}, your move (row col): ")
            try:
                row, column = (int(part) for part in raw.replace(",", " ").split())
            except ValueError:
                print("  Enter two numbers, for example: 1 2")
                continue

            cell = Cell(row, column)
            if not board.is_valid(cell):
                print(f"  That is off a {board.size}x{board.size} board.")
            elif not board.is_free(cell):
                print("  That square is taken.")
            else:
                return cell
