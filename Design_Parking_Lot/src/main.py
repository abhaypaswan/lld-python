from components.factory.parking_spot_manager_factory import ParkingSpotManagerFactory
from model.entrance_gate import EntranceGate
from model.exit_gate import ExitGate
from commands.commands import Commands

class ParkingLot:
    def __init__(self):
        self.parking_spot_manager_factory = ParkingSpotManagerFactory()
        self.entrance_gate = EntranceGate(self.parking_spot_manager_factory) 
        self.exit_gate = ExitGate(self.parking_spot_manager_factory)

    def create_parking_lot(self):
        tw_spot_manager = self.parking_spot_manager_factory.get_spot_manager("TwoWheeler")
        [tw_spot_manager.add_parking_spot(spot_number=str(i)) for i in range(0,10)]

        fw_spot_manager = self.parking_spot_manager_factory.get_spot_manager("FourWheeler")
        [fw_spot_manager.add_parking_spot(spot_number=str(i)) for i in range(10,15)]

        huv_spot_manager = self.parking_spot_manager_factory.get_spot_manager("HUV")
        [huv_spot_manager.add_parking_spot(spot_number=str(i)) for i in range(15, 18)]

def main():
    parking_lot = ParkingLot()
    parking_lot.create_parking_lot()
    with open("input.txt", "r") as file:
        for line in file:
            command_str = line.strip() # to remove new_line character
            command = Commands(command=command_str,
                        entrance_gate=parking_lot.entrance_gate, 
                        exit_gate=parking_lot.exit_gate, 
                        parking_spot_manager_factory=parking_lot.
                        parking_spot_manager_factory
                    )
            command.execute()


if __name__ == "__main__":
    main()