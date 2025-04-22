from model.entrance_gate import EntranceGate 
from model.exit_gate import ExitGate

class Commands:
    def __init__(self, command, entrance_gate: EntranceGate, exit_gate: ExitGate, parking_spot_manager_factory):
        self.command = command
        self.entrance_gate = entrance_gate 
        self.exit_gate = exit_gate
        self.parking_spot_manager_factory = parking_spot_manager_factory
        self.command_handlers = {
            'park_vehicle': self._handle_park_vehicle,
            'free_parking_spot': self._handle_free_parking_spot,
            'get_vehicles_by_color': self._handle_get_vehicles_by_color,
            'get_vehicles_by_registration_no': self._handle_get_vehicles_by_registration_no,
            'list_all_parked_vehicles': self._handle_list_all_parked_vehicles,
            'add_parking_spot': self._handle_add_parking_spot,
            'remove_parking_spot': self._handle_remove_parking_spot,
            'generate_report': self._handle_generate_report,
            'exit': self._handle_exit
        }

    """
    These commands are limited in scope and do not encompass all potential test cases. 
    This parking lot is capable of performing a range of actions beyond just these commands, 
    such as issuing tickets, calculating fees, processing payments, etc. These sample commands 
    were written as an initial demonstration and will be refined in the future when testing is complete. 
    Additionally, the output format may not be optimal and will be improved at a later time.
    """
    def execute(self):
        parts = self.command.strip().split(' ')
        cmd = parts[0]

        handler = self.command_handlers.get(cmd)
        if not handler:
            raise ValueError(f'Invalid command: {self.command}')

        handler(parts)

    # === Command Handlers ===

    def _handle_park_vehicle(self, args):
        if len(args) != 4:
            raise ValueError(f'Invalid command: {" ".join(args)}\nSuggested format: park_vehicle <registration_no> <color> <vehicle_type>')
        _, registration_no, color, vehicle_type = args
        self.entrance_gate.park_vehicle(registration_no, color, vehicle_type)

    def _handle_free_parking_spot(self, args):
        if len(args) != 3:
            raise ValueError(f'Invalid command: {" ".join(args)}\nSuggested format: free_parking_spot <spot_number> <vehicle_type>')
        _, spot_number, vehicle_type = args
        manager = self.parking_spot_manager_factory.get_spot_manager(vehicle_type)
        manager.free_parking_spot(spot_number)

    def _handle_get_vehicles_by_color(self, args):
        if len(args) != 2:
            raise ValueError(f'Invalid command: {" ".join(args)}\nSuggested format: get_vehicles_by_color <color>')
        _, color = args
        self.entrance_gate.get_vehicles_by_color(color)

    def _handle_get_vehicles_by_registration_no(self, args):
        if len(args) != 2:
            raise ValueError(f'Invalid command: {" ".join(args)}\nSuggested format: get_vehicles_by_registration_no <registration_no>')
        _, registration_no = args
        self.entrance_gate.get_vehicle_by_registration_no(registration_no)

    def _handle_list_all_parked_vehicles(self, args):
        if len(args) != 1:
            raise ValueError(f'Invalid command: {" ".join(args)}\nSuggested format: list_all_parked_vehicles')
        self.entrance_gate.list_all_parked_vehicles()

    def _handle_add_parking_spot(self, args):
        if len(args) != 3:
            raise ValueError(f'Invalid command: {" ".join(args)}\nSuggested format: add_parking_spot <spot_no> <vehicle_type>')
        _, spot_no, vehicle_type = args
        manager = self.parking_spot_manager_factory.get_spot_manager(vehicle_type)
        manager.add_parking_spot(spot_no)

    def _handle_remove_parking_spot(self, args):
        if len(args) != 3:
            raise ValueError(f'Invalid command: {" ".join(args)}\nSuggested format: remove_parking_spot <spot_no> <vehicle_type>')
        _, spot_no, vehicle_type = args
        manager = self.parking_spot_manager_factory.get_spot_manager(vehicle_type)
        manager.remove_parking_spot(spot_no)

    def _handle_generate_report(self, args):
        report_data = self.entrance_gate.get_report_data()

        print("=" * 20)
        print("PARKING LOT REPORT")
        print("=" * 20)

        total_vehicles = 0

        for vehicle_type, data in report_data.items():
            print(f"\n Vehicle Type: {vehicle_type}")
            print(f"Total Spots     : {data['total_spots']}")
            print(f"Available Spots : {data['available_spots']}")
            print(f"Occupied Spots  : {data['occupied_spots']}")
            print("Parked Vehicles :")

            if not data['vehicles']:
                print("No vehicles parked.")
            else:
                for idx, v in enumerate(data['vehicles'], 1):
                    print(f"  {idx}. RegNo: {v['registration_no']}, Color: {v['color']}, Spot: {v['spot_number']}")

            total_vehicles += data['occupied_spots']

        print("\n Summary:")
        print(f"Total Parked Vehicles: {total_vehicles}")
        print("=" * 20)

    @staticmethod
    def _handle_exit(args):
        exit()
