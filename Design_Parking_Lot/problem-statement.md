# Design a Parking lot with different color of cars

## Problem Description

The goal of this project is to design a parking lot that can efficiently manage the parking and retrieval of vehicles, with the added feature of being able to identify the color of each vehicle and the registration number. The parking lot should also be able to handle different types of vehicles, such as cars, motorcycles, and buses.

## Requirements/Use-Case

- The parking lot should be able to handle different types of vehicles, such as cars, motorcycles, and buses.
- The parking lot should be able to assign a parking spot to a vehicle when it enters the lot and free up the spot when the vehicle exits via command-line input.
- The parking lot should be able to keep track of the number of available spots and display this information via command-line output.
- The parking lot should be able to handle oversize vehicles such as buses.
- The system should be able to identify the color and registration number of each vehicle when it enters the parking lot and store this information for future reference.
- The system should be able to find the registration number of vehicles based on the color of the vehicle via command-line input.
- The system should be able to find the slot number of vehicles based on the color of the vehicle via command-line input.
- The system should be able to generate a report of all parked vehicles and their respective colors and registration numbers via command-line output.

## Example

A driver enters the parking lot with a red car and registration number ABC123, and is assigned to parking spot number 1. Another driver enters the parking lot with a blue car and registration number DEF456, and is assigned to parking spot number 2. The system stores the color information of each car (red and blue) and the registration number along with the respective parking spot number.

## Sample Input/Output
**Input** `park_vehicle ABC-123 Red TwoWheeler`     
**Output**  :
Parking Spot: 0

**Input** `park_vehicle DEF-456 White FourWheeler`       
**Output**  :
Parking Spot: 10

**Input** `list_all_parked_vehicles`      
**Output**  :
Registration Number: ABC-123
Assigned Spot Number: 0
Vehicle Type: TwoWheeler
Color: Red

Registration Number: DEF-456
Assigned Spot Number: 10
Vehicle Type: FourWheeler
Color: White

**Input** : `free_parking_spot 0 TwoWheeler`     
**Output**  :
Parking spot {self.spot_number} is now available!

**Input** : `list_all_parked_vehicles`     
**Output**  :
Registration Number: DEF-456
Assigned Spot Number: 10
Vehicle Type: FourWheeler
Color: White

**Input** : `get_vehicles_by_color White`     
**Output**  :
TwoWheeler of White color is:
FourWheeler of White color is:
RegistrationNo: DEF-456
Assigned Spot Number: 10
HUV of White color is:

**Input** : `get_vehicles_by_registration_no ABC-123`      
**Output**  :
No vehicle found with registration number: ABC-123

**Input** : `get_vehicles_by_registration_no DEF-456`      
**Output**  :
Registration Number: DEF-456
Assigned Spot Number: 10
Color: White

**Input** : `list_all_parked_vehicles`      
**Output**  :
Registration Number: DEF-456
Assigned Spot Number: 10
Vehicle Type: FourWheeler
Color: White

**Input** : `add_parking_spot 13 TwoWheeler`      
**Output**  :

**Input** : `remove_parking_spot 13 TwoWheeler`     
**Output**  :
Available parking spots: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '13']
After removing spot(13) from parking spots: ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']

**Input** : `exit`      
**Output**  :

## Running Instructions
To run the Design Parking Lot project, follow the below steps:
1. Open a terminal/command prompt.
2. Navigate to the project directory by running the following command:
```cd Design_Parking_Lot/src```
3. Run the following command to start the program:
```python3 main.py```

# Contribution Guidelines
We welcome contributions to this project. If you are interested in contributing, here are a few guidelines to follow:

1. Fork the repository to your own GitHub account.
2. Clone the repository to your local machine.
3. Make changes and test thoroughly before pushing your changes.
4. Open a pull request, describing the changes you have made and why you think they should be included in the project.
5. The project maintainers will review the pull request and either merge it or ask for additional changes to be made.

## Outstanding Tasks:
- Add comments to the code.
- Finalize the testing module.
- Rectify the output format.
- Enhance the command set by adding new commands.

If you are interested in contributing to any of these tasks, please feel free to reach out for more information.

