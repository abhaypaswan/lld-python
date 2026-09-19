"""Runnable demo for Tic Tac Toe.

python3 src/main.py                       # perfect bot vs random bot
python3 src/main.py --human               # play against the perfect bot
python3 src/main.py --size 4 --x random --o random
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from tic_tac_toe import (  # noqa: E402
    BotPlayer,
    Game,
    HumanPlayer,
    MinimaxStrategy,
    RandomStrategy,
)


def build_player(symbol: str, kind: str, size: int, seed: int | None):
    if kind == "human":
        return HumanPlayer(symbol, name="You")
    if kind == "random":
        return BotPlayer(symbol, RandomStrategy(random.Random(seed)))

    # Minimax on a board larger than 3x3 has to be depth-limited; the full tree
    # for 4x4 is 16! nodes, which is not a thing you wait for.
    return BotPlayer(symbol, MinimaxStrategy(max_depth=9 if size == 3 else 4))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Play Tic Tac Toe.")
    parser.add_argument("--size", type=int, default=3, help="Board size (default 3).")
    parser.add_argument("--x", default="random", choices=["human", "random", "perfect"])
    parser.add_argument("--o", default="perfect", choices=["human", "random", "perfect"])
    parser.add_argument("--human", action="store_true", help="Shorthand for --x human.")
    parser.add_argument("--seed", type=int, help="Seed the random bots.")
    args = parser.parse_args(argv)

    if args.human:
        args.x = "human"

    players = [
        build_player("X", args.x, args.size, args.seed),
        build_player("O", args.o, args.size, args.seed),
    ]
    game = Game(players, size=args.size)

    print(f"{players[0]} ({args.x}) vs {players[1]} ({args.o}) on {args.size}x{args.size}\n")
    print(game.board.render())
    print()

    winner = game.play()

    print("-" * 30)
    print(f"{winner} wins." if winner else "Draw.")
    print(f"{len(game.history)} moves.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
