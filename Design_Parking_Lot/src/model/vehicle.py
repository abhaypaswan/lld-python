import abc

class Vehicle(abc.ABC):
    def __init__(self, color=None, registration_no=None, vehicle_type=None):
        self.type = vehicle_type
        self.color = color
        self.registration_no = registration_no

    @staticmethod
    def create_vehicle(color, registration_no, vehicle_type):
        if vehicle_type == "TwoWheeler":
            return Bike(color, registration_no)
        elif vehicle_type == "FourWheeler":
            return Car(color, registration_no)
        elif vehicle_type == "HUV":
            return Bus(color, registration_no)
        else:
            raise ValueError(f"Unknown vehicle type: {vehicle_type}")

    def get_vehicle_type(self):
        return self.type

    def get_vehicle_color(self):
        return self.color

    def get_vehicle_registration_no(self):
        return self.registration_no


class Bike(Vehicle):
    def __init__(self, color=None, registration_no=None):
        super().__init__(color, registration_no, "TwoWheeler")

class Car(Vehicle):
    def __init__(self, color=None, registration_no=None):
        super().__init__(color, registration_no, "FourWheeler")

class Bus(Vehicle):
    def __init__(self, color=None, registration_no=None):
        super().__init__(color, registration_no, "HUV")
