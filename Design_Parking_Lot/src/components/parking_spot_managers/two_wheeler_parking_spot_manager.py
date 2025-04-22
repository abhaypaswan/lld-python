from abc import ABC, abstractmethod
from components.parking_spot_managers.parking_spot_manager import ParkingSpotManager
from model.parking_spot import TwoWheelerParkingSpot
from model.vehicle import *

class TwoWheelerParkingSpotManager(ParkingSpotManager):

    def add_parking_spot(self, spot_number):
        if spot_number in self.parking_spot_list:
            raise KeyError(f"Spot {spot_number} already exists.")

        self.parking_spot_list[spot_number] = TwoWheelerParkingSpot(spot_number=spot_number)
        self.total_spots += 1
        self.available_spots += 1