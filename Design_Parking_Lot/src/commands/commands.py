from model.entrance_gate import EntranceGate 
from model.exit_gate import ExitGate
from components.factory.parking_spot_manager_factory import ParkingSpotManagerFactory

class Commands:
    def __init__(self, command, entrance_gate: EntranceGate, exit_gate: ExitGate, parking_spot_manager_factory):
        self.command = command
        self.entrance_gate = entrance_gate 
        self.exit_gate = exit_gate
        self.parking_spot_manager_factory = parking_spot_manager_factory

    """
    These commands are limited in scope and do not encompass all potential test cases. 
    This parking lot is capable of performing a range of actions beyond just these commands, 
    such as issuing tickets, calculating fees, processing payments, etc. These sample commands 
    were written as an initial demonstration and will be refined in the future when testing is complete. 
    Additionally, the output format may not be optimal and will be improved at a later time.
    """
    def execute(self):
        command = self.command.split(' ')
        if command[0] == 'park_vehicle':
            if len(command) != 4:
                raise ValueError(f'Invalid command: {self.command}\nSuggested command format: park_vehicle <registration_no> <color> <vehicle_type>')
            self.entrance_gate.park_vehicle(registration_no=command[1], color=command[2], vehicle_type=command[3])

        elif command[0] == 'free_parking_spot':
            if len(command) != 3:
                raise ValueError(f'Invalid command: {self.command}\nSuggested command format: free_parking_spot <spot_number> <vehicle_type>')
            parking_spot_manager = self.parking_spot_manager_factory.get_spot_manager(command[2])
            parking_spot_manager.free_parking_spot(command[1])

        elif command[0] == 'get_vehicles_by_color':
            if len(command) != 2:
                raise ValueError(f'Invalid command: {self.command}\nSuggested command format: get_vehicles_by_color <color>')
            self.entrance_gate.get_vehicles_by_color(color=command[1])
            
        elif command[0] == 'get_vehicles_by_registration_no':
            if len(command) != 2:
                raise ValueError(f'Invalid command: {self.command}\nSuggested command format: get_vehicles_by_registration_no <registration_no>')
            self.entrance_gate.get_vehicle_by_registration_no(command[1])
            
        elif command[0] == 'list_all_parked_vehicles':
            if len(command) != 1:
                raise ValueError(f'Invalid command: {self.command}\nSuggested command format: list_all_parking_vehicles')
            self.entrance_gate.list_all_parked_vehicles()
            
        elif command[0] == 'add_parking_spot':
            if len(command) != 3:
                raise ValueError(f'Invalid command: {self.command}\nSuggested command format: add_parking_spot <spot_no> <vehicle_type>')
            parking_spot_manager = self.parking_spot_manager_factory.get_spot_manager(command[2])
            parking_spot_manager.add_parking_spot(command[1])
            
        elif command[0] == 'remove_parking_spot':
            if len(command) != 3:
                raise ValueError(f'Invalid command: {self.command}\nSuggested command format: remove_parking_spot <spot_no> <vehicle_type>')
            parking_spot_manager = self.parking_spot_manager_factory.get_spot_manager(command[2])
            parking_spot_manager.remove_parking_spot(command[1])
        
        elif command[0] == 'exit':
            exit()

        else:
            raise ValueError(f'Invalid command: {self.command}')