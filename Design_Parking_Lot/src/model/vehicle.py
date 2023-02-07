import abc

class Vehicle(abc.ABC):
    def create_vehicle(self, color, registration_no, vehicle_type):
        if vehicle_type == "TwoWheeler":
            return Bike(color, registration_no)
        if vehicle_type == "FourWheeler":
            return Car(color, registration_no)
        if vehicle_type == "HUV":
            return Bus(color, registration_no)

    def get_vehicle_type(self):
        return self.type

    def get_vehicle_color(self):
        return self.color

    def get_vehicle_registration_no(self):
        return self.registration_no


class Bike(Vehicle):
    def __init__(self, color=None, registration_no=None):
        self.type = "TwoWheeler"
        self.color = color 
        self.registration_no = registration_no

class Car(Vehicle):
    def __init__(self, color=None, registration_no=None):
        self.type = "FourWheeler"
        self.color = color 
        self.registration_no = registration_no

class Bus(Vehicle):
    def __init__(self, color=None, registration_no=None):
        self.type = "HUV"
        self.color = color 
        self.registration_no = registration_no