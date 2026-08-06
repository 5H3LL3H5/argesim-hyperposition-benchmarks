"""ARGESIM Benchmark C08: Canal-and-Lock System."""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable
from nsa_devs.hypertime import HyperTime


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


@dataclass(order=True)
class Event:
    time: HyperTime
    sequence: int
    name: str = field(compare=False)
    handler: Callable[[], None] = field(compare=False)


class CanalAndLock:
    def __init__(self, eastmax: int, westmax: int):
        self.eastmax = eastmax
        self.westmax = westmax

        self.time = HyperTime.at(0)
        self.events: list[Event] = []
        self.event_sequence = 0

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

        self.west_canal_time = 14.0
        self.east_canal_time = 18.0
        self.lock_change_time = 12.0
        self.lock_in_time = 5.0
        self.lock_out_time = 5.0

        self.queue_trajectory: list[tuple[float, int, int]] = []

    def schedule(self, delay: float, name: str, handler: Callable[[], None]) -> None:
        if delay == 0.0:
            target_time = self.time.after_epsilon(1)
        else:
            target_time = self.time.after_finite(delay)
        heapq.heappush(
            self.events,
            Event(target_time, self.event_sequence, name, handler),
        )
        self.event_sequence += 1

    def run(self, until: float) -> None:
        until_time = HyperTime.at(until)
        while self.events and self.events[0].time <= until_time:
            event = heapq.heappop(self.events)
            self.time = event.time
            event.handler()
        self.time = until_time

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
        self.schedule(delay, f"arrive {barge.id}", lambda b=barge: self.arrive(b))

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
                self.schedule(canal_time, f"arrive_at_lock {barge.id}", lambda b=barge: self.arrive_at_lock(b))
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
                self.schedule(canal_time, f"arrive_at_lock {b.id}", lambda b=b: self.arrive_at_lock(b))

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
                self.schedule(total_lock_time, f"leave_lock {barge.id}", lambda b=barge: self.leave_lock(b))
            else:
                target_state = (
                    LockState.MOVING_TO_HIGH
                    if expected_level == LockState.HIGH
                    else LockState.MOVING_TO_LOW
                )
                self.lock_state = target_state
                self.schedule(self.lock_change_time, f"lock_ready {expected_level.name}", lambda e=expected_level: self.lock_ready(e))
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
                    self.schedule(self.lock_change_time, f"lock_ready {expected_level.name}", lambda e=expected_level: self.lock_ready(e))

    def lock_ready(self, expected_level: LockState) -> None:
        self.lock_state = expected_level
        self.update_lock()

    def leave_lock(self, barge: Barge) -> None:
        self.lock_occupied = False
        self.lock_state = LockState.LOW if barge.direction == Direction.EASTBOUND else LockState.HIGH

        second_canal_time = (
            self.east_canal_time if barge.direction == Direction.EASTBOUND else self.west_canal_time
        )
        self.schedule(second_canal_time, f"leave_system {barge.id}", lambda b=barge: self.leave_system(b))
        self.update_lock()

    def leave_system(self, barge: Barge) -> None:
        self.active_cycle_barges.remove(barge)
        transit_time = float(self.time.standard_part() - barge.arrival_time.standard_part())
        self.completed_barges.append((barge, transit_time))

        if not self.active_cycle_barges:
            self.last_cycle_direction = self.active_cycle_direction
            self.active_cycle_direction = None
            self.try_start_cycle()
