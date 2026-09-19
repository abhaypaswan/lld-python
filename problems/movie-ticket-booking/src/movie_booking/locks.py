"""Seat locks: the reason this problem gets asked at all.

Two people click seat A5 at the same instant. Without something here, both
payment flows succeed and one of them turns up to find someone in their seat.

The answer is a short-lived exclusive hold, taken *before* payment and released
if payment does not complete. It is a lease, not a booking:

- Taken when seats are selected, so nobody else can start paying for them
- Expires on its own, so an abandoned checkout does not hold seats forever
- Converted into a booking on payment, or dropped

The expiry is the part people leave out, and it is the part that matters. A
lock with no timeout means one person closing their laptop takes those seats
out of circulation permanently.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass


class SeatUnavailable(Exception):
    """Someone else holds or has booked at least one of these seats."""


@dataclass(frozen=True)
class SeatLock:
    """An exclusive hold on one seat, for one user, until a deadline."""

    show_id: str
    seat_label: str
    user_id: str
    expires_at: float

    def is_expired(self, now: float) -> bool:
        return now >= self.expires_at

    def remaining(self, now: float) -> float:
        return max(0.0, self.expires_at - now)


class SeatLockManager:
    """Holds every live lock, keyed by (show, seat).

    A real system puts this in Redis with a TTL, because the guarantee has to
    hold across processes. The shape is the same: an atomic claim, a timeout,
    and an owner.

    `clock` is injected so expiry can be tested without sleeping, and there is
    a lock around the whole thing because check-then-claim is a race even in
    one process with threads.
    """

    def __init__(self, timeout: float = 300.0, clock: Callable[[], float] = time.monotonic):
        if timeout <= 0:
            raise ValueError(f"Lock timeout must be positive, got {timeout}")

        self.timeout = timeout
        self.clock = clock
        self._locks: dict[tuple[str, str], SeatLock] = {}
        self._mutex = threading.RLock()

    # -- claiming ---------------------------------------------------------

    def lock(self, show_id: str, seat_labels: list[str], user_id: str) -> list[SeatLock]:
        """Claim every seat, or none of them.

        All-or-nothing is not a nicety. Locking three of five seats and failing
        on the fourth leaves a party split across the auditorium, holding seats
        they did not ask for.
        """
        if not seat_labels:
            raise ValueError("No seats were requested")
        if len(set(seat_labels)) != len(seat_labels):
            raise ValueError("The same seat was requested twice")

        with self._mutex:
            now = self.clock()
            self._expire(now)

            taken = [
                label
                for label in seat_labels
                if (existing := self._locks.get((show_id, label))) is not None
                and existing.user_id != user_id
            ]
            if taken:
                raise SeatUnavailable(f"Someone else is holding: {', '.join(sorted(taken))}")

            expires_at = now + self.timeout
            locks = [SeatLock(show_id, label, user_id, expires_at) for label in seat_labels]
            for held in locks:
                self._locks[(show_id, held.seat_label)] = held
            return locks

    def release(self, show_id: str, seat_labels: list[str], user_id: str) -> int:
        """Give seats back. Only the holder may release them."""
        with self._mutex:
            released = 0
            for label in seat_labels:
                existing = self._locks.get((show_id, label))
                if existing is not None and existing.user_id == user_id:
                    del self._locks[(show_id, label)]
                    released += 1
            return released

    # -- reading ----------------------------------------------------------

    def is_locked(self, show_id: str, seat_label: str) -> bool:
        with self._mutex:
            self._expire(self.clock())
            return (show_id, seat_label) in self._locks

    def holder(self, show_id: str, seat_label: str) -> str | None:
        with self._mutex:
            self._expire(self.clock())
            existing = self._locks.get((show_id, seat_label))
            return existing.user_id if existing else None

    def locked_seats(self, show_id: str) -> set[str]:
        with self._mutex:
            self._expire(self.clock())
            return {label for (held_show, label) in self._locks if held_show == show_id}

    def held_by(self, show_id: str, user_id: str) -> set[str]:
        with self._mutex:
            self._expire(self.clock())
            return {
                label
                for (held_show, label), held in self._locks.items()
                if held_show == show_id and held.user_id == user_id
            }

    def _expire(self, now: float) -> int:
        """Drop expired locks. Lazy, so no timer thread is needed."""
        stale = [key for key, held in self._locks.items() if held.is_expired(now)]
        for key in stale:
            del self._locks[key]
        return len(stale)

    @property
    def live_locks(self) -> int:
        with self._mutex:
            self._expire(self.clock())
            return len(self._locks)
