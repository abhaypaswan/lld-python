from abc import ABC, abstractmethod 
from model.vehicle import Vehicle

class ParkingSpot(ABC):

    def park_vehicle(self, vehicle: Vehicle):
        self.is_empty = False 
        self.vehicle = vehicle 
        return self.spot_number

    def remove_vehicle(self):
        self.is_empty = True 
        self.vehicle = Vehicle() 
        print('Parking spot {self.spot_number} is now available!')
        return self.spot_number


class TwoWheelerParkingSpot(ParkingSpot):
    def __init__(self, spot_number, hour_charge=100, min_charge=1, is_empty=True): 
        self.spot_number = spot_number 
        self.vehicle = None
        self.hour_charge = hour_charge
        self.min_charge = min_charge
        self.is_empty = is_empty

class FourWheelerParkingSpot(ParkingSpot):
    def __init__(self, spot_number, hour_charge=200, min_charge=2, is_empty=True): 
        self.spot_number = spot_number 
        self.vehicle = None
        self.hour_charge = hour_charge
        self.min_charge = min_charge
        self.is_empty = is_empty

class HUVParkingSpot(ParkingSpot):
    def __init__(self, spot_number, hour_charge=300, min_charge=3, is_empty=True): 
        self.spot_number = spot_number 
        self.vehicle = None
        self.hour_charge = hour_charge
        self.min_charge = min_charge
        self.is_empty = is_empty