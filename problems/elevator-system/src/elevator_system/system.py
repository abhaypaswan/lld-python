"""The bank: dispatches hall calls and drives every car one tick at a time."""

from __future__ import annotations

from .elevator import Direction, Elevator
from .request import ExternalRequest, InternalRequest
from .scheduling import SchedulingStrategy, get_strategy


class ElevatorSystem:
    """A building's elevators, plus the controller in front of them."""

    def __init__(
        self,
        elevator_count: int = 3,
        min_floor: int = 0,
        max_floor: int = 10,
        strategy: SchedulingStrategy | str = "throughput",
        capacity: int = 8,
    ):
        if elevator_count < 1:
            raise ValueError(f"A building needs at least one elevator, got {elevator_count}")

        self.min_floor = min_floor
        self.max_floor = max_floor
        self.strategy = get_strategy(strategy) if isinstance(strategy, str) else strategy

        self.elevators = [
            Elevator(f"E{i + 1}", min_floor, min_floor, max_floor, capacity)
            for i in range(elevator_count)
        ]
        #: Hall calls no car could take yet. Retried on every tick.
        self.pending: list[ExternalRequest] = []
        self.ticks = 0
        self._observers: list = []

    def subscribe(self, observer) -> None:
        """Observer: called with (elevator, floor) each time a car serves a stop."""
        self._observers.append(observer)

    def get(self, elevator_id: str) -> Elevator:
        for elevator in self.elevators:
            if elevator.elevator_id == elevator_id:
                return elevator
        known = ", ".join(e.elevator_id for e in self.elevators)
        raise KeyError(f"No elevator {elevator_id!r}. This building has: {known}")

    # -- requests ---------------------------------------------------------

    def request_elevator(self, floor: int, direction: Direction) -> Elevator | None:
        """A hall call. Returns the car assigned, or None if all are busy."""
        if not self.min_floor <= floor <= self.max_floor:
            raise ValueError(f"Floor {floor} is outside {self.min_floor}-{self.max_floor}")

        request = ExternalRequest(floor, direction)
        elevator = self.strategy.select(self.elevators, request)

        if elevator is None:
            # Queued rather than dropped. A full building must not lose calls.
            self.pending.append(request)
            return None

        elevator.request_floor(floor, direction)
        return elevator

    def select_floor(self, elevator_id: str, floor: int) -> None:
        """A car call, from inside a specific elevator."""
        self.get(elevator_id).request_floor(floor)
        InternalRequest(elevator_id, floor)

    # -- running ----------------------------------------------------------

    def step(self) -> dict[str, int]:
        """Advance every car one tick. Returns {elevator_id: floor served}."""
        self.ticks += 1
        self._retry_pending()

        served = {}
        for elevator in self.elevators:
            floor = elevator.step()
            if floor is not None:
                served[elevator.elevator_id] = floor
                for observer in self._observers:
                    observer(elevator, floor)
        return served

    def _retry_pending(self) -> None:
        still_pending = []
        for request in self.pending:
            elevator = self.strategy.select(self.elevators, request)
            if elevator is None:
                still_pending.append(request)
            else:
                elevator.request_floor(request.floor, request.direction)
        self.pending = still_pending

    def run_until_idle(self, max_ticks: int = 1000) -> int:
        """Tick until everything is served. Returns the tick count."""
        for tick in range(max_ticks):
            if self.is_idle:
                return tick
            self.step()

        raise RuntimeError(f"Still busy after {max_ticks} ticks. Something is not making progress.")

    @property
    def is_idle(self) -> bool:
        return not self.pending and all(e.is_idle for e in self.elevators)

    def status(self) -> str:
        lines = [f"tick {self.ticks}"] + [f"  {e}" for e in self.elevators]
        if self.pending:
            lines.append(f"  pending: {', '.join(str(r) for r in self.pending)}")
        return "\n".join(lines)
