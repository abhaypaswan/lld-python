"""Command pattern: one class per operation, registered by name.

The previous version of this file was a single `execute()` holding an
if/elif chain. That works, but every new operation edits the same method, the
arity check is copy-pasted per branch, and nothing can be tested in isolation.

Here each command is its own class that declares how many arguments it takes
and returns its output as a string. The dispatcher only has to look a name up
in a dictionary, and adding a command means adding a class -- never editing an
existing one.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..model.vehicle import VehicleType


class CommandError(Exception):
    """A command that could not be parsed or run. Never fatal to the session."""


class Command(ABC):
    """One operation a user can type."""

    #: The word typed at the start of the line.
    name: str = ""
    #: Argument names, used for both the arity check and the usage message.
    arguments: tuple[str, ...] = ()
    help: str = ""

    def __init__(self, lot):
        self.lot = lot

    @property
    def usage(self) -> str:
        return " ".join((self.name, *(f"<{a}>" for a in self.arguments)))

    def run(self, args: list[str]) -> str:
        if len(args) != len(self.arguments):
            raise CommandError(
                f"{self.name} takes {len(self.arguments)} argument(s).\nUsage: {self.usage}"
            )
        return self.execute(*args)

    @abstractmethod
    def execute(self, *args: str) -> str:
        """Do the work and return what should be shown to the user."""


class ParkVehicleCommand(Command):
    name = "park_vehicle"
    arguments = ("registration_no", "color", "vehicle_type")
    help = "Park a vehicle and issue a ticket."

    def execute(self, registration_no, color, vehicle_type):
        ticket = self.lot.park(registration_no, color, vehicle_type)
        return f"Parking Spot: {ticket.spot_number}\nTicket: {ticket.ticket_id}"


class UnparkVehicleCommand(Command):
    name = "unpark_vehicle"
    arguments = ("registration_no",)
    help = "Check a vehicle out, charge for the stay, and free its spot."

    def execute(self, registration_no):
        ticket, fee = self.lot.unpark(registration_no)
        return (
            f"{ticket.vehicle.registration_no} left spot {ticket.spot_number}.\n"
            f"Parking fee: {fee:g}"
        )


class FreeParkingSpotCommand(Command):
    name = "free_parking_spot"
    arguments = ("spot_number", "vehicle_type")
    help = "Free a spot directly, without charging for it."

    def execute(self, spot_number, vehicle_type):
        manager = self.lot.factory.get_spot_manager(vehicle_type)
        vehicle = manager.free_parking_spot(spot_number)
        return f"Parking spot {spot_number} is now available ({vehicle.registration_no} has left)."


class AddParkingSpotCommand(Command):
    name = "add_parking_spot"
    arguments = ("spot_number", "vehicle_type")
    help = "Add a new spot to the lot."

    def execute(self, spot_number, vehicle_type):
        manager = self.lot.factory.get_spot_manager(vehicle_type)
        manager.add_parking_spot(spot_number)
        return f"Added {vehicle_type} spot {spot_number}. Total: {manager.total_spots}."


class RemoveParkingSpotCommand(Command):
    name = "remove_parking_spot"
    arguments = ("spot_number", "vehicle_type")
    help = "Take a spot out of service. Only works when the spot is empty."

    def execute(self, spot_number, vehicle_type):
        manager = self.lot.factory.get_spot_manager(vehicle_type)
        manager.remove_parking_spot(spot_number)
        return f"Removed {vehicle_type} spot {spot_number}. Total: {manager.total_spots}."


class ListAllParkedVehiclesCommand(Command):
    name = "list_all_parked_vehicles"
    help = "Show every vehicle currently in the lot."

    def execute(self):
        spots = self.lot.occupied_spots()
        if not spots:
            return "The parking lot is empty."

        blocks = [
            "\n".join(
                [
                    f"Registration Number: {spot.vehicle.registration_no}",
                    f"Assigned Spot Number: {spot.spot_number}",
                    f"Vehicle Type: {spot.vehicle.vehicle_type}",
                    f"Color: {spot.vehicle.color}",
                ]
            )
            for spot in spots
        ]
        return "\n\n".join(blocks)


class GetVehiclesByColorCommand(Command):
    name = "get_vehicles_by_color"
    arguments = ("color",)
    help = "Find every parked vehicle of a given colour."

    def execute(self, color):
        lines = []
        for manager in self.lot.factory.all_managers():
            spots = manager.spots_by_color(color)
            lines.append(f"{manager.vehicle_type} of {color} color:")
            if not spots:
                lines.append("  (none)")
            for spot in spots:
                lines.append(f"  RegistrationNo: {spot.vehicle.registration_no}")
                lines.append(f"  Assigned Spot Number: {spot.spot_number}")
        return "\n".join(lines)


class GetVehicleByRegistrationNoCommand(Command):
    name = "get_vehicles_by_registration_no"
    arguments = ("registration_no",)
    help = "Look a vehicle up by its plate."

    def execute(self, registration_no):
        spot = self.lot.find_spot_by_registration_no(registration_no)
        if spot is None:
            return f"No vehicle found with registration number: {registration_no}"

        return "\n".join(
            [
                f"Registration Number: {spot.vehicle.registration_no}",
                f"Assigned Spot Number: {spot.spot_number}",
                f"Color: {spot.vehicle.color}",
            ]
        )


class StatusCommand(Command):
    name = "status"
    help = "Show how full each section of the lot is."

    def execute(self):
        lines = []
        for manager in self.lot.factory.all_managers():
            lines.append(
                f"{manager.vehicle_type}: {manager.available_spots} free of {manager.total_spots}"
            )
        return "\n".join(lines)


class HelpCommand(Command):
    name = "help"
    help = "List every command."

    def execute(self):
        return "\n".join(
            f"  {command.usage:<58} {command.help}"
            for command in sorted(self.lot.commands.values(), key=lambda c: c.name)
        )


#: Every command the lot understands. Adding one here is the only wiring needed.
COMMAND_CLASSES: tuple[type[Command], ...] = (
    ParkVehicleCommand,
    UnparkVehicleCommand,
    FreeParkingSpotCommand,
    AddParkingSpotCommand,
    RemoveParkingSpotCommand,
    ListAllParkedVehiclesCommand,
    GetVehiclesByColorCommand,
    GetVehicleByRegistrationNoCommand,
    StatusCommand,
    HelpCommand,
)

__all__ = ["Command", "CommandError", "COMMAND_CLASSES", "VehicleType"]
