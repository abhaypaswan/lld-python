"""Parking, leaving, and the capacity bookkeeping in between."""

import pytest

from parking_lot import ParkingLot
from parking_lot.components import ParkingLotFull
from parking_lot.model import SpotAlreadyFree, SpotOccupied, VehicleType


def test_parking_assigns_the_first_free_spot(lot):
    ticket = lot.park("ABC-123", "Red", "TwoWheeler")

    assert ticket.spot_number == "0"
    assert ticket.vehicle.vehicle_type is VehicleType.TWO_WHEELER


def test_each_vehicle_type_uses_its_own_block_of_spots(lot):
    assert lot.park("A-1", "Red", "TwoWheeler").spot_number == "0"
    assert lot.park("B-2", "Red", "FourWheeler").spot_number == "10"
    assert lot.park("C-3", "Red", "HUV").spot_number == "15"


def test_parking_reduces_the_free_count(lot):
    before = lot.available_spots

    lot.park("ABC-123", "Red", "TwoWheeler")

    assert lot.available_spots == before - 1


def test_leaving_gives_the_spot_back(lot, clock):
    lot.park("ABC-123", "Red", "TwoWheeler")
    before = lot.available_spots

    clock.advance(3600)
    lot.unpark("ABC-123")

    assert lot.available_spots == before + 1


def test_a_full_section_refuses_more_vehicles(lot):
    # The HUV section has three spots.
    for i in range(3):
        lot.park(f"HUV-{i}", "Red", "HUV")

    with pytest.raises(ParkingLotFull, match="No HUV spot is free"):
        lot.park("HUV-X", "Red", "HUV")


def test_a_full_section_does_not_block_the_others(lot):
    for i in range(3):
        lot.park(f"HUV-{i}", "Red", "HUV")

    assert lot.park("BIKE-1", "Red", "TwoWheeler").spot_number == "0"


def test_a_spot_refuses_a_second_vehicle(lot):
    lot.park("ABC-123", "Red", "TwoWheeler")
    spot = lot.factory.get_spot_manager("TwoWheeler").get_spot("0")

    with pytest.raises(SpotOccupied, match="already holds ABC-123"):
        spot.park(lot.active_tickets["ABC-123"].vehicle)


def test_a_spot_refuses_the_wrong_category_of_vehicle(lot):
    from parking_lot.components import VehicleFactory

    car = VehicleFactory.create("CAR-1", "Red", "FourWheeler")
    bike_spot = lot.factory.get_spot_manager("TwoWheeler").get_spot("0")

    with pytest.raises(ValueError, match="takes TwoWheeler"):
        bike_spot.park(car)


def test_freeing_an_empty_spot_is_an_error(lot):
    manager = lot.factory.get_spot_manager("TwoWheeler")

    with pytest.raises(SpotAlreadyFree, match="already empty"):
        manager.free_parking_spot("0")


def test_an_occupied_spot_cannot_be_taken_out_of_service(lot):
    lot.park("ABC-123", "Red", "TwoWheeler")
    manager = lot.factory.get_spot_manager("TwoWheeler")

    with pytest.raises(ValueError, match="ABC-123 is parked"):
        manager.remove_parking_spot("0")


def test_adding_a_spot_number_twice_is_an_error(lot):
    manager = lot.factory.get_spot_manager("TwoWheeler")

    with pytest.raises(KeyError, match="already exists"):
        manager.add_parking_spot("0")


def test_every_gate_shares_one_manager_per_category():
    lot = ParkingLot().create_parking_lot()

    from_entrance = lot.entrance_gate.factory.get_spot_manager("TwoWheeler")
    from_exit = lot.exit_gate.factory.get_spot_manager("TwoWheeler")

    assert from_entrance is from_exit, "two gates disagreeing about free spots is the bug"


def test_an_unknown_vehicle_type_says_which_ones_exist(lot):
    with pytest.raises(ValueError, match="TwoWheeler, FourWheeler, HUV"):
        lot.park("ABC-123", "Red", "Spaceship")
