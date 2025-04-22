from components.factory.parking_spot_manager_factory import ParkingSpotManagerFactory
from model.ticket import Ticket
from model.vehicle import *

class EntranceGate:
    def __init__(self, parking_spot_manager_factory: ParkingSpotManagerFactory):
        self.parking_spot_manager_factory = parking_spot_manager_factory
        self.supported_vehicle_types = ["TwoWheeler", "FourWheeler", "HUV"]

    def find_parking_spot(self, vehicle_type, strategy="default"):
        return self._get_manager(vehicle_type).find_parking_spot(strategy=strategy)

    def generate_ticket(self, color, registration_no, vehicle_type, strategy="default"):
        vehicle = Vehicle().create_vehicle(color=color, registration_no=registration_no, vehicle_type=vehicle_type)
        parking_spot = self.find_parking_spot(vehicle.vehicle_type, strategy)
        ticket = Ticket(vehicle, parking_spot)
        ticket.generate_ticket() 
        return ticket

    def park_vehicle(self, color, registration_no, vehicle_type):
        vehicle = Vehicle().create_vehicle(color=color, registration_no=registration_no, vehicle_type=vehicle_type)
        self._get_manager(vehicle_type).park_vehicle(vehicle)

    def get_vehicles_by_color(self, color, vehicle_type="all"):
        vehicle_types = self.supported_vehicle_types if vehicle_type == "all" else [vehicle_type]

        for v_type in vehicle_types:
            manager = self._get_manager(v_type)
            spots = manager.get_spots_by_vehicle_color(color)
            if spots:
                print(f'\n{v_type}s with color "{color}":')
                for spot in spots:
                    self._print_vehicle_info(spot)

    def get_vehicle_by_registration_no(self, registration_no):
        for v_type in self.supported_vehicle_types:
            spot = self._get_manager(v_type).get_spot_by_vehicle_registration_no(registration_no)
            if spot:
                print(f'\nVehicle found in {v_type}:')
                self._print_vehicle_info(spot)
                return
        print(f'No vehicle found with registration number: {registration_no}')
        
    def list_all_parked_vehicles(self):
        print("\nList of all parked vehicles:")
        for v_type in self.supported_vehicle_types:
            spots = self._get_manager(v_type).list_all_parked_spots()
            for spot in spots:
                self._print_vehicle_info(spot)

    def get_report_data(self):
        report = {}

        for vehicle_type in self.supported_vehicle_types:
            manager = self.parking_spot_manager_factory.get_spot_manager(vehicle_type)
            parked = manager.list_all_parked_spots()
            total = manager.total_spots
            available = manager.available_spots
            report[vehicle_type] = {
                'total_spots': total,
                'available_spots': available,
                'occupied_spots': total - available,
                'vehicles': [
                    {
                        'registration_no': spot.vehicle.get_vehicle_registration_no(),
                        'color': spot.vehicle.get_vehicle_color(),
                        'spot_number': spot.spot_number
                    } for spot in parked
                ]
            }

        return report

    # --- Helper methods ---
    def _get_manager(self, vehicle_type):
        if vehicle_type not in self.supported_vehicle_types:
            raise ValueError(f"Unsupported vehicle type: {vehicle_type}")
        return self.parking_spot_manager_factory.get_spot_manager(vehicle_type)

    @staticmethod
    def _print_vehicle_info(spot):
        print(f'  Registration No: {spot.vehicle.get_vehicle_registration_no()}')
        print(f'  Spot Number    : {spot.spot_number}')
        print(f'  Vehicle Type   : {spot.vehicle.get_vehicle_type()}')
        print(f'  Color          : {spot.vehicle.get_vehicle_color()}')
