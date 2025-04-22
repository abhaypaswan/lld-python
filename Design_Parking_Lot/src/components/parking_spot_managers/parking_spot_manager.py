from abc import ABC, abstractmethod
from components.strategy.parking_strategy import ParkingStrategyContext


class ParkingSpotManager(ABC):
    def __init__(self):
        self.parking_spot_list = {}
        self.total_spots = 0
        self.available_spots = 0

    @abstractmethod
    def add_parking_spot(self, spot_number):
        pass

    def remove_parking_spot(self, spot_number):
        spot = self.parking_spot_list.get(spot_number)
        if not spot:
            raise KeyError(f"Parking spot {spot_number} does not exist.")

        if not spot.is_empty:
            raise ValueError(f"A vehicle is already parked in spot: {spot_number}")

        self.parking_spot_list.pop(spot_number)
        self.available_spots -= 1
        self.total_spots -= 1
        print(f'Removed spot {spot_number}. Remaining Spots: {list(self.parking_spot_list.keys())}')

    def is_full(self):
        return self.available_spots == 0

    def find_parking_spot(self, strategy: str = "default"):
        return ParkingStrategyContext().find_parking_spot(parking_spot_list=self.parking_spot_list, strategy=strategy)

    def park_vehicle(self, vehicle):
        if self.is_full():
            print("No Parking Spot is available to park this vehicle.")
            return
        parking_spot = self.find_parking_spot()
        parking_spot.park_vehicle(vehicle)
        self.available_spots -= 1
        return parking_spot

    def free_parking_spot(self, spot_number):
        spot = self.parking_spot_list.get(spot_number)
        if not spot:
            print("This parking spot does not exist.")
            return
        if spot.is_empty:
            print("Spot is already empty.")
            return

        spot.remove_vehicle()
        self.available_spots += 1

    def get_spots_by_vehicle_color(self, color):
        return [
            spot for spot in self.parking_spot_list.values()
            if not spot.is_empty and spot.vehicle.color == color
        ]

    def get_spot_by_vehicle_registration_no(self, registration_no):
        for spot in self.parking_spot_list.values():
            if not spot.is_empty and spot.vehicle.registration_no == registration_no:
                return spot
        return None

    def list_all_parked_spots(self):
        return [spot for spot in self.parking_spot_list.values() if not spot.is_empty]