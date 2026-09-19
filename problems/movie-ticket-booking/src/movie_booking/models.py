"""Movies, theatres, screens, seats and shows."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SeatType(Enum):
    """Seat classes, with the multiplier applied to a show's base price."""

    REGULAR = 1.0
    PREMIUM = 1.5
    RECLINER = 2.5

    @property
    def multiplier(self) -> float:
        return self.value

    def __str__(self) -> str:
        return self.name.lower()


@dataclass(frozen=True)
class Movie:
    movie_id: str
    title: str
    duration_minutes: int
    language: str = "English"
    rating: str = "U/A"

    def __post_init__(self):
        if self.duration_minutes <= 0:
            raise ValueError(f"{self.title} needs a positive duration")

    def __str__(self) -> str:
        return f"{self.title} ({self.language})"


@dataclass(frozen=True)
class Seat:
    """A seat in a screen. Frozen, and identified by its label.

    A seat is a physical fact about a screen, not about a show -- which is why
    availability lives on the Show and not here. Putting a `booked` flag on
    Seat is the classic mistake: booking seat A1 for the 6pm show would mark it
    taken for the 9pm show too.
    """

    label: str
    seat_type: SeatType = SeatType.REGULAR

    @property
    def row(self) -> str:
        return self.label[0]

    def __str__(self) -> str:
        return self.label


class Screen:
    """One auditorium, with a fixed seat layout."""

    def __init__(self, screen_id: str, name: str = ""):
        self.screen_id = screen_id
        self.name = name or screen_id
        self._seats: dict[str, Seat] = {}

    def add_row(self, row: str, count: int, seat_type: SeatType = SeatType.REGULAR) -> list[Seat]:
        seats = []
        for number in range(1, count + 1):
            seat = Seat(f"{row}{number}", seat_type)
            if seat.label in self._seats:
                raise ValueError(f"Seat {seat.label} already exists in {self.name}")
            self._seats[seat.label] = seat
            seats.append(seat)
        return seats

    def seat(self, label: str) -> Seat:
        found = self._seats.get(label.strip().upper())
        if found is None:
            raise KeyError(f"{self.name} has no seat {label}")
        return found

    @property
    def seats(self) -> list[Seat]:
        return [self._seats[label] for label in sorted(self._seats, key=_seat_sort_key)]

    @property
    def capacity(self) -> int:
        return len(self._seats)

    def __contains__(self, label: str) -> bool:
        return label in self._seats


class Theatre:
    def __init__(self, theatre_id: str, name: str, city: str):
        self.theatre_id = theatre_id
        self.name = name
        self.city = city
        self.screens: dict[str, Screen] = {}

    def add_screen(self, screen: Screen) -> Screen:
        if screen.screen_id in self.screens:
            raise ValueError(f"{self.name} already has screen {screen.screen_id}")
        self.screens[screen.screen_id] = screen
        return screen

    def __str__(self) -> str:
        return f"{self.name}, {self.city}"


class Show:
    """A movie on a screen at a time. Availability lives here.

    This is the object bookings are made against, and the reason it exists
    separately from Screen: the same seat is free at 6pm and taken at 9pm.
    """

    def __init__(
        self,
        show_id: str,
        movie: Movie,
        theatre: Theatre,
        screen: Screen,
        starts_at: float,
        base_price: int,
    ):
        if base_price <= 0:
            raise ValueError(f"Base price must be positive, got {base_price}")

        self.show_id = show_id
        self.movie = movie
        self.theatre = theatre
        self.screen = screen
        self.starts_at = starts_at
        self.base_price = base_price
        #: seat label -> booking id. Only confirmed bookings appear here;
        #: in-flight holds live in the lock manager, deliberately separate.
        self._booked: dict[str, str] = {}

    # -- availability -----------------------------------------------------

    def is_booked(self, label: str) -> bool:
        return label in self._booked

    def booked_seats(self) -> list[str]:
        return sorted(self._booked, key=_seat_sort_key)

    def available_seats(self, exclude: set[str] | None = None) -> list[Seat]:
        blocked = set(self._booked) | (exclude or set())
        return [seat for seat in self.screen.seats if seat.label not in blocked]

    @property
    def is_sold_out(self) -> bool:
        return len(self._booked) == self.screen.capacity

    # -- booking ----------------------------------------------------------

    def mark_booked(self, labels: list[str], booking_id: str) -> None:
        already = [label for label in labels if label in self._booked]
        if already:
            raise ValueError(f"Already booked: {', '.join(already)}")

        for label in labels:
            self._booked[label] = booking_id

    def release(self, labels: list[str]) -> None:
        for label in labels:
            self._booked.pop(label, None)

    def price_of(self, seat: Seat) -> int:
        return round(self.base_price * seat.seat_type.multiplier)

    def __str__(self) -> str:
        return f"{self.movie.title} @ {self.theatre.name} {self.screen.name}"


def _seat_sort_key(label: str):
    """Sort A2 before A10, which plain string ordering does not."""
    row, number = label[0], label[1:]
    return (row, int(number)) if number.isdigit() else (row, 0)
