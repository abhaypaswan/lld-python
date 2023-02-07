from abc import ABC, abstractmethod

from components.parking_spot_managers.two_wheeler_parking_spot_manager import TwoWheelerParkingSpotManager 
from components.parking_spot_managers.four_wheeler_parking_spot_manager import FourWheelerParkingSpotManager
from components.parking_spot_managers.huv_parking_spot_manager import HUVParkingSpotManager

class ParkingSpotManagerFactory:
    def __init__(self):
        self.two_wheeler_parking_spot_manager = TwoWheelerParkingSpotManager()
        self.four_wheeler_parking_spot_manager = FourWheelerParkingSpotManager()
        self.huv_parking_spot_manager = HUVParkingSpotManager()
    
    def get_spot_manager(self, vehicle_type):
        if vehicle_type == "TwoWheeler":
            return self.two_wheeler_parking_spot_manager
        elif vehicle_type == "FourWheeler":
            return self.four_wheeler_parking_spot_manager
        elif vehicle_type == "HUV":
            return self.huv_parking_spot_manager
        else:
            raise ValueError("Invalid vehicle_type: {}".format(vehicle_type))