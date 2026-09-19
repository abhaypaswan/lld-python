"""Owns every spot of one vehicle category."""

from __future__ import annotations

from ...model.parking_spot import ParkingSpot
from ...model.vehicle import Vehicle, VehicleType
from ..strategy.parking_strategy import ParkingStrategy, get_parking_strategy


class ParkingLotFull(Exception):
    """Raised when no spot of the requested category is free."""


class ParkingSpotManager:
    """The set of spots for one VehicleType, plus the rules for using them.

    There used to be one subclass per vehicle type here. They were identical
    apart from which spot class they instantiated, so the type is now a
    constructor argument instead. Three classes became one, and adding a fourth
    category is now a factory entry rather than a new file.
    """

    def __init__(self, vehicle_type: VehicleType, strategy: ParkingStrategy | None = None):
        self.vehicle_type = vehicle_type
        self.strategy = strategy or get_parking_strategy()
        self._spots: dict[str, ParkingSpot] = {}

    # -- capacity ---------------------------------------------------------

    @property
    def total_spots(self) -> int:
        return len(self._spots)

    @property
    def available_spots(self) -> int:
        # Counted from the spots themselves rather than tracked in a separate
        # integer. A hand-maintained counter is the classic place for this
        # design to go wrong: miss one decrement and the lot never fills up.
        return sum(1 for spot in self._spots.values() if spot.is_free)

    def is_full(self) -> bool:
        return self.available_spots == 0

    # -- managing the spots themselves ------------------------------------

    def add_parking_spot(self, spot_number: str, **rates) -> ParkingSpot:
        spot_number = str(spot_number)
        if spot_number in self._spots:
            raise KeyError(f"Spot {spot_number} already exists for {self.vehicle_type}")

        spot = ParkingSpot(spot_number, self.vehicle_type, **rates)
        self._spots[spot_number] = spot
        return spot

    def remove_parking_spot(self, spot_number: str) -> ParkingSpot:
        spot_number = str(spot_number)
        spot = self._spots.get(spot_number)
        if spot is None:
            raise KeyError(f"There is no spot {spot_number} for {self.vehicle_type}")
        if not spot.is_free:
            raise ValueError(f"{spot.vehicle.registration_no} is parked in spot {spot_number}")

        return self._spots.pop(spot_number)

    def get_spot(self, spot_number: str) -> ParkingSpot | None:
        return self._spots.get(str(spot_number))

    @property
    def spots(self) -> list[ParkingSpot]:
        return list(self._spots.values())

    # -- parking and leaving ----------------------------------------------

    def find_parking_spot(self, strategy: ParkingStrategy | str | None = None):
        return self._resolve_strategy(strategy).find_parking_spot(self._spots.values())

    def park_vehicle(
        self, vehicle: Vehicle, strategy: ParkingStrategy | str | None = None
    ) -> ParkingSpot:
        spot = self.find_parking_spot(strategy)
        if spot is None:
            raise ParkingLotFull(f"No {self.vehicle_type} spot is free")

        spot.park(vehicle)
        return spot

    def free_parking_spot(self, spot_number: str) -> Vehicle:
        spot = self._spots.get(str(spot_number))
        if spot is None:
            raise KeyError(f"There is no spot {spot_number} for {self.vehicle_type}")
        return spot.release()

    def _resolve_strategy(self, strategy) -> ParkingStrategy:
        if strategy is None:
            return self.strategy
        if isinstance(strategy, str):
            return get_parking_strategy(strategy)
        return strategy

    # -- queries ----------------------------------------------------------

    def occupied_spots(self) -> list[ParkingSpot]:
        return [spot for spot in self._spots.values() if not spot.is_free]

    def spots_by_color(self, color: str) -> list[ParkingSpot]:
        wanted = color.strip().lower()
        return [spot for spot in self.occupied_spots() if spot.vehicle.color.lower() == wanted]

    def spot_by_registration_no(self, registration_no: str) -> ParkingSpot | None:
        wanted = registration_no.strip().upper()
        for spot in self.occupied_spots():
            if spot.vehicle.registration_no == wanted:
                return spot
        return None
