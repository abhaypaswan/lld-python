"""The ticket handed out at the entrance and settled at the exit."""

from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from .parking_spot import ParkingSpot
from .vehicle import Vehicle

_ticket_numbers = itertools.count(1)


@dataclass
class Ticket:
    """Links a vehicle to the spot it occupies, from entry until payment.

    `entry_time` is a plain epoch float that the caller passes in. Reading the
    clock inside the constructor would make every fee calculation untestable,
    so the clock stays outside.
    """

    vehicle: Vehicle
    parking_spot: ParkingSpot
    entry_time: float
    ticket_id: str = field(default="")
    exit_time: float | None = None
    amount_paid: float | None = None

    def __post_init__(self):
        if not self.ticket_id:
            self.ticket_id = f"T-{next(_ticket_numbers):05d}"

    @property
    def spot_number(self) -> str:
        return self.parking_spot.spot_number

    @property
    def is_settled(self) -> bool:
        return self.amount_paid is not None

    def render(self) -> str:
        return "\n".join(
            [
                f"Ticket: {self.ticket_id}",
                f"Registration Number: {self.vehicle.registration_no}",
                f"Vehicle Type: {self.vehicle.vehicle_type}",
                f"Color: {self.vehicle.color}",
                f"Assigned Spot Number: {self.spot_number}",
            ]
        )
