"""The two strategies, checked independently of the lot around them."""

import pytest

from parking_lot import ParkingLot
from parking_lot.components import (
    FarthestParkingStrategy,
    FirstAvailableStrategy,
    FlatRatePricingStrategy,
    FreeFirstHourStrategy,
    HourlyPricingStrategy,
    NearestParkingStrategy,
    get_parking_strategy,
    get_pricing_strategy,
)
from parking_lot.model import ParkingSpot, Ticket, Vehicle, VehicleType

HOUR = 3600


def spots(*numbers):
    return [ParkingSpot(str(n), VehicleType.TWO_WHEELER) for n in numbers]


def test_first_available_sorts_numerically_not_alphabetically():
    # Plain string sorting would put "10" before "9".
    chosen = FirstAvailableStrategy().find_parking_spot(spots(9, 10, 11))

    assert chosen.spot_number == "9"


def test_nearest_prefers_even_spots_then_odd():
    available = spots(0, 1, 2, 3)
    strategy = NearestParkingStrategy()

    order = []
    for _ in range(4):
        spot = strategy.find_parking_spot(available)
        spot.park(Vehicle(f"V-{len(order)}", "Red", VehicleType.TWO_WHEELER))
        order.append(spot.spot_number)

    assert order == ["0", "2", "1", "3"]


def test_farthest_takes_the_highest_number():
    assert FarthestParkingStrategy().find_parking_spot(spots(1, 5, 12)).spot_number == "12"


def test_a_strategy_never_returns_an_occupied_spot():
    available = spots(0, 1)
    available[0].park(Vehicle("A-1", "Red", VehicleType.TWO_WHEELER))

    assert FirstAvailableStrategy().find_parking_spot(available).spot_number == "1"


def test_a_strategy_returns_none_when_nothing_is_free():
    available = spots(0)
    available[0].park(Vehicle("A-1", "Red", VehicleType.TWO_WHEELER))

    assert FirstAvailableStrategy().find_parking_spot(available) is None


def test_an_unknown_strategy_name_lists_the_known_ones():
    with pytest.raises(ValueError, match="first-available"):
        get_parking_strategy("teleport")


def test_the_lot_honours_the_strategy_it_was_built_with():
    lot = ParkingLot(parking_strategy="farthest").create_parking_lot()

    assert lot.park("ABC-123", "Red", "TwoWheeler").spot_number == "9"


# -- pricing --------------------------------------------------------------


def ticket_for(hour_charge=200, minute_charge=2, entry_time=0.0):
    spot = ParkingSpot("1", VehicleType.FOUR_WHEELER, hour_charge, minute_charge)
    vehicle = Vehicle("ABC-123", "Red", VehicleType.FOUR_WHEELER)
    return Ticket(vehicle=vehicle, parking_spot=spot, entry_time=entry_time)


def test_hourly_pricing_charges_per_hour_plus_leftover_minutes():
    # Two hours and thirty minutes: 2 * 200 + 30 * 2.
    assert HourlyPricingStrategy().calculate(ticket_for(), 2 * HOUR + 30 * 60) == 460


def test_a_stay_under_a_minute_is_free_on_hourly_pricing():
    assert HourlyPricingStrategy().calculate(ticket_for(), 30) == 0


def test_a_flat_rate_ignores_how_long_you_stayed():
    strategy = FlatRatePricingStrategy(150)

    assert strategy.calculate(ticket_for(), 30) == 150
    assert strategy.calculate(ticket_for(), 90 * HOUR) == 150


def test_the_first_hour_is_free_under_that_strategy():
    strategy = FreeFirstHourStrategy()

    assert strategy.calculate(ticket_for(), 59 * 60) == 0
    # Three hours ten minutes: the first hour is free, so 2 * 200 + 10 * 2.
    assert strategy.calculate(ticket_for(), 3 * HOUR + 10 * 60) == 420


def test_a_clock_that_runs_backwards_never_produces_a_negative_bill():
    assert HourlyPricingStrategy().calculate(ticket_for(entry_time=5 * HOUR), 0) == 0


def test_an_unknown_pricing_name_lists_the_known_ones():
    with pytest.raises(ValueError, match="hourly"):
        get_pricing_strategy("barter")
