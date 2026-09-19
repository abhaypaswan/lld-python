"""The two doors into the system.

Splitting entry from exit is not ceremony. They have genuinely different jobs:
the entrance decides where a car goes, the exit decides what it costs. Keeping
them apart means a change to pricing cannot break parking.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from ..components.factory.parking_spot_manager_factory import ParkingSpotManagerFactory
from ..components.factory.vehicle_factory import VehicleFactory
from ..components.strategy.parking_strategy import ParkingStrategy
from ..components.strategy.pricing_strategy import PricingStrategy, get_pricing_strategy
from .parking_spot import ParkingSpot
from .ticket import Ticket
from .vehicle import Vehicle, VehicleType


class EntranceGate:
    """Takes a vehicle in and issues a ticket.

    `clock` is injected so tests can control entry and exit timestamps. A gate
    that calls time.time() internally cannot be tested for anything involving
    duration, which is most of what an exit gate does.
    """

    def __init__(
        self,
        factory: ParkingSpotManagerFactory,
        clock: Callable[[], float] = time.time,
    ):
        self.factory = factory
        self.clock = clock

    def find_parking_spot(
        self, vehicle_type: str | VehicleType, strategy: ParkingStrategy | str | None = None
    ) -> ParkingSpot | None:
        return self.factory.get_spot_manager(vehicle_type).find_parking_spot(strategy)

    def park_vehicle(
        self,
        registration_no: str,
        color: str,
        vehicle_type: str | VehicleType,
        strategy: ParkingStrategy | str | None = None,
    ) -> Ticket:
        vehicle = VehicleFactory.create(registration_no, color, vehicle_type)
        manager = self.factory.get_spot_manager(vehicle.vehicle_type)
        spot = manager.park_vehicle(vehicle, strategy)

        return Ticket(vehicle=vehicle, parking_spot=spot, entry_time=self.clock())


class ExitGate:
    """Prices a stay, takes the payment, and frees the spot."""

    def __init__(
        self,
        factory: ParkingSpotManagerFactory,
        pricing: PricingStrategy | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.factory = factory
        self.pricing = pricing or get_pricing_strategy()
        self.clock = clock

    def calculate_fee(self, ticket: Ticket, exit_time: float | None = None) -> float:
        return self.pricing.calculate(ticket, exit_time if exit_time is not None else self.clock())

    def checkout(self, ticket: Ticket, exit_time: float | None = None) -> float:
        """Settle the ticket and release the spot. Returns the fee charged."""
        if ticket.is_settled:
            raise ValueError(f"Ticket {ticket.ticket_id} has already been paid")

        exit_time = exit_time if exit_time is not None else self.clock()
        fee = self.pricing.calculate(ticket, exit_time)

        manager = self.factory.get_spot_manager(ticket.vehicle.vehicle_type)
        manager.free_parking_spot(ticket.spot_number)

        ticket.exit_time = exit_time
        ticket.amount_paid = fee
        return fee

    def free_parking_spot(self, ticket: Ticket) -> Vehicle:
        """Release a spot without charging for it."""
        manager = self.factory.get_spot_manager(ticket.vehicle.vehicle_type)
        return manager.free_parking_spot(ticket.spot_number)
