"""Runnable demo: a morning rush through one bank of elevators.

    python3 src/main.py
    python3 src/main.py --strategy nearest
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from elevator_system import Direction, ElevatorSystem  # noqa: E402
from elevator_system.scheduling import STRATEGIES  # noqa: E402

# (tick, floor, direction, destination-once-inside)
TRAFFIC = [
    (0, 0, Direction.UP, 12),
    (0, 0, Direction.UP, 7),
    (1, 9, Direction.DOWN, 0),
    (2, 3, Direction.UP, 11),
    (3, 14, Direction.DOWN, 2),
    (4, 0, Direction.UP, 5),
    (6, 6, Direction.DOWN, 0),
    (8, 11, Direction.DOWN, 4),
]


def simulate(strategy: str, verbose: bool) -> dict:
    system = ElevatorSystem(elevator_count=3, min_floor=0, max_floor=15, strategy=strategy)

    # Once a car reaches a caller's floor, that person presses their floor.
    waiting: dict[int, list[int]] = {}
    for _, floor, _, destination in TRAFFIC:
        waiting.setdefault(floor, []).append(destination)

    def on_stop(elevator, floor):
        for destination in waiting.pop(floor, []):
            elevator.request_floor(destination)

    system.subscribe(on_stop)

    pending = list(TRAFFIC)
    for tick in range(300):
        while pending and pending[0][0] == tick:
            _, floor, direction, _ = pending.pop(0)
            system.request_elevator(floor, direction)

        if not pending and system.is_idle:
            break

        served = system.step()
        if verbose and served:
            print(f"  t{tick:<3} {', '.join(f'{k} stopped at {v}' for k, v in served.items())}")

    return {
        "strategy": strategy,
        "ticks": system.ticks,
        "floors": sum(e.floors_travelled for e in system.elevators),
        "stops": sum(len(e.stops_served) for e in system.elevators),
        "system": system,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Simulate a bank of elevators.")
    parser.add_argument("--strategy", choices=list(STRATEGIES), help="Run just one strategy.")
    args = parser.parse_args(argv)

    print(f"3 elevators, floors 0-15, {len(TRAFFIC)} riders arriving over 8 ticks.\n")

    if args.strategy:
        result = simulate(args.strategy, verbose=True)
        print(f"\n{result['system'].status()}")
        print(f"\n{result['ticks']} ticks, {result['floors']} floors travelled.")
        return 0

    print(f"{'strategy':<14} {'ticks':>7} {'floors travelled':>18} {'stops':>7}")
    print("-" * 50)
    for strategy in STRATEGIES:
        result = simulate(strategy, verbose=False)
        print(
            f"{strategy:<14} {result['ticks']:>7} {result['floors']:>18} {result['stops']:>7}"
        )

    print()
    print("There is no single winner here, which is the point:")
    print("  ticks   how long until the last rider is served (wall clock)")
    print("  floors  total distance run by all cars (energy and wear)")
    print()
    print("`nearest` concentrates work on the closest car and leaves the others")
    print("idle: least distance run, longest wait. `throughput` puts more cars")
    print("in motion at once, so it finishes soonest but runs further to do it.")
    print("Which one a building wants depends on whether it is paying for")
    print("electricity or for people standing in a lobby.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
