"""Factory: hand out the one manager that owns each vehicle category.

Every gate and command goes through this, so there is exactly one manager per
category for the life of the lot. That single-instance guarantee is the whole
job -- without it, two gates would each hold their own idea of which spots are
free.
"""

from __future__ import annotations

from ...model.vehicle import VehicleType
from ..parking_spot_managers.parking_spot_manager import ParkingSpotManager
from ..strategy.parking_strategy import ParkingStrategy


class ParkingSpotManagerFactory:
    def __init__(self, strategy: ParkingStrategy | None = None):
        self._managers: dict[VehicleType, ParkingSpotManager] = {
            vehicle_type: ParkingSpotManager(vehicle_type, strategy)
            for vehicle_type in VehicleType
        }

    def get_spot_manager(self, vehicle_type: str | VehicleType) -> ParkingSpotManager:
        if not isinstance(vehicle_type, VehicleType):
            vehicle_type = VehicleType.parse(vehicle_type)
        return self._managers[vehicle_type]

    def all_managers(self) -> list[ParkingSpotManager]:
        """Every manager, in declaration order, for lot-wide queries."""
        return [self._managers[vehicle_type] for vehicle_type in VehicleType]
