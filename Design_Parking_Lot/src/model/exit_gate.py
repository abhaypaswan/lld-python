import datetime 
import math
import random

from model.ticket import Ticket
from components.factory.parking_spot_manager_factory import ParkingSpotManagerFactory

class ExitGate:
    def __init__(self, parking_spot_manager_factory: ParkingSpotManagerFactory):
        self.parking_spot_manager_factory = parking_spot_manager_factory 

    def free_parking_spot(self, ticket: Ticket): 
        spot_number = ticket.spot_number
        vehicle_type = ticket.vehicle.get_vehicle_type()
        parking_spot_manager = self.parking_spot_manager_factory.get_spot_manager(vehicle_type)
        parking_spot_manager.free_parking_spot(spot_number)

    def cost_computation(self, ticket: Ticket):
        entry_time = ticket.entry_time
        exit_time = datetime.datetime.now().timestamp() 

        """
        When the program is executed, the entry_time and exit_time are almost same, 
        which is not a realistic scenario. To better understand the program, 
        a random number of seconds in the range [1000, 10000] is added to the 
        parking_time calculation to account for this issue.
        """

        parking_time_secs = (exit_time - entry_time) + random.randint(1000, 10000)  # In seconds

        def seconds_to_hours_minutes(seconds):
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return hours, minutes

        parking_time_hrs, parking_time_mins = seconds_to_hours_minutes(parking_time_secs)
        parking_cost = parking_time_hrs * ticket.parking_spot.hour_charge + \
                        parking_time_mins * ticket.parking_spot.min_charge 

        print(f'The vehicle has been parked for {parking_time_hrs} hours and {parking_time_mins} minutes, incurring a cost of {parking_cost}.')

        return parking_cost

    
    def payment(self, ticket: Ticket):
        parking_cost = self.cost_computation(ticket)
        print(f'The parking fee of {parking_cost} was paid in cash.')
        # You payment logic can be written here
        