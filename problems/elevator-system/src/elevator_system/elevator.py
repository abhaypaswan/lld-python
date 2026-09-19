"""One car: where it is, where it is going, and how it decides."""

from __future__ import annotations

from enum import Enum


class Direction(Enum):
    UP = 1
    DOWN = -1
    IDLE = 0

    @property
    def opposite(self) -> Direction:
        if self is Direction.UP:
            return Direction.DOWN
        if self is Direction.DOWN:
            return Direction.UP
        return Direction.IDLE

    def __str__(self) -> str:
        return self.name.lower()


class ElevatorState(Enum):
    """What the car is doing right now.

    An enum rather than a class per state, unlike the vending machine. The
    difference is that here the states share almost all their behaviour -- the
    interesting logic is in choosing the next stop, not in which actions each
    state permits. A four-class hierarchy would be ceremony around one `match`.
    """

    IDLE = "idle"
    MOVING = "moving"
    DOORS_OPEN = "doors-open"
    MAINTENANCE = "maintenance"

    def __str__(self) -> str:
        return self.value


class Elevator:
    """A single car running the LOOK algorithm.

    LOOK (a refinement of SCAN, the classic disk-head algorithm) is what real
    elevators do: keep travelling in one direction, serving every stop on the
    way, and only reverse when there is nothing further ahead.

    The alternative -- always go to the nearest request -- is worse than it
    sounds. A car on floor 5 with calls on 4 and 20 serves 4, then starts
    towards 20, and a new call on 3 drags it back down. Somebody on 20 can wait
    indefinitely while the car oscillates in the lobby. LOOK cannot starve
    anyone, because a stop ahead of the car is always reached before the car
    turns around.
    """

    def __init__(
        self,
        elevator_id: str,
        current_floor: int = 0,
        min_floor: int = 0,
        max_floor: int = 10,
        capacity: int = 8,
    ):
        if not min_floor <= current_floor <= max_floor:
            raise ValueError(f"Floor {current_floor} is outside the range {min_floor}-{max_floor}")

        self.elevator_id = elevator_id
        self.current_floor = current_floor
        self.min_floor = min_floor
        self.max_floor = max_floor
        self.capacity = capacity

        self.direction = Direction.IDLE
        self.state = ElevatorState.IDLE
        self.occupants = 0

        # Stops are split by travel direction. Keeping them apart is what makes
        # "is there anything further in the direction I am already going?" a
        # cheap question rather than a scan with comparisons.
        self._up_stops: set[int] = set()
        self._down_stops: set[int] = set()
        self.floors_travelled = 0
        self.stops_served: list[int] = []

    # -- reading ----------------------------------------------------------

    @property
    def stops(self) -> set[int]:
        return self._up_stops | self._down_stops

    @property
    def is_idle(self) -> bool:
        return not self.stops and self.state is not ElevatorState.MAINTENANCE

    @property
    def is_available(self) -> bool:
        return self.state is not ElevatorState.MAINTENANCE and self.occupants < self.capacity

    @property
    def load(self) -> int:
        return len(self.stops)

    def distance_to(self, floor: int) -> int:
        return abs(self.current_floor - floor)

    def is_moving_towards(self, floor: int) -> bool:
        """Whether `floor` lies ahead of the car in its current direction."""
        if self.direction is Direction.UP:
            return floor >= self.current_floor
        if self.direction is Direction.DOWN:
            return floor <= self.current_floor
        return True

    # -- accepting work ---------------------------------------------------

    def request_floor(self, floor: int, direction: Direction | None = None) -> None:
        """Add a stop. `direction` says which way the rider wants to travel."""
        if not self.min_floor <= floor <= self.max_floor:
            raise ValueError(
                f"Floor {floor} is outside the range {self.min_floor}-{self.max_floor}"
            )
        if self.state is ElevatorState.MAINTENANCE:
            raise ValueError(f"{self.elevator_id} is out of service")

        if direction is None or direction is Direction.IDLE:
            # A car call: sort it by where it is relative to us right now.
            direction = Direction.UP if floor >= self.current_floor else Direction.DOWN

        if direction is Direction.UP:
            self._up_stops.add(floor)
        else:
            self._down_stops.add(floor)

        if self.direction is Direction.IDLE:
            self.direction = self._choose_direction()
            if self.direction is not Direction.IDLE:
                self.state = ElevatorState.MOVING

    def _choose_direction(self) -> Direction:
        """Which way to set off from a standstill."""
        if not self.stops:
            return Direction.IDLE

        nearest = min(self.stops, key=lambda floor: abs(floor - self.current_floor))
        if nearest > self.current_floor:
            return Direction.UP
        if nearest < self.current_floor:
            return Direction.DOWN
        return Direction.UP if self.current_floor in self._up_stops else Direction.DOWN

    # -- running ----------------------------------------------------------

    def step(self) -> int | None:
        """Advance one floor, or open the doors. Returns the floor served.

        One call is one tick. Driving the simulation a tick at a time is what
        makes this testable: a `run()` that loops internally can only be
        checked by its end state.
        """
        if self.state is ElevatorState.MAINTENANCE:
            return None

        if self.state is ElevatorState.DOORS_OPEN:
            self.state = ElevatorState.MOVING if self.stops else ElevatorState.IDLE
            if not self.stops:
                self.direction = Direction.IDLE
            return None

        if not self.stops:
            self.direction = Direction.IDLE
            self.state = ElevatorState.IDLE
            return None

        if self._should_stop_here():
            return self._open_doors()

        if not self._anything_ahead():
            # Nothing further this way. Reverse rather than idling -- this is
            # the turn in LOOK, and it is what bounds everyone's wait.
            self.direction = self.direction.opposite
            if self._should_stop_here():
                return self._open_doors()

        self.current_floor += self.direction.value
        self.floors_travelled += 1

        if self._should_stop_here():
            return self._open_doors()
        return None

    def _should_stop_here(self) -> bool:
        """Serve a stop only if it is in the direction we are travelling.

        A car going up past floor 5 must not pick up someone on 5 who pressed
        *down* -- they would be carried the wrong way. Real elevators get this
        right and it is the detail most implementations miss.
        """
        if self.direction is Direction.UP:
            return self.current_floor in self._up_stops
        if self.direction is Direction.DOWN:
            return self.current_floor in self._down_stops
        return self.current_floor in self.stops

    def _open_doors(self) -> int:
        floor = self.current_floor

        if self.direction is Direction.DOWN:
            self._down_stops.discard(floor)
        else:
            self._up_stops.discard(floor)
        # A car call added by someone inside lands in whichever set matched its
        # direction at the time, so clear both to be sure the floor is done.
        if not self._anything_ahead():
            self._up_stops.discard(floor)
            self._down_stops.discard(floor)

        self.state = ElevatorState.DOORS_OPEN
        self.stops_served.append(floor)
        return floor

    def _anything_ahead(self) -> bool:
        if self.direction is Direction.UP:
            return any(stop > self.current_floor for stop in self.stops)
        if self.direction is Direction.DOWN:
            return any(stop < self.current_floor for stop in self.stops)
        return bool(self.stops)

    # -- operations -------------------------------------------------------

    def take_out_of_service(self) -> None:
        self.state = ElevatorState.MAINTENANCE
        self.direction = Direction.IDLE
        self._up_stops.clear()
        self._down_stops.clear()

    def return_to_service(self) -> None:
        if self.state is ElevatorState.MAINTENANCE:
            self.state = ElevatorState.IDLE

    def __str__(self) -> str:
        arrow = {Direction.UP: "^", Direction.DOWN: "v", Direction.IDLE: "-"}[self.direction]
        stops = ",".join(str(s) for s in sorted(self.stops)) or "-"
        return f"{self.elevator_id} @{self.current_floor}{arrow} [{self.state}] stops:{stops}"
