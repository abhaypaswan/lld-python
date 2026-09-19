"""Strategy: which free spot gets handed to the next car through the gate.

This is the decision a lot operator would actually tune -- fill the cheap far
end first, keep the entrance clear, spread cars out. Making it a strategy means
that tuning never touches the gate or the spot manager.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable

from ...model.parking_spot import ParkingSpot


class ParkingStrategy(ABC):
    """Picks one spot out of the free ones, or None when the lot is full."""

    name: str = "strategy"

    @abstractmethod
    def find_parking_spot(self, spots: Iterable[ParkingSpot]) -> ParkingSpot | None:
        """Choose a spot. Must only ever return a spot that is free."""

    @staticmethod
    def _free(spots: Iterable[ParkingSpot]) -> list[ParkingSpot]:
        return [spot for spot in spots if spot.is_free]


class FirstAvailableStrategy(ParkingStrategy):
    """Lowest-numbered free spot. The obvious default."""

    name = "first-available"

    def find_parking_spot(self, spots):
        free = self._free(spots)
        # Sort numerically when the numbers look numeric, so spot 9 comes
        # before spot 10 rather than after it the way string sorting would.
        return min(free, key=_spot_sort_key) if free else None


class NearestParkingStrategy(ParkingStrategy):
    """Even-numbered spots are treated as the ones closest to the entrance.

    Spots 0-9 come out in this order: 0, 2, 4, 6, 8, 1, 3, 5, 7, 9. The real
    thing would read a distance off each spot; this keeps the demo simple while
    still showing a genuinely different ordering from the default.
    """

    name = "nearest"

    def find_parking_spot(self, spots):
        free = self._free(spots)
        if not free:
            return None

        def rank(spot: ParkingSpot):
            key = _spot_sort_key(spot)
            is_odd = 1 if (isinstance(key, int) and key % 2) else 0
            return (is_odd, key)

        return min(free, key=rank)


class FarthestParkingStrategy(ParkingStrategy):
    """Highest-numbered free spot. Useful for long-stay parking."""

    name = "farthest"

    def find_parking_spot(self, spots):
        free = self._free(spots)
        return max(free, key=_spot_sort_key) if free else None


def _spot_sort_key(spot: ParkingSpot):
    """Sort spot "10" after "9", not before it.

    Spot numbers are strings because a real lot uses labels like "B2-014", but
    the demo uses plain integers, and plain string ordering would put 10 ahead
    of 9. Numeric when we can, alphabetical when we cannot.
    """
    number = spot.spot_number
    return int(number) if number.lstrip("-").isdigit() else number


#: Name -> strategy, so a caller can say "nearest" without importing a class.
STRATEGIES: dict[str, type[ParkingStrategy]] = {
    FirstAvailableStrategy.name: FirstAvailableStrategy,
    NearestParkingStrategy.name: NearestParkingStrategy,
    FarthestParkingStrategy.name: FarthestParkingStrategy,
    "default": FirstAvailableStrategy,
}


def get_parking_strategy(name: str = "default") -> ParkingStrategy:
    try:
        return STRATEGIES[name]()
    except KeyError:
        known = ", ".join(sorted(set(STRATEGIES) - {"default"}))
        raise ValueError(f"{name!r} is not a parking strategy. Try one of: {known}") from None
