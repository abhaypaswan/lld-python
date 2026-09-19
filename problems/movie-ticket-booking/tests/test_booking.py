"""Seat locking, pricing, and the ordering that stops a double sale."""

import threading

import pytest
from movie_booking import (
    BookingBuilder,
    BookingService,
    BookingStatus,
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
    WeekdayDiscount,
)


class FakeClock:
    def __init__(self, now=0.0):
        self.now = now

    def __call__(self):
        return self.now

    def advance(self, seconds):
        self.now += seconds


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def movie():
    return Movie("M1", "Dune", 166)


@pytest.fixture
def theatre():
    theatre = Theatre("T1", "Cineplex", "Mumbai")
    screen = theatre.add_screen(Screen("S1", "Screen 1"))
    screen.add_row("A", 5, SeatType.REGULAR)
    screen.add_row("B", 5, SeatType.PREMIUM)
    screen.add_row("C", 2, SeatType.RECLINER)
    return theatre


@pytest.fixture
def service(clock, movie, theatre):
    svc = BookingService(lock_manager=SeatLockManager(timeout=300, clock=clock), clock=clock)
    svc.add_show(Show("SH1", movie, theatre, theatre.screens["S1"], starts_at=0.0, base_price=200))
    return svc


# -- models ---------------------------------------------------------------


def test_seat_availability_belongs_to_the_show_not_the_seat(movie, theatre):
    """Booking A1 at 6pm must not take A1 at 9pm."""
    screen = theatre.screens["S1"]
    six = Show("SH1", movie, theatre, screen, 0.0, 200)
    nine = Show("SH2", movie, theatre, screen, 10800.0, 200)

    six.mark_booked(["A1"], "BK-1")

    assert six.is_booked("A1")
    assert not nine.is_booked("A1")


def test_seats_sort_numerically(theatre):
    screen = theatre.screens["S1"]
    screen.add_row("D", 12)

    labels = [seat.label for seat in screen.seats if seat.row == "D"]

    assert labels[:3] == ["D1", "D2", "D3"]
    assert labels[-1] == "D12", "string ordering would put D12 before D2"


def test_a_screen_rejects_a_duplicate_seat(theatre):
    with pytest.raises(ValueError, match="already exists"):
        theatre.screens["S1"].add_row("A", 3)


def test_a_show_needs_a_positive_price(movie, theatre):
    with pytest.raises(ValueError, match="must be positive"):
        Show("SH9", movie, theatre, theatre.screens["S1"], 0.0, 0)


# -- locking --------------------------------------------------------------


def test_holding_seats_blocks_everyone_else(service):
    service.hold("SH1", ["A1", "A2"], "alice")

    with pytest.raises(SeatUnavailable, match="A2"):
        service.hold("SH1", ["A2", "A3"], "bob")


def test_the_same_user_may_re_hold_their_own_seats(service):
    service.hold("SH1", ["A1"], "alice")

    assert service.hold("SH1", ["A1", "A2"], "alice")


def test_a_failed_hold_claims_nothing(service):
    """All or nothing: a party must not end up split across the auditorium."""
    service.hold("SH1", ["A2"], "alice")

    with pytest.raises(SeatUnavailable):
        service.hold("SH1", ["A1", "A2", "A3"], "bob")

    assert service.locks.holder("SH1", "A1") is None
    assert service.locks.holder("SH1", "A3") is None


def test_a_hold_expires_on_its_own(service, clock):
    """Without expiry, one abandoned checkout takes seats out of circulation."""
    service.hold("SH1", ["A1"], "alice")

    clock.advance(301)

    assert not service.locks.is_locked("SH1", "A1")
    assert service.hold("SH1", ["A1"], "bob")


def test_a_hold_survives_until_it_expires(service, clock):
    service.hold("SH1", ["A1"], "alice")

    clock.advance(299)

    with pytest.raises(SeatUnavailable):
        service.hold("SH1", ["A1"], "bob")


def test_abandoning_returns_the_seats_immediately(service):
    service.hold("SH1", ["A1"], "alice")

    service.abandon("SH1", ["A1"], "alice")

    assert service.hold("SH1", ["A1"], "bob")


def test_only_the_holder_can_release(service):
    service.hold("SH1", ["A1"], "alice")

    assert service.locks.release("SH1", ["A1"], "bob") == 0
    assert service.locks.is_locked("SH1", "A1")


def test_the_same_seat_cannot_be_requested_twice(service):
    with pytest.raises(ValueError, match="same seat was requested twice"):
        service.hold("SH1", ["A1", "A1"], "alice")


def test_an_empty_request_is_refused(service):
    with pytest.raises(ValueError, match="No seats"):
        service.hold("SH1", [], "alice")


def test_an_unknown_seat_is_refused(service):
    with pytest.raises(KeyError, match="no seat"):
        service.hold("SH1", ["Z9"], "alice")


def test_a_lock_timeout_must_be_positive():
    with pytest.raises(ValueError, match="must be positive"):
        SeatLockManager(timeout=0)


def test_concurrent_holds_produce_exactly_one_winner(service):
    """Twenty threads, one seat. Check-then-claim is a race without the mutex."""
    winners, losers = [], []
    barrier = threading.Barrier(20)

    def attempt(user):
        barrier.wait()
        try:
            service.hold("SH1", ["A1"], user)
            winners.append(user)
        except SeatUnavailable:
            losers.append(user)

    threads = [threading.Thread(target=attempt, args=(f"user{i}",)) for i in range(20)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(winners) == 1, f"exactly one should win, got {winners}"
    assert len(losers) == 19


# -- the booking flow -----------------------------------------------------


def test_confirming_a_held_seat_produces_a_booking(service):
    service.hold("SH1", ["A1", "A2"], "alice")

    booking = service.confirm("SH1", ["A1", "A2"], "alice")

    assert booking.status is BookingStatus.CONFIRMED
    assert booking.seat_labels == ["A1", "A2"]


def test_confirming_without_holding_is_refused(service):
    with pytest.raises(SeatUnavailable, match="not holding"):
        service.confirm("SH1", ["A1"], "alice")


def test_confirming_after_the_hold_expired_is_refused(service, clock):
    service.hold("SH1", ["A1"], "alice")
    clock.advance(301)

    with pytest.raises(SeatUnavailable, match="hold may have expired"):
        service.confirm("SH1", ["A1"], "alice")


def test_confirming_releases_the_hold(service):
    service.book("SH1", ["A1"], "alice")

    assert service.locks.live_locks == 0, "a confirmed seat needs no hold"


def test_a_booked_seat_cannot_be_held_again(service):
    service.book("SH1", ["A1"], "alice")

    with pytest.raises(SeatUnavailable, match="Already sold"):
        service.hold("SH1", ["A1"], "bob")


def test_a_declined_payment_creates_no_booking(service):
    service.hold("SH1", ["A1"], "alice")

    with pytest.raises(ValueError, match="declined"):
        service.confirm("SH1", ["A1"], "alice", pay=lambda amount: False)

    assert service.bookings == {}
    assert not service.show("SH1").is_booked("A1")


def test_a_declined_payment_frees_the_seat_at_once(service):
    """Waiting out the timeout after a known failure wastes five minutes."""
    service.hold("SH1", ["A1"], "alice")
    with pytest.raises(ValueError):
        service.confirm("SH1", ["A1"], "alice", pay=lambda amount: False)

    assert service.hold("SH1", ["A1"], "bob")


def test_payment_receives_the_quoted_amount(service):
    service.hold("SH1", ["B1"], "alice")
    seen = []

    service.confirm("SH1", ["B1"], "alice", pay=lambda amount: seen.append(amount) or True)

    assert seen == [300], "a premium seat at base 200 is 200 * 1.5"


def test_cancelling_returns_the_seats(service):
    booking = service.book("SH1", ["A1"], "alice")

    service.cancel(booking.booking_id)

    assert not service.show("SH1").is_booked("A1")
    assert service.hold("SH1", ["A1"], "bob")


def test_cancelling_twice_is_an_error(service):
    booking = service.book("SH1", ["A1"], "alice")
    service.cancel(booking.booking_id)

    with pytest.raises(ValueError, match="already cancelled"):
        service.cancel(booking.booking_id)


def test_available_seats_exclude_both_booked_and_held(service):
    service.book("SH1", ["A1"], "alice")
    service.hold("SH1", ["A2"], "bob")

    available = {seat.label for seat in service.available_seats("SH1")}

    assert "A1" not in available
    assert "A2" not in available
    assert "A3" in available


def test_bookings_are_listed_per_user(service):
    service.book("SH1", ["A1"], "alice")
    service.book("SH1", ["A2"], "bob")

    assert len(service.bookings_for("alice")) == 1


# -- pricing --------------------------------------------------------------


def test_seat_class_scales_the_price(service):
    assert service.quote("SH1", ["A1"]) == 200
    assert service.quote("SH1", ["B1"]) == 300
    assert service.quote("SH1", ["C1"]) == 500


def test_a_quote_totals_several_seats(service):
    assert service.quote("SH1", ["A1", "B1"]) == 500


def test_surge_pricing_kicks_in_once_the_house_fills(clock, movie, theatre):
    service = BookingService(
        pricing=SurgePricing(threshold=0.5, multiplier=2.0),
        lock_manager=SeatLockManager(clock=clock),
        clock=clock,
    )
    show = service.add_show(Show("SH1", movie, theatre, theatre.screens["S1"], 0.0, 200))
    assert service.quote("SH1", ["A1"]) == 200

    show.mark_booked([s.label for s in show.screen.seats[:7]], "BK-X")

    assert service.quote("SH1", ["A5"]) == 400


def test_a_weekday_discount_comes_off_the_top(clock, movie, theatre):
    service = BookingService(
        pricing=WeekdayDiscount(25), lock_manager=SeatLockManager(clock=clock), clock=clock
    )
    service.add_show(Show("SH1", movie, theatre, theatre.screens["S1"], 0.0, 200))

    assert service.quote("SH1", ["A1"]) == 150


def test_a_surge_multiplier_below_one_is_refused():
    with pytest.raises(ValueError, match="below 1 is a discount"):
        SurgePricing(multiplier=0.5)


def test_a_discount_of_a_hundred_percent_is_refused():
    with pytest.raises(ValueError, match="between 0 and 100"):
        WeekdayDiscount(100)


# -- builder --------------------------------------------------------------


def test_the_builder_assembles_a_booking(service):
    show = service.show("SH1")
    seats = [show.screen.seat("A1")]

    booking = (
        BookingBuilder().for_show(show).for_user("alice").with_seats(seats).costing(200).build()
    )

    assert booking.amount == 200
    assert booking.booking_id.startswith("BK-")


def test_the_builder_names_everything_that_is_missing(service):
    with pytest.raises(ValueError, match="missing: show, user, seats, amount"):
        BookingBuilder().build()


def test_the_builder_rejects_a_seat_that_is_not_in_the_screen(service, theatre):
    other = Screen("S2", "Screen 2")
    other.add_row("Z", 1)
    show = service.show("SH1")

    with pytest.raises(ValueError, match="no seat"):
        (
            BookingBuilder()
            .for_show(show)
            .for_user("alice")
            .with_seats([other.seat("Z1")])
            .costing(100)
            .build()
        )


def test_the_builder_rejects_duplicate_seats(service):
    seat = service.show("SH1").screen.seat("A1")

    with pytest.raises(ValueError, match="added twice"):
        BookingBuilder().with_seats([seat, seat])


def test_the_builder_rejects_a_negative_amount():
    with pytest.raises(ValueError, match="cannot be negative"):
        BookingBuilder().costing(-1)


def test_builder_calls_chain(service):
    show = service.show("SH1")
    booking = (
        BookingBuilder()
        .for_show(show)
        .for_user("alice")
        .with_seats([show.screen.seat("A1")])
        .costing(200)
        .tagged(coupon="EARLYBIRD")
        .build()
    )

    assert booking.metadata["coupon"] == "EARLYBIRD"


# -- repository and proxy -------------------------------------------------


def test_the_caching_proxy_answers_without_hitting_the_repository(movie, theatre):
    inner = InMemoryShowRepository()
    proxy = CachingShowRepository(inner)
    proxy.add(Show("SH1", movie, theatre, theatre.screens["S1"], 0.0, 200))

    proxy.in_city("Mumbai")
    queries_after_first = inner.query_count
    proxy.in_city("Mumbai")

    assert inner.query_count == queries_after_first, "the second read should be cached"
    assert proxy.hits == 1


def test_the_proxy_invalidates_on_a_write(movie, theatre):
    """A proxy that caches reads and forgets to invalidate is confidently wrong."""
    inner = InMemoryShowRepository()
    proxy = CachingShowRepository(inner)
    proxy.add(Show("SH1", movie, theatre, theatre.screens["S1"], 0.0, 200))
    assert len(proxy.in_city("Mumbai")) == 1

    proxy.add(Show("SH2", movie, theatre, theatre.screens["S1"], 10800.0, 200))

    assert len(proxy.in_city("Mumbai")) == 2


def test_the_proxy_is_interchangeable_with_the_real_repository(clock, movie, theatre):
    """The test of a proxy: a caller cannot tell which one it has."""
    for repository in (InMemoryShowRepository(), CachingShowRepository(InMemoryShowRepository())):
        service = BookingService(
            repository=repository, lock_manager=SeatLockManager(clock=clock), clock=clock
        )
        service.add_show(Show("SH1", movie, theatre, theatre.screens["S1"], 0.0, 200))

        assert service.book("SH1", ["A1"], "alice").status is BookingStatus.CONFIRMED


def test_a_repository_refuses_a_duplicate_show(movie, theatre):
    repository = InMemoryShowRepository()
    repository.add(Show("SH1", movie, theatre, theatre.screens["S1"], 0.0, 200))

    with pytest.raises(ValueError, match="already exists"):
        repository.add(Show("SH1", movie, theatre, theatre.screens["S1"], 0.0, 200))


def test_shows_can_be_found_by_city_and_movie(service):
    assert len(service.shows_in("mumbai")) == 1
    assert len(service.shows_in("Delhi")) == 0
    assert len(service.shows_for("M1")) == 1


def test_an_unknown_show_is_an_error(service):
    with pytest.raises(KeyError, match="No show"):
        service.show("NOPE")


# -- seat map -------------------------------------------------------------


def test_the_seat_map_distinguishes_free_held_and_booked(service):
    service.book("SH1", ["A1"], "alice")
    service.hold("SH1", ["A2"], "bob")

    row = service.seat_map("SH1").splitlines()[0]

    assert row.split()[1:4] == ["#", "o", "."]
