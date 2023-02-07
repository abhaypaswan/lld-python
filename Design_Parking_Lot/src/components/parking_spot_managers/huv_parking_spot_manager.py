from abc import ABC, abstractmethod
from components.parking_spot_managers.parking_spot_manager import ParkingSpotManager
from model.parking_spot import HUVParkingSpot

class HUVParkingSpotManager(ParkingSpotManager):
    def __init__(self):
        self.parking_spot_list = {}
        self.total_spots = 0
        self.available_spots = 0

    def add_parking_spot(self, spot_number):
        parking_spot = HUVParkingSpot(spot_number=spot_number)
        try:
            self.parking_spot_list.update({spot_number: parking_spot})
            self.available_spots += 1
            self.total_spots += 1
        except:
            raise KeyError(f"Parking Spot with this spot number ({spot_number}) already exists")