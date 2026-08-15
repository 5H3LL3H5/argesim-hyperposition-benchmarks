"""ARGESIM Benchmark C08: Canal-and-Lock System."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
import random
import statistics
from typing import Callable
from nsa_devs.hypertime import HyperTime
from nsa_devs.scheduler import DesScheduler


class Direction(Enum):
    EASTBOUND = "eastbound"
    WESTBOUND = "westbound"


class LockState(Enum):
    HIGH = "high"
    LOW = "low"
    MOVING_TO_HIGH = "moving_to_high"
    MOVING_TO_LOW = "moving_to_low"


@dataclass(frozen=True)
class Barge:
    id: int
    direction: Direction
    arrival_time: HyperTime


class CanalAndLock:
    def __init__(self, eastmax: int, westmax: int):
        for name, value in (("eastmax", eastmax), ("westmax", westmax)):
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        self.eastmax = eastmax
        self.westmax = westmax

        self.scheduler = DesScheduler()

        self.queues: dict[Direction, list[Barge]] = {
            Direction.EASTBOUND: [],
            Direction.WESTBOUND: [],
        }

        self.completed_barges: list[tuple[Barge, float]] = []

        self.lock_state = LockState.HIGH
        self.lock_occupied = False
        self.lock_queue: list[Barge] = []

        self.active_cycle_direction: Direction | None = None
        self.active_cycle_barges: set[Barge] = set()
        self.pre_lock_barges: set[Barge] = set()
        self.last_cycle_direction: Direction | None = None

        # System parameters (in minutes) as specified in ARGESIM C08 definition:
        self.west_canal_time = 14.0
        self.east_canal_time = 18.0
        self.lock_change_time = 12.0
        self.lock_in_time = 5.0
        self.lock_out_time = 5.0

        self.queue_trajectory: list[tuple[float, int, int]] = []

    @property
    def time(self) -> HyperTime:
        return self.scheduler.time

    def schedule(self, delay: float, name: str, handler: Callable, *args) -> None:
        self.scheduler.schedule(delay, name, handler, *args)

    def run(self, until: float) -> None:
        self.scheduler.run(until)

    def _record_queues(self) -> None:
        self.queue_trajectory.append((
            float(self.time.standard_part()),
            len(self.queues[Direction.EASTBOUND]),
            len(self.queues[Direction.WESTBOUND])
        ))

    def schedule_arrival(self, barge: Barge) -> None:
        if barge.arrival_time < self.time:
            raise ValueError("Cannot schedule arrival in the past")
        delay = float(barge.arrival_time.standard_part() - self.time.standard_part())
        self.schedule(delay, f"arrive {barge.id}", self.arrive, barge)

    def arrive(self, barge: Barge) -> None:
        self.queues[barge.direction].append(barge)
        self._record_queues()
        if self.active_cycle_direction == barge.direction:
            max_allowed = (
                self.eastmax if barge.direction == Direction.EASTBOUND else self.westmax
            )
            if len(self.active_cycle_barges) < max_allowed:
                self.queues[barge.direction].remove(barge)
                self._record_queues()
                self.active_cycle_barges.add(barge)
                self.pre_lock_barges.add(barge)
                canal_time = (
                    self.west_canal_time
                    if barge.direction == Direction.EASTBOUND
                    else self.east_canal_time
                )
                self.schedule(canal_time, f"arrive_at_lock {barge.id}", self.arrive_at_lock, barge)
                return

        self.try_start_cycle()

    def try_start_cycle(self) -> None:
        if self.active_cycle_direction is not None:
            return

        has_east = len(self.queues[Direction.EASTBOUND]) > 0
        has_west = len(self.queues[Direction.WESTBOUND]) > 0

        if not has_east and not has_west:
            return

        next_dir = None
        if self.last_cycle_direction is not None:
            opp_dir = (
                Direction.WESTBOUND
                if self.last_cycle_direction == Direction.EASTBOUND
                else Direction.EASTBOUND
            )
            if self.queues[opp_dir]:
                next_dir = opp_dir
            elif self.queues[self.last_cycle_direction]:
                next_dir = self.last_cycle_direction
        else:
            if has_east and has_west:
                # Per the ARGESIM C08 specification tie-breaking logic (e.g., initial state in Dataset 1),
                # Eastbound barges are given precedence when starting from an empty system.
                next_dir = Direction.EASTBOUND
            elif has_east:
                next_dir = Direction.EASTBOUND
            else:
                next_dir = Direction.WESTBOUND

        if next_dir is not None:
            self.active_cycle_direction = next_dir
            max_allowed = (
                self.eastmax if next_dir == Direction.EASTBOUND else self.westmax
            )
            admitted = self.queues[next_dir][:max_allowed]
            self.queues[next_dir] = self.queues[next_dir][max_allowed:]
            self._record_queues()

            for b in admitted:
                self.active_cycle_barges.add(b)
                self.pre_lock_barges.add(b)
                canal_time = (
                    self.west_canal_time
                    if b.direction == Direction.EASTBOUND
                    else self.east_canal_time
                )
                self.schedule(canal_time, f"arrive_at_lock {b.id}", self.arrive_at_lock, b)

            self.update_lock()

    def arrive_at_lock(self, barge: Barge) -> None:
        self.lock_queue.append(barge)
        self.update_lock()

    def update_lock(self) -> None:
        if self.lock_state in (LockState.MOVING_TO_HIGH, LockState.MOVING_TO_LOW):
            return
        if self.lock_occupied:
            return

        if self.lock_queue:
            barge = self.lock_queue[0]
            expected_level = (
                LockState.HIGH if barge.direction == Direction.EASTBOUND else LockState.LOW
            )

            if self.lock_state == expected_level:
                self.lock_queue.pop(0)
                self.pre_lock_barges.remove(barge)
                self.lock_occupied = True

                total_lock_time = self.lock_in_time + self.lock_change_time + self.lock_out_time
                self.schedule(total_lock_time, f"leave_lock {barge.id}", self.leave_lock, barge)
            else:
                target_state = (
                    LockState.MOVING_TO_HIGH
                    if expected_level == LockState.HIGH
                    else LockState.MOVING_TO_LOW
                )
                self.lock_state = target_state
                self.schedule(self.lock_change_time, f"lock_ready {expected_level.name}", self.lock_ready, expected_level)
        else:
            if self.pre_lock_barges:
                expected_level = (
                    LockState.HIGH if self.active_cycle_direction == Direction.EASTBOUND else LockState.LOW
                )
                if self.lock_state != expected_level:
                    target_state = (
                        LockState.MOVING_TO_HIGH
                        if expected_level == LockState.HIGH
                        else LockState.MOVING_TO_LOW
                    )
                    self.lock_state = target_state
                    self.schedule(self.lock_change_time, f"lock_ready {expected_level.name}", self.lock_ready, expected_level)

    def lock_ready(self, expected_level: LockState) -> None:
        self.lock_state = expected_level
        self.update_lock()

    def leave_lock(self, barge: Barge) -> None:
        self.lock_occupied = False
        self.lock_state = LockState.LOW if barge.direction == Direction.EASTBOUND else LockState.HIGH

        second_canal_time = (
            self.east_canal_time if barge.direction == Direction.EASTBOUND else self.west_canal_time
        )
        self.schedule(second_canal_time, f"leave_system {barge.id}", self.leave_system, barge)
        self.update_lock()

    def leave_system(self, barge: Barge) -> None:
        self.active_cycle_barges.remove(barge)
        transit_time = float(self.time.standard_part() - barge.arrival_time.standard_part())
        self.completed_barges.append((barge, transit_time))

        if not self.active_cycle_barges:
            self.last_cycle_direction = self.active_cycle_direction
            self.active_cycle_direction = None
            self.try_start_cycle()

    def average_transit_times(self) -> dict[str, float]:
        """Return eastbound, westbound, and pooled completed-barge means."""

        east = [
            transit
            for barge, transit in self.completed_barges
            if barge.direction == Direction.EASTBOUND
        ]
        west = [
            transit
            for barge, transit in self.completed_barges
            if barge.direction == Direction.WESTBOUND
        ]
        pooled = east + west

        def mean(values: list[float]) -> float:
            return sum(values) / len(values) if values else 0.0

        return {
            "eastbound": mean(east),
            "westbound": mean(west),
            "pooled": mean(pooled),
        }


def _inverse_exponential(unit_value: float, mean: float = 75.0) -> float:
    unit_value = min(max(unit_value, 1.0e-15), 1.0 - 1.0e-15)
    return -mean * math.log1p(-unit_value)


def _stochastic_arrivals(
    *,
    seed: int,
    duration: float,
    antithetic: bool = False,
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Generate the official stochastic arrival streams by inverse transform."""

    rng = random.Random(seed)

    def unit() -> float:
        value = rng.random()
        return 1.0 - value if antithetic else value

    def stream(first_scale: float) -> tuple[float, ...]:
        arrival = first_scale * unit()
        values = []
        while arrival <= duration:
            values.append(arrival)
            arrival += _inverse_exponential(unit())
        return tuple(values)

    return stream(30.0), stream(20.0)


def run_c08_replication(
    eastmax: int,
    westmax: int,
    *,
    duration: float = 14400.0,
    seed: int = 42,
    antithetic: bool = False,
) -> float:
    """Run one probabilistic Task-C replication and return the pooled mean."""

    if duration <= 0.0 or not math.isfinite(duration):
        raise ValueError("duration must be positive and finite")
    east_arrivals, west_arrivals = _stochastic_arrivals(
        seed=seed,
        duration=duration,
        antithetic=antithetic,
    )
    model = CanalAndLock(eastmax, westmax)
    barge_id = 0
    for arrival in east_arrivals:
        model.schedule_arrival(
            Barge(barge_id, Direction.EASTBOUND, HyperTime.at(arrival))
        )
        barge_id += 1
    for arrival in west_arrivals:
        model.schedule_arrival(
            Barge(barge_id, Direction.WESTBOUND, HyperTime.at(arrival))
        )
        barge_id += 1
    model.run(duration)
    if not model.completed_barges:
        raise RuntimeError("replication completed no barges")
    return model.average_transit_times()["pooled"]


def _student_t_90(df: int) -> float:
    """Accurate asymptotic t critical value for a two-sided 90% interval."""

    if df <= 0:
        raise ValueError("degrees of freedom must be positive")
    z = 1.6448536269514722
    return (
        z
        + (z**3 + z) / (4.0 * df)
        + (5.0 * z**5 + 16.0 * z**3 + 3.0 * z) / (96.0 * df**2)
        + (3.0 * z**7 + 19.0 * z**5 + 17.0 * z**3 - 15.0 * z)
        / (384.0 * df**3)
    )


def _confidence_interval_90(values: list[float]) -> dict[str, float | int]:
    if len(values) < 2:
        raise ValueError("confidence interval requires at least two observations")
    mean = statistics.mean(values)
    deviation = statistics.stdev(values)
    half_width = _student_t_90(len(values) - 1) * deviation / math.sqrt(len(values))
    return {
        "observations": len(values),
        "mean": mean,
        "standard_deviation": deviation,
        "lower": mean - half_width,
        "upper": mean + half_width,
        "half_width": half_width,
    }


def c08_task_c(
    *,
    duration: float = 14400.0,
    independent_replications: int = 100,
    paired_replications: int = 50,
    starting_seeds: tuple[int, ...] = (42, 314159, 271828),
) -> dict[str, object]:
    """Execute all six variance-reduction activities from the definition."""

    if duration <= 0.0 or not math.isfinite(duration):
        raise ValueError("duration must be positive and finite")
    for name, value in (
        ("independent_replications", independent_replications),
        ("paired_replications", paired_replications),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 2:
            raise ValueError(f"{name} must be an integer of at least two")
    if not starting_seeds:
        raise ValueError("at least one random-number starting seed is required")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in starting_seeds):
        raise ValueError("starting seeds must be integers")

    experiments: list[dict[str, object]] = []
    for starting_seed in starting_seeds:
        seed_rng = random.Random(starting_seed)
        independent_seeds = [
            seed_rng.randrange(0, 2**63) for _ in range(independent_replications)
        ]
        pair_seeds = [
            seed_rng.randrange(0, 2**63) for _ in range(paired_replications)
        ]
        independent_policy_seeds = [
            seed_rng.randrange(0, 2**63) for _ in range(2 * paired_replications)
        ]

        ordinary_values = [
            run_c08_replication(5, 5, duration=duration, seed=seed)
            for seed in independent_seeds
        ]
        ordinary = _confidence_interval_90(ordinary_values)

        antithetic_pair_means = [
            0.5
            * (
                run_c08_replication(5, 5, duration=duration, seed=seed)
                + run_c08_replication(
                    5, 5, duration=duration, seed=seed, antithetic=True
                )
            )
            for seed in pair_seeds
        ]
        antithetic = _confidence_interval_90(antithetic_pair_means)

        independent_differences = [
            run_c08_replication(
                5,
                5,
                duration=duration,
                seed=independent_policy_seeds[2 * index],
            )
            - run_c08_replication(
                6,
                6,
                duration=duration,
                seed=independent_policy_seeds[2 * index + 1],
            )
            for index in range(paired_replications)
        ]
        independent_policy = _confidence_interval_90(independent_differences)

        crn_differences = [
            run_c08_replication(5, 5, duration=duration, seed=seed)
            - run_c08_replication(6, 6, duration=duration, seed=seed)
            for seed in pair_seeds
        ]
        common_random_numbers = _confidence_interval_90(crn_differences)

        ordinary_width = float(ordinary["half_width"])
        independent_width = float(independent_policy["half_width"])
        experiments.append(
            {
                "starting_seed": starting_seed,
                "ordinary_5_5": ordinary,
                "antithetic_5_5": antithetic,
                "antithetic_width_reduction": (
                    1.0 - float(antithetic["half_width"]) / ordinary_width
                    if ordinary_width
                    else 0.0
                ),
                "independent_difference_5_minus_6": {
                    **independent_policy,
                    "reject_null_mean_difference_le_zero": float(independent_policy["lower"]) > 0.0,
                },
                "crn_difference_5_minus_6": {
                    **common_random_numbers,
                    "reject_null_mean_difference_le_zero": float(common_random_numbers["lower"]) > 0.0,
                },
                "crn_width_reduction": (
                    1.0
                    - float(common_random_numbers["half_width"]) / independent_width
                    if independent_width
                    else 0.0
                ),
            }
        )

    return {
        "confidence_probability": 0.90,
        "duration_minutes": duration,
        "independent_replications": independent_replications,
        "paired_replications": paired_replications,
        "experiments": tuple(experiments),
    }
