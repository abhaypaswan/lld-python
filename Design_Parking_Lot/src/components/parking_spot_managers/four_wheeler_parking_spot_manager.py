from components.parking_spot_managers.parking_spot_manager import ParkingSpotManager
from model.parking_spot import FourWheelerParkingSpot

class FourWheelerParkingSpotManager(ParkingSpotManager):

    def add_parking_spot(self, spot_number):
        if spot_number in self.parking_spot_list:
            raise KeyError(f"Spot {spot_number} already exists.")

        self.parking_spot_list[spot_number] = FourWheelerParkingSpot(spot_number=spot_number)
        self.total_spots += 1
        self.available_spots += 1
