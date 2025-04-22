import datetime
import random

from model.ticket import Ticket
from components.factory.parking_spot_manager_factory import ParkingSpotManagerFactory

class ExitGate:
    def __init__(self, parking_spot_manager_factory: ParkingSpotManagerFactory):
        self.parking_spot_manager_factory = parking_spot_manager_factory 

    def free_parking_spot(self, ticket: Ticket): 
        spot_number = ticket.parking_spot.spot_number
        vehicle_type = ticket.vehicle.get_vehicle_type()
        parking_spot_manager = self.parking_spot_manager_factory.get_spot_manager(vehicle_type)
        parking_spot_manager.free_parking_spot(spot_number)


    @staticmethod
    def _calculate_parking_duration(entry_time: float, exit_time: float = None):
        if exit_time is None:
            exit_time = datetime.datetime.now().timestamp()
        duration_secs = (exit_time - entry_time) + random.randint(1000, 10000)  # Simulated duration
        hours = int(duration_secs) // 3600
        minutes = (int(duration_secs) % 3600) // 60
        return hours, minutes

    def compute_cost(self, ticket: Ticket):
        hours, minutes = self._calculate_parking_duration(ticket.entry_time)
        cost = (hours * ticket.parking_spot.hour_charge) + (minutes * ticket.parking_spot.min_charge)

        print(
            f"[Cost] Parking duration: {hours}h {minutes}m | "
            f"Rate: ₹{ticket.parking_spot.hour_charge}/hr, ₹{ticket.parking_spot.min_charge}/min | "
            f"Total: ₹{cost}"
        )

        return cost
    
    def payment(self, ticket: Ticket):
        parking_cost = self.compute_cost(ticket)
        print(f'The parking fee of {parking_cost} was paid in cash.')
        # Real payment gateway integration can be added here (QR, Card, UPI, etc.)
        