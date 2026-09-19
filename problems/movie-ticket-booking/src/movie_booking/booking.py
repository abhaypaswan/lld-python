"""The booking, and the Builder that assembles one."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field
from enum import Enum

from .models import Seat, Show

_ids = itertools.count(1)


class BookingStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

    def __str__(self) -> str:
        return self.value


@dataclass
class Booking:
    """A confirmed set of seats for one show."""

    booking_id: str
    show: Show
    user_id: str
    seats: list[Seat]
    amount: int
    status: BookingStatus = BookingStatus.PENDING
    created_at: float = 0.0
    metadata: dict = field(default_factory=dict)

    @property
    def seat_labels(self) -> list[str]:
        return [seat.label for seat in self.seats]

    @property
    def is_active(self) -> bool:
        return self.status is BookingStatus.CONFIRMED

    def render(self) -> str:
        return "\n".join(
            [
                f"Booking {self.booking_id} [{self.status}]",
                f"  {self.show.movie.title} at {self.show.theatre.name}",
                f"  Screen {self.show.screen.name}, seats {', '.join(self.seat_labels)}",
                f"  Total: {self.amount}",
            ]
        )

    def __str__(self) -> str:
        return f"{self.booking_id}: {len(self.seats)} seat(s) for {self.amount}"


class BookingBuilder:
    """Builder: assemble a booking a piece at a time, validating at the end.

    Worth the class because a booking needs several things that arrive at
    different moments -- the show is picked on one screen, the seats on the
    next, the payment method on a third -- and several of them are optional
    (a coupon, a loyalty id, a note).

    A constructor taking eight arguments, five of them optional, is the thing
    this replaces. The other thing it replaces is a half-built Booking floating
    around in an invalid state: nothing is constructed until `build`, and
    `build` refuses anything incomplete.
    """

    def __init__(self):
        self._show: Show | None = None
        self._user_id: str | None = None
        self._seats: list[Seat] = []
        self._amount: int | None = None
        self._created_at: float = 0.0
        self._metadata: dict = {}

    def for_show(self, show: Show) -> BookingBuilder:
        self._show = show
        return self

    def for_user(self, user_id: str) -> BookingBuilder:
        self._user_id = user_id
        return self

    def with_seats(self, seats: list[Seat]) -> BookingBuilder:
        if not seats:
            raise ValueError("A booking needs at least one seat")
        if len({seat.label for seat in seats}) != len(seats):
            raise ValueError("The same seat was added twice")

        self._seats = list(seats)
        return self

    def costing(self, amount: int) -> BookingBuilder:
        if amount < 0:
            raise ValueError(f"Amount cannot be negative, got {amount}")
        self._amount = amount
        return self

    def at(self, timestamp: float) -> BookingBuilder:
        self._created_at = timestamp
        return self

    def tagged(self, **metadata) -> BookingBuilder:
        self._metadata.update(metadata)
        return self

    def build(self) -> Booking:
        """Validate everything at once, naming every missing piece."""
        missing = [
            name
            for name, value in (
                ("show", self._show),
                ("user", self._user_id),
                ("seats", self._seats or None),
                ("amount", self._amount),
            )
            if value is None
        ]
        if missing:
            raise ValueError(f"Booking is incomplete, missing: {', '.join(missing)}")

        # Reporting every problem at once beats failing on the first, which
        # makes the caller fix one thing and resubmit to find the next.
        unknown = [seat.label for seat in self._seats if seat.label not in self._show.screen]
        if unknown:
            raise ValueError(
                f"{self._show.screen.name} has no seat(s): {', '.join(sorted(unknown))}"
            )

        return Booking(
            booking_id=f"BK-{next(_ids):06d}",
            show=self._show,
            user_id=self._user_id,
            seats=self._seats,
            amount=self._amount,
            created_at=self._created_at,
            metadata=dict(self._metadata),
        )
