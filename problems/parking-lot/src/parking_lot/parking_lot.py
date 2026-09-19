"""Facade: the one object the outside world talks to.

Everything underneath -- factory, managers, strategies, gates -- is reachable
from here, but a caller who just wants to park a car should not have to know
that a ParkingSpotManagerFactory exists.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from .commands.commands import COMMAND_CLASSES, Command, CommandError
from .components.factory.parking_spot_manager_factory import ParkingSpotManagerFactory
from .components.strategy.parking_strategy import ParkingStrategy, get_parking_strategy
from .components.strategy.pricing_strategy import PricingStrategy, get_pricing_strategy
from .model.gate import EntranceGate, ExitGate
from .model.parking_spot import ParkingSpot
from .model.ticket import Ticket
from .model.vehicle import VehicleType


class ParkingLot:
    """A whole parking lot: spots, gates, live tickets and a command console."""

    def __init__(
        self,
        parking_strategy: ParkingStrategy | str | None = None,
        pricing_strategy: PricingStrategy | str | None = None,
        clock: Callable[[], float] = time.time,
    ):
        self.clock = clock
        self.factory = ParkingSpotManagerFactory(_as_parking_strategy(parking_strategy))
        self.entrance_gate = EntranceGate(self.factory, clock=clock)
        self.exit_gate = ExitGate(
            self.factory, pricing=_as_pricing_strategy(pricing_strategy), clock=clock
        )

        #: Open tickets, keyed by registration number.
        self.active_tickets: dict[str, Ticket] = {}
        self.commands: dict[str, Command] = {
            command_class.name: command_class(self) for command_class in COMMAND_CLASSES
        }

    # -- setup ------------------------------------------------------------

    def create_parking_lot(
        self, two_wheeler: int = 10, four_wheeler: int = 5, huv: int = 3
    ) -> ParkingLot:
        """Lay out a lot with numbered spots, two-wheelers first."""
        layout = [
            (VehicleType.TWO_WHEELER, two_wheeler),
            (VehicleType.FOUR_WHEELER, four_wheeler),
            (VehicleType.HUV, huv),
        ]

        next_number = 0
        for vehicle_type, count in layout:
            manager = self.factory.get_spot_manager(vehicle_type)
            for _ in range(count):
                manager.add_parking_spot(str(next_number))
                next_number += 1

        return self

    # -- the things people actually want to do ----------------------------

    def park(
        self,
        registration_no: str,
        color: str,
        vehicle_type: str | VehicleType,
        strategy: ParkingStrategy | str | None = None,
    ) -> Ticket:
        ticket = self.entrance_gate.park_vehicle(registration_no, color, vehicle_type, strategy)
        self.active_tickets[ticket.vehicle.registration_no] = ticket
        return ticket

    def unpark(self, registration_no: str, exit_time: float | None = None) -> tuple[Ticket, float]:
        """Check a vehicle out. Returns its ticket and what it was charged."""
        plate = registration_no.strip().upper()
        ticket = self.active_tickets.get(plate)
        if ticket is None:
            raise KeyError(f"No open ticket for {plate}")

        fee = self.exit_gate.checkout(ticket, exit_time)
        del self.active_tickets[plate]
        return ticket, fee

    # -- queries ----------------------------------------------------------

    def occupied_spots(self) -> list[ParkingSpot]:
        return [
            spot for manager in self.factory.all_managers() for spot in manager.occupied_spots()
        ]

    def find_spot_by_registration_no(self, registration_no: str) -> ParkingSpot | None:
        for manager in self.factory.all_managers():
            spot = manager.spot_by_registration_no(registration_no)
            if spot is not None:
                return spot
        return None

    @property
    def available_spots(self) -> int:
        return sum(manager.available_spots for manager in self.factory.all_managers())

    @property
    def total_spots(self) -> int:
        return sum(manager.total_spots for manager in self.factory.all_managers())

    # -- the console ------------------------------------------------------

    def execute(self, line: str) -> str:
        """Run one typed command line and return its output.

        Returning a string rather than printing is what lets the tests drive the
        whole console without capturing stdout.
        """
        parts = line.strip().split()
        if not parts:
            return ""

        name, args = parts[0], parts[1:]
        command = self.commands.get(name)
        if command is None:
            known = ", ".join(sorted(self.commands))
            raise CommandError(f"Unknown command: {name}\nKnown commands: {known}")

        return command.run(args)


def _as_parking_strategy(value) -> ParkingStrategy | None:
    if value is None or isinstance(value, ParkingStrategy):
        return value
    return get_parking_strategy(value)


def _as_pricing_strategy(value) -> PricingStrategy | None:
    if value is None or isinstance(value, PricingStrategy):
        return value
    return get_pricing_strategy(value)
