from abc import ABC, abstractmethod
from model.parking_spot import ParkingSpot
from components.strategy.parking_strategy import ParkingStrategy
from model.vehicle import *

class ParkingSpotManager:
    @abstractmethod
    def add_parking_spot(self, spot_number):
        pass

    def remove_parking_spot(self, spot_number):
        if spot_number in self.parking_spot_list: 
            if self.parking_spot_list[spot_number].is_empty == False:
                raise ValueError(f"A vehicle is already parked in spot: {spot_number}")
            
        print(f'Available parking spots: {list(self.parking_spot_list.keys())}')
        if spot_number in self.parking_spot_list:
            value = self.parking_spot_list.pop(spot_number, None)
            self.available_spots -= 1
            self.total_spots -= 1
        print(f'After removing spot({spot_number}) from parking spots: {list(self.parking_spot_list.keys())}')

    def is_full(self):
        if self.available_spots == 0: 
            return True
        return False

    def find_parking_spot(self, strategy: str = "default"):
        return ParkingStrategy().find_parking_spot(parking_spot_list=self.parking_spot_list, strategy=strategy)

    def park_vehicle(self, vehicle):
        if self.is_full():
            print("No Parking Spot is available to park this vehicle.")
            return
        parking_spot = self.find_parking_spot()
        parking_spot.park_vehicle(vehicle)
        return parking_spot

    def free_parking_spot(self, spot_number):
        if spot_number in self.parking_spot_list:
            parking_spot = self.parking_spot_list[spot_number]
            parking_spot.remove_vehicle()
            self.available_spots += 1 
            return

        print("This parking spot is not available")

    def get_spots_by_vehicle_color(self, color):
        parking_spots = [
            self.parking_spot_list[key] for key in self.parking_spot_list.keys() 
            if (self.parking_spot_list[key].is_empty==False 
            and self.parking_spot_list[key].vehicle.color==color)
        ]
        return parking_spots

    def get_spot_by_vehicle_registration_no(self, registration_no):
        parking_spot = [
            self.parking_spot_list[key] for key in self.parking_spot_list.keys() 
            if (self.parking_spot_list[key].is_empty==False 
            and self.parking_spot_list[key].vehicle.registration_no==registration_no)
        ]
        return None if (len(parking_spot)==0) else parking_spot[0]

    def list_all_parked_spots(self):
        spots = [
            self.parking_spot_list[key] for key in self.parking_spot_list.keys() if (self.parking_spot_list[key].is_empty==False) 
        ]
        return spots