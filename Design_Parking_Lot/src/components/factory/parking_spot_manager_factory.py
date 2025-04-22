from components.parking_spot_managers.two_wheeler_parking_spot_manager import TwoWheelerParkingSpotManager
from components.parking_spot_managers.four_wheeler_parking_spot_manager import FourWheelerParkingSpotManager
from components.parking_spot_managers.huv_parking_spot_manager import HUVParkingSpotManager

class ParkingSpotManagerFactory:
    def __init__(self):
        self._registry = {
            "TwoWheeler": TwoWheelerParkingSpotManager(),
            "FourWheeler": FourWheelerParkingSpotManager(),
            "HUV": HUVParkingSpotManager()
        }

    def get_spot_manager(self, vehicle_type: str):
        manager = self._registry.get(vehicle_type)
        if not manager:
            raise ValueError(f"Invalid vehicle type: {vehicle_type}")
        return manager
