"""Runnable demo: the same traffic through all four algorithms.

    python3 src/main.py
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from rate_limiter import RateLimiter  # noqa: E402
from rate_limiter.algorithms import ALGORITHMS  # noqa: E402

LIMIT = 5
WINDOW = 10.0

# Five requests just before a window boundary, five just after. This is the
# pattern that separates the algorithms: a fixed window lets all ten through.
BURST = [9.9] * 5 + [10.1] * 5


def replay(algorithm: str) -> None:
    clock = [0.0]
    limiter = RateLimiter(LIMIT, WINDOW, algorithm, clock=lambda: clock[0])

    allowed = 0
    marks = []
    for at in BURST:
        clock[0] = at
        decision = limiter.allow("user")
        allowed += decision.allowed
        marks.append("." if decision.allowed else "x")

    print(f"  {algorithm:<24} {''.join(marks)}   {allowed}/10 allowed")


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Compare rate limiting algorithms.").parse_args(argv)

    print(f"Limit: {LIMIT} requests per {WINDOW:g}s.")
    print("Traffic: 5 requests at t=9.9s, then 5 more at t=10.1s.")
    print("A fixed window sees two separate budgets. The others do not.\n")

    for algorithm in ALGORITHMS:
        replay(algorithm)

    print("\n('.' allowed, 'x' rejected)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
