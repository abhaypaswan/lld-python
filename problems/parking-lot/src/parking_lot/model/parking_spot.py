"""A single numbered spot and its tariff."""

from __future__ import annotations

from .vehicle import Vehicle, VehicleType

#: Default tariff per spot category: (charge per whole hour, charge per minute).
#: Real lots price by category, not by individual spot, so keeping the table
#: here rather than in three subclasses means changing prices is a one-line edit.
DEFAULT_RATES: dict[VehicleType, tuple[int, int]] = {
    VehicleType.TWO_WHEELER: (100, 1),
    VehicleType.FOUR_WHEELER: (200, 2),
    VehicleType.HUV: (300, 3),
}


class SpotOccupied(Exception):
    """Raised when something tries to park in a spot that already has a car."""


class SpotAlreadyFree(Exception):
    """Raised when something tries to free a spot that is already empty."""


class ParkingSpot:
    """One numbered spot for one category of vehicle.

    There are deliberately no subclasses per vehicle type. The only thing that
    differed between a TwoWheelerParkingSpot and a FourWheelerParkingSpot was
    two numbers, and two numbers are data, not a class hierarchy.
    """

    def __init__(
        self,
        spot_number: str,
        vehicle_type: VehicleType,
        hour_charge: int | None = None,
        minute_charge: int | None = None,
    ):
        default_hour, default_minute = DEFAULT_RATES[vehicle_type]

        self.spot_number = str(spot_number)
        self.vehicle_type = vehicle_type
        self.hour_charge = default_hour if hour_charge is None else hour_charge
        self.minute_charge = default_minute if minute_charge is None else minute_charge
        self.vehicle: Vehicle | None = None

    @property
    def is_free(self) -> bool:
        return self.vehicle is None

    def park(self, vehicle: Vehicle) -> str:
        if self.vehicle is not None:
            raise SpotOccupied(
                f"Spot {self.spot_number} already holds {self.vehicle.registration_no}"
            )
        if vehicle.vehicle_type is not self.vehicle_type:
            raise ValueError(
                f"Spot {self.spot_number} takes {self.vehicle_type}, "
                f"but {vehicle.registration_no} is a {vehicle.vehicle_type}"
            )

        self.vehicle = vehicle
        return self.spot_number

    def release(self) -> Vehicle:
        """Empty the spot and hand back whoever was in it."""
        if self.vehicle is None:
            raise SpotAlreadyFree(f"Spot {self.spot_number} is already empty")

        vehicle, self.vehicle = self.vehicle, None
        return vehicle

    def __repr__(self) -> str:
        who = "free" if self.is_free else self.vehicle.registration_no
        return f"ParkingSpot({self.spot_number!r}, {self.vehicle_type}, {who})"
