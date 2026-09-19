"""Runnable demo: a weekend trip, four people, four ways to split.

python3 src/main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from splitwise import (  # noqa: E402
    EqualSplit,
    ExactSplit,
    ExpenseManager,
    PercentageSplit,
    ShareSplit,
    User,
)


def money(cents: int) -> str:
    return f"{cents / 100:,.2f}"


def show(expense) -> None:
    print(f"\n{expense.description}: {expense.payer} paid {money(expense.amount)}")
    print(f"  split {expense.strategy.name}")
    for user, share in expense.shares.items():
        print(f"    {str(user):<8} {money(share):>9}")


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run the shared-expenses demo.").parse_args(argv)

    manager = ExpenseManager()
    alice, bob, carol, dave = (
        manager.add_user(User(name.lower(), name)) for name in ("Alice", "Bob", "Carol", "Dave")
    )
    everyone = [alice, bob, carol, dave]

    # Equal: 10,001 cents four ways does not divide. One person pays a cent more.
    show(manager.add_expense(alice, 10_001, everyone, EqualSplit(), "Groceries"))

    # Shares: Alice and Bob take the double room.
    show(
        manager.add_expense(
            bob,
            48_000,
            everyone,
            ShareSplit({alice: 2, bob: 2, carol: 1, dave: 1}),
            "Cabin",
        )
    )

    # Percentage: Dave drove, so he covers less of the fuel.
    show(
        manager.add_expense(
            carol,
            7_500,
            everyone,
            PercentageSplit({alice: 30, bob: 30, carol: 30, dave: 10}),
            "Fuel",
        )
    )

    # Exact: everyone ordered something different.
    show(
        manager.add_expense(
            dave,
            12_450,
            everyone,
            ExactSplit({alice: 3_200, bob: 4_100, carol: 2_650, dave: 2_500}),
            "Dinner",
        )
    )

    print("\n" + "-" * 48)
    print("Net balances (positive = the group owes them):\n")
    for user in everyone:
        print(f"  {str(user):<8} {money(manager.balance_of(user)):>10}")

    payments = manager.simplify()
    print(f"\n{len(payments)} payments settle all four people:\n")
    for payer, payee, amount in payments:
        print(f"  {payer} pays {payee} {money(amount)}")

    for payer, payee, amount in payments:
        manager.settle(payer, payee, amount)

    print(f"\nAfter settling: {manager.summary()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
