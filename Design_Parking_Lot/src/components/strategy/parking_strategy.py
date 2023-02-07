from abc import ABC, abstractmethod 

class ParkingStrategy:
    def find_parking_spot(self, parking_spot_list, strategy="default"):
        """default strategy is first come first serve"""
        if strategy == "nearest":
            return NearestParkingStrategy().find_parking_spot(parking_spot_list)
        return FirstComeFirstServe().find_parking_spot(parking_spot_list)

class NearestParkingStrategy:
    """
    For simplicity, the logic assumes that even numbered spots are closest in ascending order and 
    odd numbered spots are farthest away. However, you can implement your own logic as desired.

    As an example, if there are 10 spots numbered from 0 to 9, 
    sorting them in ascending order of proximity would result 
    in the following list: [0, 2, 4, 6, 8, 1, 3, 5, 7, 9].
    """

    def find_parking_spot(self, parking_dict):
        even_keys = [key for key in parking_dict.keys() if key % 2 == 0 and parking_dict[key].is_empty()]
        if even_keys:
            return parking_dict[min(even_keys)]
        else:
            odd_keys = [key for key in parking_dict.keys() if key % 2 != 0 and parking_dict[key].is_empty()]
            return parking_dict[min(odd_keys)]

class FirstComeFirstServe:
    def find_parking_spot(self, parking_spot_list):
        for spot_no, parking_spot in parking_spot_list.items():
            if parking_spot.is_empty:
                print(f'Parking Spot: {parking_spot.spot_number}')
                return parking_spot