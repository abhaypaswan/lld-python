import datetime
from model.parking_spot import *
from model.vehicle import *

class Ticket:
    def __init__(self, vehicle: Vehicle, parking_spot: ParkingSpot):
        self.entry_time = datetime.datetime.now().timestamp()
        self.vehicle = vehicle
        self.parking_spot = parking_spot

    def generate_ticket(self):
        print(f'Entry time: {self.entry_time}')
        print(f'Spot No.: {self.parking_spot.spot_number}') 
        print(f'Vehicle type: {self.vehicle.registration_no}')
        print(f'Vehicle color: {self.vehicle.color}')