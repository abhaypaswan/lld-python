"""Runnable demo for the parking lot design.

    python3 src/main.py                       # replay src/input.txt
    python3 src/main.py --interactive         # type commands yourself
    python3 src/main.py --parking-strategy nearest --pricing free-first-hour

Type `help` in interactive mode for the full command list.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parking_lot import ParkingLot  # noqa: E402
from parking_lot.commands import CommandError  # noqa: E402

DEFAULT_SCRIPT = Path(__file__).resolve().parent / "input.txt"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the parking lot.")
    parser.add_argument(
        "script",
        nargs="?",
        type=Path,
        default=DEFAULT_SCRIPT,
        help="File of commands to replay (default: src/input.txt).",
    )
    parser.add_argument(
        "--interactive", action="store_true", help="Read commands from the terminal instead."
    )
    parser.add_argument(
        "--parking-strategy",
        default="default",
        help="How a spot is chosen: first-available, nearest, farthest.",
    )
    parser.add_argument(
        "--pricing",
        default="default",
        help="How a stay is priced: hourly, flat, free-first-hour.",
    )
    return parser.parse_args(argv)


def run_line(lot: ParkingLot, line: str) -> None:
    """Run one command, reporting failures without killing the session."""
    line = line.strip()
    if not line or line.startswith("#"):
        return

    print(f"> {line}")
    try:
        output = lot.execute(line)
    except (CommandError, KeyError, ValueError) as exc:
        # A bad command should not end the session. This is the difference
        # between a console and a script that dies on the first typo.
        print(f"  error: {exc}")
    else:
        if output:
            print(output)
    print()


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    lot = ParkingLot(
        parking_strategy=args.parking_strategy, pricing_strategy=args.pricing
    ).create_parking_lot()

    print(f"Parking lot ready: {lot.total_spots} spots.\n")

    if args.interactive:
        print("Type `help` for commands, `exit` to quit.\n")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if line in {"exit", "quit"}:
                break
            run_line(lot, line)
        return 0

    if not args.script.is_file():
        print(f"No such command file: {args.script}", file=sys.stderr)
        return 1

    for line in args.script.read_text(encoding="utf-8").splitlines():
        if line.strip() in {"exit", "quit"}:
            break
        run_line(lot, line)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
