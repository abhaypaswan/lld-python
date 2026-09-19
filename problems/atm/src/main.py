"""Runnable demo for the ATM.

python3 src/main.py                # scripted session
python3 src/main.py --interactive  # drive it yourself
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from atm import ATM, Bank, CashDispenser, InsufficientCash, InsufficientFunds  # noqa: E402
from atm.bank import AuthenticationFailed  # noqa: E402
from atm.states import InvalidOperation  # noqa: E402

ERRORS = (InvalidOperation, AuthenticationFailed, InsufficientFunds, InsufficientCash, ValueError)

SCRIPT = [
    ("withdraw 2000", "withdrawing before inserting a card"),
    ("card 111", None),
    ("withdraw 2000", "withdrawing before entering a PIN"),
    ("pin 9999", "a wrong PIN"),
    ("pin 1234", None),
    ("balance", None),
    ("withdraw 7700", None),
    ("collect", None),
    ("withdraw 150", "an amount no combination of notes can make"),
    ("withdraw 999999", "more than the account holds"),
    ("deposit 5000", None),
    ("transfer 222 3000", None),
    ("balance", None),
    ("eject", None),
]


def build() -> ATM:
    bank = Bank()
    bank.open_account("111", "1234", balance=50_000, daily_limit=25_000)
    bank.open_account("222", "4321", balance=10_000)

    dispenser = CashDispenser()
    dispenser.load(two_thousand=8, five_hundred=10, two_hundred=10, hundred=20)
    return ATM(bank, dispenser)


def run(machine: ATM, line: str, note: str | None = None) -> None:
    parts = line.split()
    if not parts:
        return

    label = f"> {line}"
    print(f"{label:<28}# {note}" if note else label)

    action, args = parts[0], parts[1:]
    try:
        if action == "card":
            print(f"  {machine.insert_card(args[0])}")
        elif action == "pin":
            print(f"  {machine.enter_pin(args[0])}")
        elif action == "balance":
            print(f"  Balance: {machine.check_balance()}")
        elif action == "withdraw":
            plan = machine.withdraw(int(args[0]))
            print(f"  Dispensing {args[0]}: {machine.dispenser.describe(plan)}")
        elif action == "collect":
            print(f"  Collected {machine.dispenser.describe(machine.collect_cash())}")
        elif action == "deposit":
            print(f"  New balance: {machine.deposit(int(args[0]))}")
        elif action == "transfer":
            balance = machine.transfer(args[0], int(args[1]))
            print(f"  Sent {args[1]} to {args[0]}. Balance: {balance}")
        elif action == "status":
            print("  " + machine.status().replace("\n", "\n  "))
        elif action == "eject":
            print(f"  {machine.eject_card()}")
        else:
            print(f"  unknown command: {action}")
    except ERRORS as exc:
        print(f"  refused: {exc}")
    except IndexError:
        print("  that command needs more arguments")
    print()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the ATM.")
    parser.add_argument("--interactive", action="store_true")
    args = parser.parse_args(argv)

    machine = build()
    print(machine.status() + "\n")

    if args.interactive:
        print("card <n> | pin <n> | balance | withdraw <amt> | collect |")
        print("deposit <amt> | transfer <acct> <amt> | status | eject | exit\n")
        print("Try card 111, pin 1234.\n")
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

    for line, note in SCRIPT:
        run(machine, line, note)

    print(machine.status())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
