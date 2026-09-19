"""A controllable clock, so fee tests do not depend on how fast they run."""

import pytest
from parking_lot import ParkingLot

HOUR = 3600


class FakeClock:
    """Starts at zero and only moves when a test tells it to."""

    def __init__(self, now: float = 0.0):
        self.now = now

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> float:
        self.now += seconds
        return self.now


@pytest.fixture
def clock():
    return FakeClock()


@pytest.fixture
def lot(clock):
    """A lot with 10 two-wheeler, 5 four-wheeler and 3 HUV spots."""
    return ParkingLot(clock=clock).create_parking_lot()
