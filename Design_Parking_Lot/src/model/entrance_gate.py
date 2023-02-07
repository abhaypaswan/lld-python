from components.factory.parking_spot_manager_factory import ParkingSpotManagerFactory
from model.ticket import Ticket
from model.vehicle import *

class EntranceGate:
    def __init__(self, parking_spot_manager_factory: ParkingSpotManagerFactory):
        self.parking_spot_manager_factory = parking_spot_manager_factory
    
    def find_parking_spot(self, vehicle_type, strategy="default"):
        parking_spot_manager = self.parking_spot_manager_factory.get_spot_manager(vehicle_type)
        parking_spot = parking_spot_manager.find_parking_spot(strategy=strategy)
        return parking_spot

    def generate_ticket(self, color, registration_no, vehicle_type, strategy="default"):
        vehicle = Vehicle().create_vehicle(color=color, registration_no=registration_no, vehicle_type=vehicle_type)
        parking_spot = self.find_parking_spot(vehicle.vehicle_type, strategy)
        ticket = Ticket(vehicle, parking_spot)
        ticket.generate_ticket() 
        return ticket

    def park_vehicle(self, color, registration_no, vehicle_type):
        vehicle = Vehicle().create_vehicle(color=color, registration_no=registration_no, vehicle_type=vehicle_type)
        parking_spot_manager = self.parking_spot_manager_factory.get_spot_manager(vehicle_type)
        parking_spot_manager.park_vehicle(vehicle)

    def get_vehicles_by_color(self, color, vehicle_type="all"):
        if vehicle_type == "all":
            self.get_vehicles_by_color(color, vehicle_type="TwoWheeler")
            self.get_vehicles_by_color(color, vehicle_type="FourWheeler")
            self.get_vehicles_by_color(color, vehicle_type="HUV")
        elif vehicle_type in ['TwoWheeler', 'FourWheeler', 'HUV']:
            spots = self.parking_spot_manager_factory.get_spot_manager(vehicle_type).get_spots_by_vehicle_color(color)
            print(f'{vehicle_type} of {color} color is:')
            for spot in spots:
                print(f'RegistrationNo: {spot.vehicle.get_vehicle_registration_no()}')
                print(f'Assigned Spot Number: {spot.spot_number}')
        else:
            print('Wrong vehicle type')

    def get_vehicle_by_registration_no(self, registration_no):
        for vehicle_type in ['TwoWheeler', 'FourWheeler', 'HUV']:
            spot = self.parking_spot_manager_factory.get_spot_manager(vehicle_type).get_spot_by_vehicle_registration_no(registration_no)
            if spot:
                print(f'Registration Number: {spot.vehicle.get_vehicle_registration_no()}')
                print(f'Assigned Spot Number: {spot.spot_number}')
                print(f'Color: {spot.vehicle.get_vehicle_color()}')
                return 
        print(f'No vehicle found with registration number: {registration_no}')
        
    def list_all_parked_vehicles(self):
        for vehicle_type in ['TwoWheeler', 'FourWheeler', 'HUV']:
            spots = self.parking_spot_manager_factory.get_spot_manager(vehicle_type).list_all_parked_spots()
            for spot in spots:
                print(f'Registration Number: {spot.vehicle.get_vehicle_registration_no()}')
                print(f'Assigned Spot Number: {spot.spot_number}')
                print(f'Vehicle Type: {spot.vehicle.get_vehicle_type()}')
                print(f'Color: {spot.vehicle.get_vehicle_color()}')
                print('')
