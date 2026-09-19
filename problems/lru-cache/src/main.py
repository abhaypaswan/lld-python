"""Runnable demo: the same access pattern under three eviction policies.

    python3 src/main.py
    python3 src/main.py --capacity 4
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lru_cache import Cache  # noqa: E402

# Deliberately chosen so the three policies disagree: "a" is read often but
# early, "d" arrives late and is never read again.
ACCESS_PATTERN = [
    ("put", "a", 1),
    ("put", "b", 2),
    ("get", "a", None),
    ("get", "a", None),
    ("put", "c", 3),
    ("get", "b", None),
    ("put", "d", 4),
    ("get", "a", None),
    ("put", "e", 5),
]


def replay(policy: str, capacity: int) -> None:
    cache = Cache(capacity, policy)

    print(f"--- {policy.upper()}, capacity {capacity} ---")
    for action, key, value in ACCESS_PATTERN:
        if action == "put":
            cache.put(key, value)
            print(f"  put {key}={value:<3} -> {cache.keys()}")
        else:
            hit = cache.get(key)
            outcome = f"hit ({hit})" if hit is not None else "MISS"
            print(f"  get {key:<5} {outcome:<9} -> {cache.keys()}")

    print(f"  survivors: {sorted(cache.keys())}")
    print(f"  {cache.stats}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compare cache eviction policies.")
    parser.add_argument("--capacity", type=int, default=3)
    args = parser.parse_args(argv)

    print("The same access pattern, three policies. Note who survives.\n")
    for policy in ("lru", "lfu", "fifo"):
        replay(policy, args.capacity)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
