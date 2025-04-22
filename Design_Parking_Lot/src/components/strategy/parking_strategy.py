from abc import ABC, abstractmethod


class ParkingStrategy(ABC):
    """Abstract base class for parking strategies."""

    @abstractmethod
    def find_parking_spot(self, parking_spot_list: dict):
        pass


class FirstComeFirstServe(ParkingStrategy):
    """Assign the first available parking spot (ordered by insertion or ID)."""

    def find_parking_spot(self, parking_spot_list: dict):
        for spot in parking_spot_list.values():
            if spot.is_empty:
                print(f'FirstComeFirstServe selected Spot: {spot.spot_number}')
                return spot
        print("No available spots.")
        return None

class NearestParkingStrategy(ParkingStrategy):
    """
    Even-numbered spots are considered closer than odd-numbered ones.
    Prioritize even-numbered available spots, then odd-numbered.
    """

    def find_parking_spot(self, parking_spot_list: dict):
        even_spots = sorted(
            [spot for spot in parking_spot_list.values() if spot.is_empty and int(spot.spot_number) % 2 == 0],
            key=lambda x: int(x.spot_number)
        )
        if even_spots:
            print(f'NearestParkingStrategy selected even Spot: {even_spots[0].spot_number}')
            return even_spots[0]

        odd_spots = sorted(
            [spot for spot in parking_spot_list.values() if spot.is_empty and int(spot.spot_number) % 2 != 0],
            key=lambda x: int(x.spot_number)
        )
        if odd_spots:
            print(f'NearestParkingStrategy selected odd Spot: {odd_spots[0].spot_number}')
            return odd_spots[0]

        raise Exception("No available parking spots")


class HighestChargeStrategy(ParkingStrategy):
    """Choose the most expensive available parking spot."""

    def find_parking_spot(self, parking_spot_list: dict):
        available_spots = [
            spot for spot in parking_spot_list.values() if spot.is_empty
        ]
        if not available_spots:
            raise Exception("No available parking spots")

        best_spot = max(available_spots, key=lambda s: s.hour_charge)
        print(f'HighestChargeStrategy selected Spot: {best_spot.spot_number} with charge {best_spot.hour_charge}')
        return best_spot


class RandomStrategy(ParkingStrategy):
    """Choose a random spot from available ones."""

    def find_parking_spot(self, parking_spot_list: dict):
        import random
        available_spots = [
            spot for spot in parking_spot_list.values() if spot.is_empty
        ]
        if not available_spots:
            raise Exception("No available parking spots")
        chosen = random.choice(available_spots)
        print(f'RandomStrategy selected Spot: {chosen.spot_number}')
        return chosen


class ParkingStrategyContext:
    """Context class to select and use a parking strategy."""
    @staticmethod
    def find_parking_spot(parking_spot_list: dict, strategy: str = "default"):
        strategy_map = {
            "default": FirstComeFirstServe(),
            "nearest": NearestParkingStrategy(),
            "expensive": HighestChargeStrategy(),
            "random": RandomStrategy(),
        }

        selected_strategy = strategy_map.get(strategy, FirstComeFirstServe())
        return selected_strategy.find_parking_spot(parking_spot_list)
