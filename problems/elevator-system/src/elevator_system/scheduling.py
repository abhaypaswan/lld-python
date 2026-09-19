"""Strategy: which car in the bank answers a hall call.

This is the decision a building operator would actually tune, and it is
completely separate from how a car behaves once it has the job. That separation
is the main structural point of the problem: `Elevator` runs LOOK regardless of
which strategy picked it, and a strategy can be swapped without any car
noticing.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence

from .elevator import Direction, Elevator
from .request import ExternalRequest


class SchedulingStrategy(ABC):
    """Picks a car for a hall call, or None when none can take it."""

    name: str = "strategy"

    @abstractmethod
    def select(self, elevators: Sequence[Elevator], request: ExternalRequest) -> Elevator | None:
        """Choose a car. Must only ever return an available one."""

    @staticmethod
    def _available(elevators: Sequence[Elevator]) -> list[Elevator]:
        return [e for e in elevators if e.is_available]


class NearestCarStrategy(SchedulingStrategy):
    """Fewest floors away. The obvious answer, and often the wrong one.

    It ignores direction, so the nearest car may be travelling away from the
    caller and have to finish its run and come back. `ThroughputStrategy` fixes
    exactly that.
    """

    name = "nearest"

    def select(self, elevators, request):
        available = self._available(elevators)
        if not available:
            return None
        return min(available, key=lambda e: (e.distance_to(request.floor), e.elevator_id))


class LeastBusyStrategy(SchedulingStrategy):
    """Fewest outstanding stops. Spreads load rather than minimising distance.

    Useful when cars are getting overloaded, at the cost of sending a distant
    empty car past three closer busy ones.
    """

    name = "least-busy"

    def select(self, elevators, request):
        available = self._available(elevators)
        if not available:
            return None
        return min(available, key=lambda e: (e.load, e.distance_to(request.floor), e.elevator_id))


class ThroughputStrategy(SchedulingStrategy):
    """Prefer a car already heading the caller's way. The realistic choice.

    Cars are ranked in tiers:

      0. Moving towards the caller, in the direction they want to travel.
         Picking them up costs the car nothing extra -- it was passing anyway.
      1. Idle. Free to start a fresh run.
      2. Anything else. It has to finish its current run first, so the cost is
         the detour, not the distance.

    Within a tier, nearest wins. This is roughly what real controllers do, and
    the reasoning -- that a stop on the way is free and a stop behind you is
    expensive -- is the part worth saying out loud.
    """

    name = "throughput"

    def select(self, elevators, request):
        available = self._available(elevators)
        if not available:
            return None
        return min(
            available, key=lambda e: (self._tier(e, request), self._cost(e, request), e.elevator_id)
        )

    @staticmethod
    def _tier(elevator: Elevator, request: ExternalRequest) -> int:
        if elevator.direction is Direction.IDLE:
            return 1
        same_way = elevator.direction is request.direction
        if same_way and elevator.is_moving_towards(request.floor):
            return 0
        return 2

    @staticmethod
    def _cost(elevator: Elevator, request: ExternalRequest) -> int:
        direct = elevator.distance_to(request.floor)
        if elevator.direction is Direction.IDLE or elevator.is_moving_towards(request.floor):
            return direct

        # Going the wrong way: it must run to the end of its stops and back.
        stops = elevator.stops
        if not stops:
            return direct
        turning_point = max(stops) if elevator.direction is Direction.UP else min(stops)
        return abs(elevator.current_floor - turning_point) + abs(turning_point - request.floor)


STRATEGIES: dict[str, type[SchedulingStrategy]] = {
    NearestCarStrategy.name: NearestCarStrategy,
    LeastBusyStrategy.name: LeastBusyStrategy,
    ThroughputStrategy.name: ThroughputStrategy,
}


def get_strategy(name: str = "throughput") -> SchedulingStrategy:
    try:
        return STRATEGIES[name]()
    except KeyError:
        known = ", ".join(sorted(STRATEGIES))
        raise ValueError(f"{name!r} is not a scheduling strategy. Try one of: {known}") from None
