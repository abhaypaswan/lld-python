"""The booking flow, front to back."""

from __future__ import annotations

import time
from collections.abc import Callable

from .booking import Booking, BookingBuilder, BookingStatus
from .locks import SeatLockManager, SeatUnavailable
from .models import Movie, Seat, Show, Theatre
from .pricing import PricingStrategy, StandardPricing
from .repository import InMemoryShowRepository, ShowRepository


class BookingService:
    """Select seats, hold them, pay, confirm.

    The ordering below is the answer to this problem:

        1. lock the seats        <- exclusive, and it expires
        2. price them
        3. take payment          <- the slow, failure-prone step
        4. confirm the booking
        5. release the lock

    Payment happens **inside** the lock, which is the whole reason the lock
    exists. Take payment first and two people can both pay for seat A5. Confirm
    first and you have sold a seat nobody paid for.
    """

    def __init__(
        self,
        repository: ShowRepository | None = None,
        lock_manager: SeatLockManager | None = None,
        pricing: PricingStrategy | None = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.clock = clock
        self.repository = repository or InMemoryShowRepository()
        self.locks = lock_manager or SeatLockManager(clock=clock)
        self.pricing = pricing or StandardPricing()
        self.bookings: dict[str, Booking] = {}

    # -- catalogue --------------------------------------------------------

    def add_show(self, show: Show) -> Show:
        return self.repository.add(show)

    def shows_in(self, city: str) -> list[Show]:
        return self.repository.in_city(city)

    def shows_for(self, movie: Movie | str) -> list[Show]:
        movie_id = movie.movie_id if isinstance(movie, Movie) else movie
        return self.repository.for_movie(movie_id)

    def show(self, show_id: str) -> Show:
        found = self.repository.get(show_id)
        if found is None:
            raise KeyError(f"No show {show_id!r}")
        return found

    def available_seats(self, show_id: str) -> list[Seat]:
        """Free seats: not booked, and not currently held by anyone."""
        show = self.show(show_id)
        return show.available_seats(exclude=self.locks.locked_seats(show_id))

    # -- the flow ---------------------------------------------------------

    def hold(self, show_id: str, seat_labels: list[str], user_id: str) -> list[Seat]:
        """Step 1: claim the seats before showing anyone a payment page."""
        show = self.show(show_id)
        labels = [label.strip().upper() for label in seat_labels]

        unknown = [label for label in labels if label not in show.screen]
        if unknown:
            raise KeyError(f"{show.screen.name} has no seat(s): {', '.join(unknown)}")

        already_sold = [label for label in labels if show.is_booked(label)]
        if already_sold:
            raise SeatUnavailable(f"Already sold: {', '.join(sorted(already_sold))}")

        self.locks.lock(show_id, labels, user_id)
        return [show.screen.seat(label) for label in labels]

    def quote(self, show_id: str, seat_labels: list[str]) -> int:
        show = self.show(show_id)
        seats = [show.screen.seat(label) for label in seat_labels]
        return self.pricing.total(show, seats)

    def confirm(
        self,
        show_id: str,
        seat_labels: list[str],
        user_id: str,
        pay: Callable[[int], bool] | None = None,
        **metadata,
    ) -> Booking:
        """Steps 2 to 5. `pay` stands in for a payment gateway."""
        show = self.show(show_id)
        labels = [label.strip().upper() for label in seat_labels]

        held = self.locks.held_by(show_id, user_id)
        missing = [label for label in labels if label not in held]
        if missing:
            # Either never held, or the hold expired while the user was paying.
            raise SeatUnavailable(
                f"You are not holding {', '.join(sorted(missing))} — the hold may have expired"
            )

        seats = [show.screen.seat(label) for label in labels]
        amount = self.pricing.total(show, seats)

        if pay is not None and not pay(amount):
            # Payment failed: drop the hold so the seats go back on sale at
            # once rather than waiting out the timeout.
            self.locks.release(show_id, labels, user_id)
            raise ValueError(f"Payment of {amount} was declined")

        booking = (
            BookingBuilder()
            .for_show(show)
            .for_user(user_id)
            .with_seats(seats)
            .costing(amount)
            .at(self.clock())
            .tagged(**metadata)
            .build()
        )

        show.mark_booked(labels, booking.booking_id)
        booking.status = BookingStatus.CONFIRMED
        self.bookings[booking.booking_id] = booking

        self.locks.release(show_id, labels, user_id)
        return booking

    def book(
        self,
        show_id: str,
        seat_labels: list[str],
        user_id: str,
        pay: Callable[[int], bool] | None = None,
        **metadata,
    ) -> Booking:
        """Hold and confirm in one call, for callers with no payment step."""
        self.hold(show_id, seat_labels, user_id)
        return self.confirm(show_id, seat_labels, user_id, pay, **metadata)

    def cancel(self, booking_id: str) -> Booking:
        booking = self.bookings.get(booking_id)
        if booking is None:
            raise KeyError(f"No booking {booking_id!r}")
        if booking.status is BookingStatus.CANCELLED:
            raise ValueError(f"{booking_id} is already cancelled")

        booking.show.release(booking.seat_labels)
        booking.status = BookingStatus.CANCELLED
        return booking

    def abandon(self, show_id: str, seat_labels: list[str], user_id: str) -> int:
        """The user walked away. Give the seats back now."""
        return self.locks.release(
            show_id, [label.strip().upper() for label in seat_labels], user_id
        )

    # -- reading ----------------------------------------------------------

    def bookings_for(self, user_id: str) -> list[Booking]:
        return [b for b in self.bookings.values() if b.user_id == user_id]

    def seat_map(self, show_id: str) -> str:
        """A text seat map: . free, # booked, o held by someone right now."""
        show = self.show(show_id)
        locked = self.locks.locked_seats(show_id)

        rows: dict[str, list[str]] = {}
        for seat in show.screen.seats:
            if show.is_booked(seat.label):
                mark = "#"
            elif seat.label in locked:
                mark = "o"
            else:
                mark = "."
            rows.setdefault(seat.row, []).append(mark)

        lines = [f"  {row}  {' '.join(marks)}" for row, marks in sorted(rows.items())]
        lines.append("  (. free   o held   # booked)")
        return "\n".join(lines)


def build_theatre(name: str, city: str, rows: dict) -> tuple[Theatre, object]:
    """Convenience for demos and tests: a theatre with one screen."""
    from .models import Screen

    theatre = Theatre(f"T-{name[:3].upper()}", name, city)
    screen = theatre.add_screen(Screen("S1", "Screen 1"))
    for row, (count, seat_type) in rows.items():
        screen.add_row(row, count, seat_type)
    return theatre, screen
