"""Experimental C02 spatial model; NOT the registered benchmark implementation.

This candidate models pallet spacing and finite station buffers. Its point
representation of shifters does not yet enforce their complete zero-storage
footprints, especially at the two adjacent Sy/Sx pairs. Consequently its
deadlocks and throughput cannot certify C02. Keep it isolated until that
remaining geometric rule and the independent reference mismatch are resolved.

Finite-pallet transport uses event-driven, integer-coordinate motion.

Coordinates are pallet centres in centimetres. At the specified belt speed a
centimetre takes 1/30 s; all benchmark lengths and service durations lie on
this lattice. The engine jumps to the next interaction, not through time steps.
Shifts reserve their receiving position before starting. A processed pallet
retains the positioning unit until its rear has cleared that unit.
"""

from __future__ import annotations

import itertools
import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..models.c02_flexible_assembly import C02Constants, StationConfig, _station_configs

_MAIN = frozenset({"main", "shift_in"})
_PRE = frozenset({"pre", "shift_in"})
_UNIT = frozenset({"enter", "process", "processed", "leave"})
_POST = frozenset({"leave", "post", "shift_out"})


@dataclass
class _Pallet:
    identifier: int
    position: int
    gate: int
    phase: str = "main"
    station: int = -1
    loaded: bool = False
    operations: int = 0
    loaded_at: int | None = None
    deadline: int | None = None
    operation: str = ""


@dataclass
class _Station:
    config: StationConfig
    sx: int
    sy: int
    length: int
    buffer: int
    pre_capacity: int
    post_capacity: int


class C02SpatialCandidate:
    """C02 with FIFO spatial queues, finite storage and branch merge priority.

    Initial pallets are empty and equally spaced on B1 unless positions are
    supplied. The policy takes the first required operation with room in its
    input buffer. A2 is not interleaved with the A3/A4/A5 operation group.
    A6 performs all missing operations from that group in one 30 s service.
    """

    def __init__(
        self,
        num_pallets: int,
        *,
        constants: C02Constants | None = None,
        initial_positions_m: Sequence[float] | None = None,
        trace: bool = False,
    ) -> None:
        if (
            isinstance(num_pallets, bool)
            or not isinstance(num_pallets, int)
            or num_pallets <= 0
        ):
            raise ValueError("num_pallets must be a positive integer")
        self.constants = constants or C02Constants()
        c = self.constants
        if not math.isfinite(c.speed_m_s) or c.speed_m_s <= 0:
            raise ValueError("belt speed must be positive and finite")
        self.tick_seconds = 0.01 / c.speed_m_s
        self.pallet_length = self._cm(c.pallet_length)
        if self.pallet_length <= 0 or self.pallet_length % 2:
            raise ValueError(
                "pallet length must be a positive even number of centimetres"
            )
        self.half_pallet = self.pallet_length // 2
        self.shift_ticks = self._ticks(c.shift_time)
        self.unit_length = self._cm(c.positioning_unit_length)
        self.shifter_width = self._cm(c.shifter_width)
        if (
            self.unit_length < self.pallet_length
            or self.shifter_width < self.pallet_length
        ):
            raise ValueError("a pallet must fit on a shifter and positioning unit")
        self.end = self._ticks(c.end_minutes * 60)
        self.warmup = self._ticks(c.warmup_minutes * 60)
        if not 0 <= self.warmup < self.end or self.shift_ticks <= 0:
            raise ValueError("require 0 <= warm-up < end and positive shift duration")
        self.stations: list[_Station] = []
        self.gates: list[int] = []
        offset = 0
        for index, config in enumerate(_station_configs(c)):
            length, buffer = self._cm(config.length_b1), self._cm(config.length_buffer)
            post = length - buffer - self.unit_length
            if min(buffer, post) < self.pallet_length:
                raise ValueError("each buffer must accommodate a complete pallet")
            self.stations.append(
                _Station(
                    config,
                    offset,
                    offset + self.shifter_width + length,
                    length,
                    buffer,
                    buffer // self.pallet_length,
                    post // self.pallet_length,
                )
            )
            self.gates.extend(
                (offset, offset + self.shifter_width + length - self.pallet_length)
            )
            offset += length + 2 * self.shifter_width
            if index not in (3, 7):
                offset += self._cm(c.space_between_subsystems)
        self.circumference = offset
        if num_pallets * self.pallet_length > self.circumference:
            raise ValueError("initial pallets do not fit on the B1 circuit")
        positions = (
            [index * self.circumference // num_pallets for index in range(num_pallets)]
            if initial_positions_m is None
            else [self._cm(position) for position in initial_positions_m]
        )
        if len(positions) != num_pallets or any(
            not 0 <= position < offset for position in positions
        ):
            raise ValueError(
                "supply one initial B1 position per pallet within the circuit"
            )
        ordered = sorted(positions)
        gaps = [
            (ordered[(i + 1) % num_pallets] - position) % offset
            if num_pallets > 1
            else offset
            for i, position in enumerate(ordered)
        ]
        if min(gaps) < self.pallet_length:
            raise ValueError("initial pallets overlap")
        self.pallets = [
            _Pallet(
                index,
                position,
                min(range(16), key=lambda g, p=position: (self.gates[g] - p) % offset),
            )
            for index, position in enumerate(positions)
        ]
        self.now = 0
        self.throughput = 0
        self.total_transit_ticks = 0
        self.trace_enabled = trace
        self.trace: list[dict[str, object]] = []
        self.event_count = 0
        self.max_pre = [0] * 8
        self.max_post = [0] * 8
        self.minimum_main_gap = self.circumference
        self.minimum_branch_gap = self.circumference

    @staticmethod
    def _cm(value: float) -> int:
        if not math.isfinite(value) or not math.isclose(
            value * 100, round(value * 100), abs_tol=1e-8, rel_tol=0
        ):
            raise ValueError(
                "geometry and initial positions must lie on the centimetre lattice"
            )
        return round(value * 100)

    def _ticks(self, seconds: float) -> int:
        value = seconds / self.tick_seconds
        if not math.isfinite(value) or not math.isclose(
            value, round(value), abs_tol=1e-7, rel_tol=0
        ):
            raise ValueError("durations must lie on the conveyor time lattice")
        return round(value)

    def _record(self, kind: str, pallet: _Pallet) -> None:
        if self.trace_enabled:
            self.trace.append(
                {
                    "time": self.now * self.tick_seconds,
                    "event": kind,
                    "pallet": pallet.identifier,
                    "station": self.stations[pallet.station].config.name,
                    "operations": pallet.operations,
                }
            )

    @staticmethod
    def _needs(pallet: _Pallet, index: int) -> bool:
        if index == 0:
            return not pallet.loaded or pallet.operations == 15
        if not pallet.loaded:
            return False
        if index in (1, 2, 3):
            return not pallet.operations & 1 and pallet.operations & 14 in (0, 14)
        if index == 7:
            return pallet.operations & 14 != 14
        return not pallet.operations & (1 << (index - 3))

    def _branch(self, index: int) -> list[_Pallet]:
        return sorted(
            (p for p in self.pallets if p.station == index and p.phase not in _MAIN),
            key=lambda p: p.position,
        )

    def _complete(self, pallet: _Pallet) -> None:
        index = pallet.station
        station = self.stations[index]
        pallet.deadline = None
        if pallet.phase == "shift_in":
            pallet.phase, pallet.position = "pre", self.half_pallet
            self._record("shift_in_complete", pallet)
        elif pallet.phase == "shift_out":
            pallet.phase, pallet.position = "main", station.sy
            pallet.gate = (2 * index + 2) % 16
            self._record("shift_out_complete", pallet)
        elif pallet.operation == "unload":
            if self.now >= self.warmup:
                if pallet.loaded_at is None:
                    raise RuntimeError("completed part lacks a loading timestamp")
                self.throughput += 1
                self.total_transit_ticks += self.now - pallet.loaded_at
            self._record("unloaded", pallet)
            pallet.loaded = False
            pallet.operations = 0
            pallet.operation = "load"
            pallet.deadline = self.now + self._ticks(7.5)
        else:
            if pallet.operation == "load":
                pallet.loaded = True
                pallet.loaded_at = self.now
                self._record("loaded", pallet)
            elif index in (1, 2, 3):
                pallet.operations |= 1
            elif index == 7:
                pallet.operations |= 14
            else:
                pallet.operations |= 1 << (index - 3)
            pallet.phase = "processed"
            self._record("operation_complete", pallet)

    def _can_merge(self, position: int) -> bool:
        return all(
            min(
                (p.position - position) % self.circumference,
                (position - p.position) % self.circumference,
            )
            >= self.pallet_length
            for p in self.pallets
            if p.phase in _MAIN
        )

    def _settle(self) -> None:
        for pallet in self.pallets:
            if pallet.deadline == self.now:
                self._complete(pallet)
        changed = True
        while changed:
            changed = False
            # Branch completion and Sy reservations precede main-lane routing.
            for index, station in enumerate(self.stations):
                branch = self._branch(index)
                unit_busy = any(p.phase in _UNIT for p in branch)
                post_count = sum(p.phase in _POST for p in branch)
                for pallet in reversed(branch):
                    if (
                        pallet.phase == "post"
                        and pallet.position == station.length - self.half_pallet
                    ):
                        if self._can_merge(station.sy):
                            pallet.phase = "shift_out"
                            pallet.deadline = self.now + self.shift_ticks
                            self._record("shift_out_start", pallet)
                            changed = True
                    elif (
                        pallet.phase == "leave"
                        and pallet.position
                        == station.buffer + self.unit_length + self.half_pallet
                    ):
                        pallet.phase = "post"
                        unit_busy = False
                        changed = True
                    elif (
                        pallet.phase == "processed"
                        and post_count < station.post_capacity
                    ):
                        pallet.phase = "leave"
                        post_count += 1
                        changed = True
                    elif (
                        pallet.phase == "enter"
                        and pallet.position == station.buffer + self.unit_length // 2
                    ):
                        pallet.phase = "process"
                        pallet.operation = (
                            ("unload" if pallet.loaded else "load")
                            if index == 0
                            else "work"
                        )
                        duration = 7.5 if index == 0 else station.config.op_time
                        pallet.deadline = self.now + self._ticks(duration)
                        self._record("operation_start", pallet)
                        changed = True
                    elif (
                        pallet.phase == "pre"
                        and pallet.position == station.buffer - self.half_pallet
                        and not unit_busy
                    ):
                        pallet.phase = "enter"
                        unit_busy = True
                        changed = True
            for pallet in self.pallets:
                if pallet.phase != "main" or pallet.position != self.gates[pallet.gate]:
                    continue
                index, kind = divmod(pallet.gate, 2)
                station = self.stations[index]
                branch = self._branch(index)
                if kind == 1:
                    if any(
                        p.phase == "shift_out"
                        or (
                            p.phase == "post"
                            and p.position == station.length - self.half_pallet
                        )
                        for p in branch
                    ):
                        continue
                    pallet.gate = (pallet.gate + 1) % 16
                else:
                    reserved = [
                        p
                        for p in self.pallets
                        if p.station == index and p.phase in _PRE
                    ]
                    entry_free = (
                        not branch
                        or branch[0].position >= self.half_pallet + self.pallet_length
                    )
                    can_enter = (
                        len(reserved) < station.pre_capacity
                        and entry_free
                        and not any(p.phase == "shift_in" for p in reserved)
                    )
                    if self._needs(pallet, index) and can_enter:
                        pallet.station, pallet.phase = index, "shift_in"
                        pallet.deadline = self.now + self.shift_ticks
                        self._record("shift_in_start", pallet)
                    else:
                        pallet.gate = (pallet.gate + 1) % 16
                changed = True

    def _target(self, pallet: _Pallet) -> int | None:
        if pallet.phase == "main":
            return self.gates[pallet.gate]
        station = self.stations[pallet.station]
        return {
            "pre": station.buffer - self.half_pallet,
            "enter": station.buffer + self.unit_length // 2,
            "leave": station.buffer + self.unit_length + self.half_pallet,
            "post": station.length - self.half_pallet,
        }.get(pallet.phase)

    def _motion(self) -> tuple[dict[int, int], int | None]:
        velocity = {}
        distances = []
        for pallet in self.pallets:
            target = self._target(pallet)
            distance = 0 if target is None else target - pallet.position
            if pallet.phase == "main":
                distance %= self.circumference
            if distance < 0:
                raise RuntimeError("pallet has passed its next physical control point")
            velocity[pallet.identifier] = int(distance > 0)
            if distance:
                distances.append((pallet.identifier, distance))
        main = [(p.position, p.identifier) for p in self.pallets if p.phase in _MAIN]
        for pallet in self.pallets:
            if pallet.phase == "shift_out":
                ghost = -1 - pallet.station
                main.append((self.stations[pallet.station].sy, ghost))
                velocity[ghost] = 0
        main.sort()
        contacts = []
        if len(main) > 1:
            for i, (position, identifier) in enumerate(main):
                next_position, ahead = main[(i + 1) % len(main)]
                gap = (next_position - position) % self.circumference
                self.minimum_main_gap = min(self.minimum_main_gap, gap)
                contacts.append((identifier, ahead, gap))
        for index in range(8):
            branch = self._branch(index)
            for behind, ahead in itertools.pairwise(branch):
                gap = ahead.position - behind.position
                self.minimum_branch_gap = min(self.minimum_branch_gap, gap)
                contacts.append((behind.identifier, ahead.identifier, gap))
        if any(gap < self.pallet_length for _, _, gap in contacts):
            raise RuntimeError("physical pallet overlap")
        for _ in range(len(velocity)):
            stopped = False
            for behind, ahead, gap in contacts:
                if (
                    gap == self.pallet_length
                    and velocity[behind]
                    and not velocity[ahead]
                ):
                    velocity[behind] = 0
                    stopped = True
            if not stopped:
                break
        candidates = [
            distance for identifier, distance in distances if velocity[identifier]
        ]
        candidates.extend(
            gap - self.pallet_length
            for behind, ahead, gap in contacts
            if velocity[behind] and not velocity[ahead] and gap > self.pallet_length
        )
        # A merge becomes available as soon as an interfering pallet clears it,
        # even when that pallet's next routing point is much farther away.
        for index, station in enumerate(self.stations):
            if not any(
                p.phase == "post" and p.position == station.length - self.half_pallet
                for p in self._branch(index)
            ):
                continue
            for position, identifier in main:
                relative = (position - station.sy) % self.circumference
                if velocity[identifier] and (
                    relative < self.pallet_length
                    or relative > self.circumference - self.pallet_length
                ):
                    candidates.append(
                        (station.sy + self.pallet_length - position)
                        % self.circumference
                    )
        return velocity, min(candidates) if candidates else None

    def _check_storage(self) -> None:
        for index, station in enumerate(self.stations):
            local = [
                p for p in self.pallets if p.station == index and p.phase != "main"
            ]
            pre = sum(p.phase in _PRE for p in local)
            post = sum(p.phase in _POST for p in local)
            self.max_pre[index] = max(self.max_pre[index], pre)
            self.max_post[index] = max(self.max_post[index], post)
            if pre > station.pre_capacity or post > station.post_capacity:
                raise RuntimeError("finite C02 buffer capacity exceeded")
            if sum(p.phase in _UNIT for p in local) > 1:
                raise RuntimeError("two pallets occupy one positioning unit")
            for phase in ("shift_in", "shift_out"):
                if sum(p.phase == phase for p in local) > 1:
                    raise RuntimeError("two pallets occupy one shifter")

    def run(self, *, max_events: int = 2_000_000) -> dict[str, object]:
        deadlocked = False
        while self.now < self.end:
            self._settle()
            self._check_storage()
            velocity, motion_delay = self._motion()
            delays = [
                p.deadline - self.now for p in self.pallets if p.deadline is not None
            ]
            if motion_delay is not None:
                delays.append(motion_delay)
            if not delays:
                deadlocked = True
                break
            delta = min(min(delays), self.end - self.now)
            if delta <= 0:
                raise RuntimeError("C02 failed to advance event time")
            for pallet in self.pallets:
                pallet.position += velocity[pallet.identifier] * delta
                if pallet.phase in _MAIN:
                    pallet.position %= self.circumference
            self.now += delta
            self.event_count += 1
            if self.event_count > max_events:
                raise RuntimeError("C02 event limit exceeded")
        if not deadlocked:
            self._settle()
            self._check_storage()
            self._motion()
        return {
            "scope": "experimental; shifter zero-storage geometry incomplete",
            "throughput": float(self.throughput),
            "average_throughput_time": self.total_transit_ticks
            * self.tick_seconds
            / self.throughput
            if self.throughput
            else 0.0,
            "deadlock": deadlocked,
            "stopped_at_seconds": self.now * self.tick_seconds,
            "pallets": len(self.pallets),
            "events": self.event_count,
            "maximum_input_buffer_occupancy": tuple(self.max_pre),
            "maximum_output_buffer_occupancy": tuple(self.max_post),
            "minimum_main_spacing_m": self.minimum_main_gap / 100,
            "minimum_branch_spacing_m": self.minimum_branch_gap / 100,
        }
