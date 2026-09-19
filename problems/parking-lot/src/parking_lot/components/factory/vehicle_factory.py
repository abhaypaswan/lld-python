"""Factory Method: turn raw command input into a Vehicle.

Worth its own seam because parsing is where bad input should be rejected. The
rest of the system gets to assume every Vehicle it sees is already valid.
"""

from __future__ import annotations

from ...model.vehicle import Vehicle, VehicleType


class VehicleFactory:
    """Builds vehicles from the loose strings a gate receives."""

    @staticmethod
    def create(registration_no: str, color: str, vehicle_type: str | VehicleType) -> Vehicle:
        if not isinstance(vehicle_type, VehicleType):
            vehicle_type = VehicleType.parse(vehicle_type)

        return Vehicle(
            registration_no=registration_no.strip().upper(),
            color=color.strip().title(),
            vehicle_type=vehicle_type,
        )
