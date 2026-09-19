"""The LOOK algorithm inside a car, and the scheduler in front of the bank."""

import pytest
from elevator_system import (
    Direction,
    Elevator,
    ElevatorState,
    ElevatorSystem,
    ExternalRequest,
    LeastBusyStrategy,
    NearestCarStrategy,
    ThroughputStrategy,
)
from elevator_system.scheduling import get_strategy


def run(elevator, ticks=60):
    """Tick a single car until it goes idle."""
    for _ in range(ticks):
        if elevator.is_idle and elevator.state is ElevatorState.IDLE:
            return elevator.stops_served
        elevator.step()
    raise AssertionError(f"still busy after {ticks} ticks: {elevator}")


@pytest.fixture
def car():
    return Elevator("E1", current_floor=0, min_floor=0, max_floor=10)


# -- one car --------------------------------------------------------------


def test_a_new_car_is_idle(car):
    assert car.is_idle
    assert car.direction is Direction.IDLE


def test_a_car_goes_to_the_floor_it_was_asked_for(car):
    car.request_floor(5)

    assert run(car) == [5]
    assert car.current_floor == 5


def test_a_car_serves_stops_on_the_way_up_in_order(car):
    for floor in (7, 3, 5):
        car.request_floor(floor, Direction.UP)

    assert run(car) == [3, 5, 7], "LOOK sweeps, it does not chase the nearest"


def test_a_car_serves_stops_on_the_way_down_in_order(car):
    car.current_floor = 10
    for floor in (2, 8, 5):
        car.request_floor(floor, Direction.DOWN)

    assert run(car) == [8, 5, 2]


def test_a_car_finishes_its_sweep_before_reversing(car):
    car.current_floor = 5
    car.request_floor(8, Direction.UP)
    car.request_floor(2, Direction.DOWN)

    assert run(car) == [8, 2], "it must not turn back for 2 before reaching 8"


def test_a_stop_added_ahead_mid_journey_is_picked_up(car):
    car.request_floor(9, Direction.UP)
    car.step()
    car.step()
    car.request_floor(4, Direction.UP)

    assert run(car) == [4, 9]


def test_a_car_going_up_does_not_pick_up_someone_going_down(car):
    """The detail most implementations miss: direction, not just floor."""
    car.request_floor(9, Direction.UP)
    car.request_floor(5, Direction.DOWN)

    served = run(car)

    assert served.index(9) < served.index(5), "5-going-down is served on the way back"


def test_nobody_is_starved_by_a_stream_of_nearby_calls(car):
    """The failure mode that rules out always-serve-the-nearest."""
    car.current_floor = 5
    car.request_floor(10, Direction.UP)

    for _ in range(3):
        car.step()
        car.request_floor(4, Direction.DOWN)

    served = run(car)

    assert 10 in served
    assert served.index(10) < served.index(4)


def test_a_floor_outside_the_building_is_rejected(car):
    with pytest.raises(ValueError, match="outside the range 0-10"):
        car.request_floor(11)


def test_a_car_cannot_start_outside_its_own_range():
    with pytest.raises(ValueError, match="outside the range"):
        Elevator("E1", current_floor=20, min_floor=0, max_floor=10)


def test_a_car_in_maintenance_takes_no_requests(car):
    car.take_out_of_service()

    with pytest.raises(ValueError, match="out of service"):
        car.request_floor(5)


def test_maintenance_drops_outstanding_stops(car):
    car.request_floor(5)
    car.take_out_of_service()

    assert car.stops == set()
    assert car.step() is None


def test_a_car_comes_back_into_service(car):
    car.take_out_of_service()
    car.return_to_service()

    car.request_floor(5)
    assert run(car) == [5]


def test_a_car_ends_idle_with_no_direction(car):
    car.request_floor(3)
    run(car)

    assert car.direction is Direction.IDLE
    assert car.state is ElevatorState.IDLE


def test_travel_distance_is_tracked(car):
    car.request_floor(4)
    run(car)

    assert car.floors_travelled == 4


# -- requests -------------------------------------------------------------


def test_a_hall_call_must_state_a_direction():
    with pytest.raises(ValueError, match="must be up or down"):
        ExternalRequest(3, Direction.IDLE)


# -- scheduling -----------------------------------------------------------


def make_bank(*positions):
    system = ElevatorSystem(len(positions), 0, 20)
    for elevator, floor in zip(system.elevators, positions, strict=False):
        elevator.current_floor = floor
    return system


def test_nearest_picks_the_closest_car():
    system = make_bank(0, 8, 15)
    system.strategy = NearestCarStrategy()

    assert system.request_elevator(9, Direction.UP).elevator_id == "E2"


def test_least_busy_spreads_the_load():
    system = make_bank(0, 1, 2)
    system.strategy = LeastBusyStrategy()
    for floor in (5, 7, 9):
        system.elevators[0].request_floor(floor, Direction.UP)
    system.elevators[1].request_floor(6, Direction.UP)

    # E3 is furthest away but has nothing to do.
    assert system.request_elevator(3, Direction.UP).elevator_id == "E3"


def test_throughput_prefers_a_car_already_heading_your_way():
    system = make_bank(0, 10)
    system.strategy = ThroughputStrategy()
    # E1 is heading up past floor 8; E2 sits idle at 10, one floor closer.
    system.elevators[0].request_floor(20, Direction.UP)
    system.elevators[0].step()

    chosen = system.request_elevator(8, Direction.UP)

    assert chosen.elevator_id == "E1", "a stop on the way costs nothing extra"


def test_throughput_skips_a_car_travelling_the_wrong_way():
    system = make_bank(10, 0)
    system.strategy = ThroughputStrategy()
    # E1 is close but heading down, away from a caller who wants to go up.
    system.elevators[0].request_floor(0, Direction.DOWN)
    system.elevators[0].step()

    assert system.request_elevator(12, Direction.UP).elevator_id == "E2"


def test_a_car_in_maintenance_is_never_scheduled():
    system = make_bank(5, 20)
    system.elevators[0].take_out_of_service()

    assert system.request_elevator(6, Direction.UP).elevator_id == "E2"


def test_a_call_nobody_can_take_is_queued_not_dropped():
    system = ElevatorSystem(1, 0, 10)
    system.elevators[0].take_out_of_service()

    assert system.request_elevator(5, Direction.UP) is None
    assert len(system.pending) == 1


def test_a_queued_call_is_served_once_a_car_frees_up():
    system = ElevatorSystem(1, 0, 10)
    system.elevators[0].take_out_of_service()
    system.request_elevator(5, Direction.UP)

    system.elevators[0].return_to_service()
    system.run_until_idle()

    assert system.elevators[0].stops_served == [5]
    assert system.pending == []


def test_an_unknown_strategy_lists_the_known_ones():
    with pytest.raises(ValueError, match="least-busy, nearest"):
        get_strategy("psychic")


# -- the system -----------------------------------------------------------


def test_a_hall_call_then_a_car_call_completes():
    system = ElevatorSystem(2, 0, 10)
    car = system.request_elevator(5, Direction.UP)
    system.select_floor(car.elevator_id, 8)

    system.run_until_idle()

    assert car.stops_served == [5, 8]


def test_a_floor_outside_the_building_is_rejected_at_the_system_level():
    with pytest.raises(ValueError, match="outside 0-10"):
        ElevatorSystem(2, 0, 10).request_elevator(50, Direction.UP)


def test_an_unknown_elevator_lists_the_real_ones():
    with pytest.raises(KeyError, match="E1, E2"):
        ElevatorSystem(2).get("E9")


def test_a_building_needs_at_least_one_elevator():
    with pytest.raises(ValueError, match="at least one elevator"):
        ElevatorSystem(0)


def test_observers_see_every_stop():
    system = ElevatorSystem(1, 0, 10)
    seen = []
    system.subscribe(lambda elevator, floor: seen.append((elevator.elevator_id, floor)))

    system.request_elevator(4, Direction.UP)
    system.run_until_idle()

    assert ("E1", 4) in seen


def test_a_busy_bank_always_reaches_idle():
    system = ElevatorSystem(3, 0, 15)
    for floor in (2, 14, 7, 11, 3):
        system.request_elevator(floor, Direction.UP)
    for floor in (9, 1, 12):
        system.request_elevator(floor, Direction.DOWN)

    system.run_until_idle()

    assert system.is_idle


def test_every_requested_floor_is_eventually_served():
    system = ElevatorSystem(2, 0, 15)
    wanted = {2, 14, 7, 11, 3}
    for floor in wanted:
        system.request_elevator(floor, Direction.UP)

    system.run_until_idle()

    served = {f for e in system.elevators for f in e.stops_served}
    assert wanted <= served
