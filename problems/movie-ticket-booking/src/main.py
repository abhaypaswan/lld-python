"""Runnable demo for movie ticket booking.

python3 src/main.py
"""

from __future__ import annotations

import argparse
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from movie_booking import (  # noqa: E402
    BookingService,
    CachingShowRepository,
    InMemoryShowRepository,
    Movie,
    Screen,
    SeatLockManager,
    SeatType,
    SeatUnavailable,
    Show,
    SurgePricing,
    Theatre,
)


class Clock:
    def __init__(self):
        self.now = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def build(clock, pricing=None, repository=None) -> BookingService:
    service = BookingService(
        repository=repository,
        lock_manager=SeatLockManager(timeout=300, clock=clock),
        pricing=pricing,
        clock=clock,
    )

    theatre = Theatre("T1", "Cineplex", "Mumbai")
    screen = theatre.add_screen(Screen("S1", "Screen 1"))
    screen.add_row("A", 8, SeatType.REGULAR)
    screen.add_row("B", 8, SeatType.PREMIUM)
    screen.add_row("C", 4, SeatType.RECLINER)

    service.add_show(Show("SH1", Movie("M1", "Dune: Part Two", 166), theatre, screen, 0.0, 200))
    return service


def main(argv: list[str] | None = None) -> int:
    argparse.ArgumentParser(description="Run the ticket booking demo.").parse_args(argv)

    clock = Clock()
    service = build(clock)

    print("Screen 1 — A regular, B premium, C recliner.\n")
    print(service.seat_map("SH1"))

    print("\n1. Seat class scales the price off one base of 200.\n")
    for label in ("A1", "B1", "C1"):
        print(f"   {label}  {service.quote('SH1', [label])}")

    print("\n2. alice holds A1 and A2. bob cannot touch them.\n")
    service.hold("SH1", ["A1", "A2"], "alice")
    try:
        service.hold("SH1", ["A2", "A3"], "bob")
    except SeatUnavailable as exc:
        print(f"   bob: {exc}")
    print(f"   and A3 was not claimed either: {service.locks.holder('SH1', 'A3') is None}")

    print("\n3. Payment happens inside the hold. A decline frees the seats at once.\n")
    service.hold("SH1", ["B1"], "bob")
    try:
        service.confirm("SH1", ["B1"], "bob", pay=lambda amount: False)
    except ValueError as exc:
        print(f"   {exc}")
    print(f"   B1 is free again immediately: {service.locks.holder('SH1', 'B1') is None}")

    print("\n4. alice pays and her booking is confirmed.\n")
    booking = service.confirm("SH1", ["A1", "A2"], "alice", pay=lambda amount: True)
    print("   " + booking.render().replace("\n", "\n   "))

    print("\n5. An abandoned checkout expires rather than holding seats forever.\n")
    service.hold("SH1", ["C1", "C2"], "carol")
    print(f"   carol holds C1, C2 — free seats now: {len(service.available_seats('SH1'))}")
    clock.advance(301)
    print(
        f"   five minutes later, the hold lapsed  — free seats: "
        f"{len(service.available_seats('SH1'))}"
    )

    print("\n6. Twenty people click the same seat at once.\n")
    contested = build(Clock())
    winners, losers = [], []
    barrier = threading.Barrier(20)

    def attempt(user: str) -> None:
        barrier.wait()
        try:
            contested.hold("SH1", ["A5"], user)
            winners.append(user)
        except SeatUnavailable:
            losers.append(user)

    threads = [threading.Thread(target=attempt, args=(f"user{i}",)) for i in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    print(f"   {len(winners)} winner ({winners[0]}), {len(losers)} turned away")

    print("\n7. Surge pricing, once the house is more than half full.\n")
    surged = build(Clock(), pricing=SurgePricing(threshold=0.5, multiplier=1.5))
    show = surged.show("SH1")
    print(f"   empty house:  A5 costs {surged.quote('SH1', ['A5'])}")
    show.mark_booked([s.label for s in show.screen.seats[:11]], "BK-X")
    print(f"   55% full:     A5 costs {surged.quote('SH1', ['A5'])}")

    print("\n8. The caching proxy is indistinguishable from the real repository.\n")
    inner = InMemoryShowRepository()
    cached = build(Clock(), repository=CachingShowRepository(inner))
    for _ in range(5):
        cached.shows_in("Mumbai")
    proxy = cached.repository
    print(
        f"   5 listings -> {inner.query_count} repository queries "
        f"({proxy.hits} cache hits, {proxy.hit_rate:.0%})"
    )

    print(f"\nFinal seat map:\n\n{service.seat_map('SH1')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
