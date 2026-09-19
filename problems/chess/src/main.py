"""Runnable demo for the chess design.

    python3 src/main.py                 # replay a short game
    python3 src/main.py --interactive   # play both sides
    python3 src/main.py --perft 3       # count positions, to check move generation
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from chess import Board, Color, Game  # noqa: E402
from chess.game import IllegalMove  # noqa: E402

# Scholar's mate, with a castle thrown in so the demo exercises it.
GAME = [
    ("e2", "e4", None),
    ("e7", "e5", None),
    ("f1", "c4", None),
    ("b8", "c6", None),
    ("g1", "f3", None),
    ("g8", "f6", None),
    ("e1", "g1", "White castles kingside"),
    ("f8", "c5", None),
    ("f3", "g5", None),
    ("e8", "g8", "Black castles kingside"),
    ("g5", "f7", "a fork on the rook and queen"),
]


def perft(board: Board, depth: int, color: Color) -> int:
    """Count leaf positions at `depth`. The standard move-generation check."""
    if depth == 0:
        return 1

    total = 0
    for move in board.legal_moves(color):
        board.apply(move)
        total += perft(board, depth - 1, color.opponent)
        board.undo()
    return total


def run_perft(depth: int) -> int:
    known = {1: 20, 2: 400, 3: 8_902, 4: 197_281}

    print("Counting positions from the opening. Known-correct values in brackets.\n")
    for d in range(1, depth + 1):
        count = perft(Board(), d, Color.WHITE)
        expected = known.get(d)
        mark = "" if expected is None else (" ok" if count == expected else "  MISMATCH")
        print(f"  perft({d}) = {count:>9}  [{expected if expected else '?'}]{mark}")
    return 0


def interactive(game: Game) -> int:
    print("Enter moves as 'e2 e4'. Type 'undo', 'moves', or 'exit'.\n")
    print(game.render() + "\n")

    while not game.is_over:
        try:
            line = input(f"{game.to_move}> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if line in {"exit", "quit"}:
            break
        if line == "undo":
            game.undo()
            print("\n" + game.render() + "\n")
            continue
        if line == "moves":
            print("  " + ", ".join(sorted(m.notation() for m in game.legal_moves())) + "\n")
            continue

        parts = line.split()
        if len(parts) != 2:
            print("  Enter two squares, for example: e2 e4\n")
            continue

        try:
            move = game.move(*parts)
        except (IllegalMove, ValueError) as exc:
            print(f"  {exc}\n")
            continue

        print(f"\n  {move.notation()}\n")
        print(game.render() + "\n")

    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the chess demo.")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--perft", type=int, metavar="DEPTH")
    args = parser.parse_args(argv)

    if args.perft:
        return run_perft(args.perft)

    game = Game()
    if args.interactive:
        return interactive(game)

    for origin, target, note in GAME:
        move = game.move(origin, target)
        label = f"  {move.notation()}"
        print(f"{label:<16}# {note}" if note else label)

    print("\n" + game.render())
    print(f"\nMaterial — white {game.material(Color.WHITE)}, black {game.material(Color.BLACK)}")
    print(f"{game.to_move} has {len(game.legal_moves())} legal moves.")

    print("\nTaking the last three moves back:")
    for _ in range(3):
        print(f"  undo {game.undo().notation()}")
    print("\n" + game.render())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
