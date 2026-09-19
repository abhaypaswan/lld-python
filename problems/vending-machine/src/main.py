"""Runnable demo for the vending machine design.

python3 src/main.py               # scripted walkthrough
python3 src/main.py --interactive # drive it yourself
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from vending_machine import VendingMachine  # noqa: E402
from vending_machine.model import CannotMakeChange, SoldOut  # noqa: E402
from vending_machine.states import InvalidAction  # noqa: E402


def stocked_machine() -> VendingMachine:
    machine = VendingMachine()
    machine.add_item("A1", "Coke", 75, quantity=2)
    machine.add_item("A2", "Chips", 50, quantity=1)
    machine.add_item("B1", "Candy Bar", 65, quantity=3)
    machine.load_coins(quarter=4, dime=4, nickel=4)
    return machine


SCRIPT = [
    "status",
    "insert dollar",
    "select A1",
    "dispense",
    "status",
    "insert quarter",
    "select A1",  # 25 is not enough for a 75c Coke
    "insert quarter",
    "insert quarter",
    "select A1",
    "dispense",
    "select A1",  # now sold out
    "insert dollar",
    "refund",
    "status",
]


def run(machine: VendingMachine, line: str) -> None:
    """Run one command, printing what happened or why it could not."""
    parts = line.strip().split()
    if not parts:
        return

    print(f"> {line}")
    action, args = parts[0], parts[1:]

    try:
        if action == "status":
            print(machine.status())
        elif action == "insert":
            print(machine.insert_coin(args[0]))
        elif action == "select":
            print(machine.select_item(args[0]))
        elif action == "dispense":
            item = machine.dispense()
            change = ", ".join(str(c) for c in machine.last_change) or "none"
            print(f"Dispensed {item.name}. Change: {change}")
        elif action == "refund":
            coins = ", ".join(str(c) for c in machine.refund()) or "nothing"
            print(f"Returned: {coins}")
        else:
            print(f"  unknown command: {action}")
    except (InvalidAction, SoldOut, CannotMakeChange, ValueError, KeyError, IndexError) as exc:
        print(f"  {exc}")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the vending machine.")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args(argv)

    machine = stocked_machine()

    if args.interactive:
        print("Commands: status | insert <coin> | select <code> | dispense | refund | exit\n")
        while True:
            try:
                line = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if line in {"exit", "quit"}:
                break
            run(machine, line)
        return 0

    for line in SCRIPT:
        run(machine, line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
