"""The console. Every command is exercised through ParkingLot.execute()."""

import pytest

from parking_lot.commands import CommandError

HOUR = 3600


def test_park_reports_the_spot_and_ticket(lot):
    output = lot.execute("park_vehicle ABC-123 Red TwoWheeler")

    assert "Parking Spot: 0" in output
    assert "Ticket: T-" in output


def test_registration_numbers_are_normalised(lot):
    lot.execute("park_vehicle abc-123 red TwoWheeler")

    assert "ABC-123" in lot.execute("get_vehicles_by_registration_no ABC-123")


def test_listing_an_empty_lot_says_so(lot):
    assert lot.execute("list_all_parked_vehicles") == "The parking lot is empty."


def test_listing_shows_every_parked_vehicle(lot):
    lot.execute("park_vehicle ABC-123 Red TwoWheeler")
    lot.execute("park_vehicle DEF-456 White FourWheeler")

    output = lot.execute("list_all_parked_vehicles")

    assert "ABC-123" in output
    assert "DEF-456" in output


def test_colour_search_is_case_insensitive(lot):
    lot.execute("park_vehicle DEF-456 White FourWheeler")

    assert "DEF-456" in lot.execute("get_vehicles_by_color white")


def test_a_plate_that_is_not_here_says_so(lot):
    assert "No vehicle found" in lot.execute("get_vehicles_by_registration_no ZZZ-000")


def test_unparking_charges_for_the_stay(lot, clock):
    lot.execute("park_vehicle DEF-456 White FourWheeler")
    clock.advance(2 * HOUR)

    output = lot.execute("unpark_vehicle DEF-456")

    assert "Parking fee: 400" in output


def test_unparking_an_unknown_plate_is_an_error(lot):
    with pytest.raises(KeyError, match="No open ticket"):
        lot.execute("unpark_vehicle ZZZ-000")


def test_a_ticket_cannot_be_paid_twice(lot, clock):
    ticket = lot.park("DEF-456", "White", "FourWheeler")
    clock.advance(HOUR)
    lot.unpark("DEF-456")

    with pytest.raises(ValueError, match="already been paid"):
        lot.exit_gate.checkout(ticket)


def test_add_and_remove_spot_change_the_total(lot):
    before = lot.total_spots

    lot.execute("add_parking_spot 99 TwoWheeler")
    assert lot.total_spots == before + 1

    lot.execute("remove_parking_spot 99 TwoWheeler")
    assert lot.total_spots == before


def test_status_reports_each_section(lot):
    lot.execute("park_vehicle ABC-123 Red TwoWheeler")

    assert "TwoWheeler: 9 free of 10" in lot.execute("status")


def test_help_lists_every_command(lot):
    output = lot.execute("help")

    for name in lot.commands:
        assert name in output


def test_an_unknown_command_lists_the_known_ones(lot):
    with pytest.raises(CommandError, match="Unknown command: teleport"):
        lot.execute("teleport ABC-123")


def test_the_wrong_number_of_arguments_shows_the_usage(lot):
    with pytest.raises(CommandError, match="Usage: park_vehicle"):
        lot.execute("park_vehicle ABC-123")


def test_a_blank_line_does_nothing(lot):
    assert lot.execute("   ") == ""
