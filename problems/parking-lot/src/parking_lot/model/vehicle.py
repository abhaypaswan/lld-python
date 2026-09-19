"""Vehicles and the categories of spot they fit in."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class VehicleType(Enum):
    """The spot category a vehicle needs.

    This is an enum rather than a bare string so that a typo like
    "Fourwheeler" fails loudly at the edge of the system instead of quietly
    matching nothing three layers down.
    """

    TWO_WHEELER = "TwoWheeler"
    FOUR_WHEELER = "FourWheeler"
    HUV = "HUV"

    @classmethod
    def parse(cls, value: str) -> VehicleType:
        for member in cls:
            if member.value.lower() == value.strip().lower():
                return member
        known = ", ".join(m.value for m in cls)
        raise ValueError(f"{value!r} is not a vehicle type. Try one of: {known}")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class Vehicle:
    """A vehicle, identified by its registration number.

    Frozen because a parked vehicle's plate and colour do not change while it
    sits in the lot, and freezing it means a Ticket can safely hold a reference
    rather than a defensive copy.
    """

    registration_no: str
    color: str
    vehicle_type: VehicleType

    def __post_init__(self):
        if not self.registration_no.strip():
            raise ValueError("A vehicle needs a registration number")
        if not self.color.strip():
            raise ValueError("A vehicle needs a colour")
