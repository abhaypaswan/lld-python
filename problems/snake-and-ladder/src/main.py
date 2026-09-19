"""Runnable demo for the Snake and Ladder design.

Run it from this problem's directory:

    python3 src/main.py
    python3 src/main.py --players Alice Bob --dice crooked --seed 7

Passing --seed makes a game reproducible, which is handy when you want to show
someone the same sequence of rolls twice.
"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# Let the script run directly without anyone having to set PYTHONPATH first.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from snake_and_ladder.game_logic import SnakeLadderGame  # noqa: E402
from snake_and_ladder.model import Ladder, Snake  # noqa: E402

# A standard board. Nothing here chains into anything else, which Board.validate
# checks for you on construction.
DEFAULT_JUMPS = [
    Ladder(1, 38),
    Ladder(4, 14),
    Ladder(9, 31),
    Ladder(21, 42),
    Ladder(28, 84),
    Ladder(36, 44),
    Ladder(51, 67),
    Ladder(71, 91),
    Ladder(80, 100),
    Snake(98, 78),
    Snake(95, 75),
    Snake(93, 73),
    Snake(87, 24),
    Snake(64, 60),
    Snake(62, 19),
    Snake(56, 53),
    Snake(49, 11),
    Snake(48, 26),
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Play a game of Snake and Ladder.")
    parser.add_argument(
        "--players",
        nargs="+",
        metavar="NAME",
        help="Player names. Prompts for them if you leave this off.",
    )
    parser.add_argument(
        "--dice",
        default="fair",
        choices=["fair", "crooked"],
        help="Which die to play with (default: fair).",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Seed the random number generator so the game replays identically.",
    )
    return parser.parse_args(argv)


DEFAULT_PLAYERS = ["Alice", "Bob"]


def prompt_for_players() -> list[str]:
    """Ask who is playing, falling back to two players when nobody can answer.

    Piped or redirected stdin means there is no one at the keyboard -- CI, or a
    `python3 src/main.py < /dev/null`. Prompting there hangs forever, so the
    demo just plays itself instead.
    """
    if not sys.stdin.isatty():
        print(f"(no terminal attached, playing {' vs '.join(DEFAULT_PLAYERS)})")
        return list(DEFAULT_PLAYERS)

    count = int(input("How many players are playing? "))
    return [input(f"Enter player {i + 1} name: ").strip() for i in range(count)]


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    players = args.players or prompt_for_players()

    game = SnakeLadderGame(
        jumps=DEFAULT_JUMPS,
        player_names=players,
        dice_strategy=args.dice,
        rng=random.Random(args.seed) if args.seed is not None else None,
    )

    print()
    winner = game.play()
    print("Final positions: " + ", ".join(f"{p.name}={p.position}" for p in game.players))
    return 0 if winner else 1


if __name__ == "__main__":
    raise SystemExit(main())
