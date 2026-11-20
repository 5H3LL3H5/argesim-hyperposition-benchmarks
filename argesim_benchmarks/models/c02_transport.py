"""Event-driven C02 plant with finite conveyors and shifters without storage.

All distances are in cm internally. One tick moves a pallet one cm at belt
speed. Time advances only to a transport, clearance or service event.
"""

from __future__ import annotations

import math
import random
from collections import deque
from dataclasses import dataclass, field

from .c02_flexible_assembly import C02Constants, _station_configs


@dataclass(slots=True)
class _Pallet:
    identifier: int
    loaded_at: int | None = None
    operations: int = 0  # low to high bits: A2, A3, A4, A5
    load_started: int = 0


@dataclass(slots=True)
class _Belt:
    name: str
    capacity: int
    transit: int
    pitch: int
    # FIFO ownership includes incoming transfers with a guaranteed exit from
    # their shifter. ready_at is the earliest free-flow arrival at the outlet.
    queue: deque[tuple[_Pallet, int]] = field(default_factory=deque)
    next_entry: int = 0
    next_exit: int = 0

    @property
    def full(self) -> bool:
        return len(self.queue) == self.capacity

    def reserve(self, pallet: _Pallet, arrival: int) -> None:
        if len(self.queue) >= self.capacity or arrival < self.next_entry:
            raise RuntimeError(f"overlapping C02 admission at {self.name}")
        self.queue.append((pallet, arrival + self.transit))
        self.next_entry = arrival + self.pitch

    def release(self, now: int) -> _Pallet:
        pallet, ready_at = self.queue[0]
        if now < max(ready_at, self.next_exit):
            raise RuntimeError(f"premature departure from {self.name}")
        self.queue.popleft()
        self.next_exit = now + self.pitch
        return pallet


@dataclass(slots=True)
class _Station:
    name: str
    bypass: _Belt
    before: _Belt
    after: _Belt
    connector: _Belt | None
    service: int
    sx_free: int = 0
    sy_free: int = 0
    pallet: _Pallet | None = None
    phase: str = "idle"
    due: int = 0
    unload_started: int = 0

    def unit_busy(self, now: int) -> bool:
        return self.pallet is not None or self.due > now


def _positive_count(count: int) -> None:
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("number of pallets must be a positive integer")


class C02Plant:
    """Eight stations with finite B1/B2 queues, exclusive units and B2 priority."""

    def __init__(
        self,
        num_pallets: int,
        *,
        controller: str = "first-eligible",
        unit_timing: str = "exclusive",
        initial_seed: int | None = None,
        constants: C02Constants | None = None,
        trace: bool = False,
    ) -> None:
        _positive_count(num_pallets)
        if controller not in ("first-eligible", "cyclic-a2"):
            raise ValueError("controller must be 'first-eligible' or 'cyclic-a2'")
        if unit_timing not in ("exclusive", "service-only"):
            raise ValueError("unit_timing must be 'exclusive' or 'service-only'")
        if initial_seed is not None and type(initial_seed) is not int:
            raise ValueError("initial_seed must be an integer or None")
        self.initial_seed = initial_seed
        self.controller = controller
        self.unit_timing = unit_timing
        self.a2_passages = [0, 0]
        c = constants or C02Constants()
        if not math.isfinite(c.speed_m_s) or c.speed_m_s <= 0:
            raise ValueError("belt speed must be positive and finite")
        self.tick_seconds = 0.01 / c.speed_m_s
        self.warmup = self._ticks(c.warmup_minutes * 60)
        self.end = self._ticks(c.end_minutes * 60)
        if not 0 <= self.warmup < self.end:
            raise ValueError("require 0 <= warm-up < end")
        shift = self._ticks(c.shift_time)
        self.straight = self._ticks(c.shifter_width / c.speed_m_s)
        self.lateral_crossing = self.straight + shift
        pitch = self._ticks(c.pallet_length / c.speed_m_s)
        unit = self._ticks(c.positioning_unit_length / c.speed_m_s)
        gap = self._ticks(c.space_between_subsystems / c.speed_m_s)
        if min(shift, pitch) <= 0 or min(unit, self.straight, gap) < pitch:
            raise ValueError("a pallet must fit on a shifter, unit and connector")
        if unit % 2 or pitch % 2:
            raise ValueError("unit and pallet centres must lie on the cm lattice")
        # The reference sensitivity assigns approach and clearance to the
        # adjoining transports. Physical distances and slot counts are fixed.
        self.exclusive_half_travel = unit // 2 if unit_timing == "exclusive" else 0
        belt_half_travel = unit // 2 - self.exclusive_half_travel
        self.stations: list[_Station] = []

        def belt(name: str, length: int, extra_travel: int = 0) -> _Belt:
            return _Belt(name, length // pitch, length + extra_travel, pitch)

        for i, config in enumerate(_station_configs(c)):
            length = self._ticks(config.length_b1 / c.speed_m_s)
            pre = self._ticks(config.length_buffer / c.speed_m_s)
            post = length - pre - unit
            if min(pre, post) < pitch:
                raise ValueError("a pallet must fit in both station buffers")

            self.stations.append(
                _Station(
                    config.name,
                    belt(f"{config.name}.B1", length),
                    belt(f"{config.name}.pre", pre, belt_half_travel),
                    belt(f"{config.name}.post", post, belt_half_travel),
                    None if i in (3, 7) else belt(f"{config.name}.gap", gap),
                    self._ticks(config.op_time),
                )
            )
        self.half_a1 = self._ticks(7.5)
        self.num_pallets = num_pallets
        self.feed = _Belt("initial B1 feed", num_pallets, 0, pitch)
        self.initial_on_b1 = self._place_empty_pallets(num_pallets)
        self.filled_at: int | None = None if self.feed.queue else 0
        self.now = 0
        self.next_time: int | None = None
        self.throughput = 0
        self.part_ticks = self.with_unload_ticks = self.with_handling_ticks = 0
        self.trace: list[dict] | None = [] if trace else None

    def _ticks(self, seconds: float) -> int:
        value = seconds / self.tick_seconds
        if not math.isfinite(value) or not math.isclose(
            value, round(value), abs_tol=1e-7, rel_tol=0
        ):
            raise ValueError("duration is not on the C02 transport time lattice")
        return round(value)

    def _place_empty_pallets(self, count: int) -> int:
        # Empty B1 belts and connectors have 40 resting places. Additional
        # empty pallets join at A1's B1 entrance as space becomes available.
        slots = []
        for station in self.stations:
            for belt in (station.bypass, station.connector):
                if belt is not None:
                    for j in range(belt.capacity):
                        centre = belt.pitch // 2 + j * belt.pitch
                        slots.append((belt, centre))
        placed = min(count, len(slots))
        if self.initial_seed is None:
            selected = [i * len(slots) // placed for i in range(placed)]
        else:
            # Sample legal B1 centres without replacement. Ordering is needed
            # for FIFO insertion, including when all 40 slots are occupied.
            rng = random.Random(self.initial_seed)
            selected = sorted(rng.sample(range(len(slots)), placed))
        for i, slot in enumerate(selected):
            belt, centre = slots[slot]
            belt.queue.appendleft((_Pallet(i), belt.transit - centre))
            belt.next_entry = max(belt.next_entry, belt.pitch - centre)
        self.feed.queue.extend((_Pallet(i), 0) for i in range(placed, count))
        return placed

    def _ready(self, tick: int) -> bool:
        if tick <= self.now:
            return True
        if self.next_time is None or tick < self.next_time:
            self.next_time = tick
        return False

    def _front(self, belt: _Belt) -> _Pallet | None:
        if belt.queue and self._ready(max(belt.queue[0][1], belt.next_exit)):
            return belt.queue[0][0]
        return None

    def _record(self, event: str, pallet: _Pallet, **fields) -> None:
        if self.trace is not None:
            self.trace.append(
                dict(tick=self.now, event=event, pallet=pallet.identifier, **fields)
            )

    def _takes_branch(self, part: _Pallet, index: int) -> bool:
        if index == 0:
            return part.loaded_at is None or part.operations == 15
        if part.loaded_at is None:
            return False
        group = part.operations & 14
        if index <= 3:
            if part.operations & 1 or group not in (0, 14):
                return False
            if self.controller == "first-eligible" or index == 3:
                return True
            # For the cyclic policy, count a passage only once the transfer
            # commits. Testing an outlet or retrying a blocked head is read-only.
            period = 3 if index == 1 else 2
            return (self.a2_passages[index - 1] + 1) % period == 0
        if index == 7:
            return group != 14
        if index == 4:
            # Herzog's executable C02 controller observes A6's input belt
            # and positioning/processing unit, excluding shifters and output.
            a6 = self.stations[7]
            on_input = sum(
                ready - a6.before.transit <= self.now for _, ready in a6.before.queue
            )
            return not group & 2 and on_input + a6.unit_busy(self.now) >= 2
        if index == 5:
            return group & 6 == 2
        return group == 6

    def _advance_unit(self, index: int, station: _Station) -> bool:
        part = station.pallet
        if part is None:
            part = self._front(station.before)
            if part is None or not self._ready(station.due):
                return False
            station.pallet = station.before.release(self.now)
            station.phase, station.due = (
                "position",
                self.now + self.exclusive_half_travel,
            )
            self._record("unit_enter", part, station=station.name)
            return True
        if not self._ready(station.due):
            return False
        if station.phase == "position":
            if index == 0:
                if part.loaded_at is None:
                    part.load_started = self.now
                    station.phase = "load"
                else:
                    station.unload_started = self.now
                    station.phase = "unload"
                duration = self.half_a1
            else:
                station.phase, duration = "work", station.service
            station.due = self.now + duration
            self._record(station.phase, part, station=station.name)
            return True
        if station.phase == "unload":
            if part.loaded_at is None or part.operations != 15:
                raise RuntimeError("C02 attempted to unload an unfinished part")
            if self.now >= self.warmup:
                self.throughput += 1
                self.part_ticks += station.unload_started - part.loaded_at
                self.with_unload_ticks += self.now - part.loaded_at
                self.with_handling_ticks += self.now - part.load_started
            self._record("unloaded", part, station=station.name)
            part.operations, part.loaded_at, part.load_started = 0, None, self.now
            station.phase, station.due = "load", self.now + self.half_a1
            self._record("load", part, station=station.name)
            return True
        if station.phase == "load":
            part.loaded_at = self.now
            self._record("loaded", part, station=station.name)
        elif station.phase == "work":
            if index <= 3:
                part.operations |= 1
            elif index == 7:
                part.operations |= 14
            else:
                part.operations |= 1 << (index - 3)
            self._record(
                "assembled", part, station=station.name, operations=part.operations
            )
        station.phase = "done"
        if station.after.full or not self._ready(
            station.after.next_entry - self.exclusive_half_travel
        ):
            return False  # the finished pallet still owns the positioning unit
        station.due = self.now + self.exclusive_half_travel
        station.after.reserve(part, station.due)
        station.pallet, station.phase = None, "idle"
        self._record("unit_exit", part, station=station.name, clear=station.due)
        return True

    def _transfer(
        self,
        source: _Belt,
        next_index: int,
        *,
        sy: _Station | None = None,
        sx: _Station | None = None,
    ) -> bool:
        part = self._front(source)
        if part is None:
            return False
        sy_duration = 0
        if sy is not None:
            if not self._ready(sy.sy_free):
                return False
            sy_duration = self.lateral_crossing if source is sy.after else self.straight
        sx_start = self.now + sy_duration
        if sx is None:
            assert sy is not None and sy.connector is not None
            dest, arrival = sy.connector, sx_start
        else:
            # For adjacent Sy/Sx reserve both crossing intervals and the final
            # destination before release. Neither shifter can become a queue.
            if not self._ready(sx.sx_free - sy_duration):
                return False
            dest, arrival = sx.bypass, sx_start + self.straight
            if (
                self._takes_branch(part, next_index)
                and not sx.before.full
                and self._ready(
                    sx.before.next_entry - sy_duration - self.lateral_crossing
                )
            ):
                dest, arrival = sx.before, sx_start + self.lateral_crossing
        if dest.full or not self._ready(dest.next_entry - (arrival - self.now)):
            return False
        source.release(self.now)
        dest.reserve(part, arrival)
        if sy is not None:
            sy.sy_free = sx_start
        if sx is not None:
            sx.sx_free = arrival
            if self.controller == "cyclic-a2" and next_index in (1, 2):
                self.a2_passages[next_index - 1] += 1
        if source is self.feed and not source.queue:
            self.filled_at = self.now
        if self.trace is not None:
            self._record(
                "transfer",
                part,
                source=source.name,
                destination=dest.name,
                sy=sy.name if sy else None,
                sx=sx.name if sx else None,
                sx_start=sx_start,
                arrival=arrival,
            )
        return True

    def _settle(self) -> None:
        changed = True
        while changed:
            changed = False
            for i, station in enumerate(self.stations):
                if self._advance_unit(i, station):
                    changed = True
            for i, station in enumerate(self.stations):
                nxt = (i + 1) % len(self.stations)
                sx = self.stations[nxt]
                if station.connector is not None:
                    if self._transfer(station.connector, nxt, sx=sx):
                        changed = True
                    sx = None
                # If both routes are admissible at this instant, B2 wins.
                if self._transfer(
                    station.after, nxt, sy=station, sx=sx
                ) or self._transfer(station.bypass, nxt, sy=station, sx=sx):
                    changed = True
            if self._transfer(self.feed, 0, sx=self.stations[0]):
                changed = True

    def _inventory(self) -> tuple[dict[str, tuple[int, int]], list[int]]:
        counts = {self.feed.name: (len(self.feed.queue), self.feed.capacity)}
        parts = [p.identifier for p, _ in self.feed.queue]
        for station in self.stations:
            for belt in (
                station.before,
                station.after,
                station.bypass,
                station.connector,
            ):
                if belt is not None:
                    counts[belt.name] = (len(belt.queue), belt.capacity)
                    parts.extend(p.identifier for p, _ in belt.queue)
            counts[station.name] = (int(station.pallet is not None), 1)
            if station.pallet is not None:
                parts.append(station.pallet.identifier)
        return counts, parts

    def _deadlock_witness(self, inventory: dict[str, tuple[int, int]]) -> dict:
        waits: dict[str, list[str]] = {}

        def targets(part: _Pallet, index: int) -> list[str]:
            station = self.stations[index]
            names = [station.bypass.name]
            if self._takes_branch(part, index):
                names.append(station.before.name)
            return names

        for i, station in enumerate(self.stations):
            nxt = (i + 1) % len(self.stations)
            if station.before.queue:
                waits[station.before.name] = [station.name]
            if station.pallet is not None:
                if station.phase != "done":
                    raise RuntimeError("C02 deadlock with unfinished service")
                waits[station.name] = [station.after.name]
            for source in (station.bypass, station.after):
                if source.queue:
                    waits[source.name] = (
                        [station.connector.name]
                        if station.connector is not None
                        else targets(source.queue[0][0], nxt)
                    )
            if station.connector is not None and station.connector.queue:
                waits[station.connector.name] = targets(
                    station.connector.queue[0][0], nxt
                )
        if self.feed.queue:
            waits[self.feed.name] = targets(self.feed.queue[0][0], 0)
        # Every outgoing edge ends at another occupied, blocked resource.
        # In a finite graph this proves a wait cycle, independent of pallet count.
        for blockers in waits.values():
            for name in blockers:
                used, capacity = inventory[name]
                if used != capacity or name not in waits:
                    raise RuntimeError(f"unaccounted C02 progress at {name}")
        if not waits:
            raise RuntimeError("empty C02 deadlock witness")
        return {
            "waits_for": waits,
            "occupied_capacity": {
                name: count for name, count in inventory.items() if count[0]
            },
        }

    def run(self) -> dict:
        while True:
            self.next_time = None
            self._settle()
            # A reserved pallet changes A3's routing as soon as it enters
            # the A6 input belt, before it is ready at that belt's outlet.
            a6_input = self.stations[7].before
            for _, ready_at in a6_input.queue:
                if not self._ready(ready_at - a6_input.transit):
                    break  # subsequent reservations arrive in FIFO order
            if self.next_time is None:
                # A reserved transfer or a queued pallet behind a stopped FIFO
                # head may still be travelling without enabling a new departure.
                for station in self.stations:
                    self._ready(max(station.sx_free, station.sy_free, station.due))
                    for belt in (
                        station.before,
                        station.after,
                        station.bypass,
                        station.connector,
                    ):
                        if belt is not None and belt.queue:
                            self._ready(belt.queue[-1][1])
            if self.next_time is None or self.now == self.end:
                break
            self.now = min(self.next_time, self.end)
        inventory, parts = self._inventory()
        if sorted(parts) != list(range(self.num_pallets)):
            raise RuntimeError("C02 pallet ownership is not conserved")
        deadlock = self.next_time is None

        def mean(ticks: int) -> float | None:
            return (
                ticks * self.tick_seconds / self.throughput if self.throughput else None
            )

        return {
            "num_pallets": self.num_pallets,
            "controller": self.controller,
            "unit_timing": self.unit_timing,
            "initial_seed": self.initial_seed,
            "throughput": float(self.throughput),
            "average_throughput_time": mean(self.part_ticks),
            "average_to_unload_complete_seconds": mean(self.with_unload_ticks),
            "average_including_handling_seconds": mean(self.with_handling_ticks),
            "deadlock": deadlock,
            "deadlock_witness": self._deadlock_witness(inventory) if deadlock else None,
            "stopped_at_seconds": self.now * self.tick_seconds,
            "initial_on_b1": self.initial_on_b1,
            "pending_admission": len(self.feed.queue),
            "fully_admitted_at_seconds": (
                self.filled_at * self.tick_seconds
                if self.filled_at is not None
                else None
            ),
        }


def _simevents_listing3_value(throughput: float, mean_seconds: float) -> float:
    """Literal objective minimized by Pingel and Pawletta in Listing 3."""
    return abs(throughput - mean_seconds) * throughput


def c02_pallet_study(
    min_pallets: int = 1,
    max_pallets: int = 60,
    *,
    controller: str = "first-eligible",
    unit_timing: str = "exclusive",
    initial_seed: int | None = None,
) -> dict:
    """Run independently initialized loads; rank productive, fully admitted runs."""
    _positive_count(min_pallets)
    _positive_count(max_pallets)
    if min_pallets > max_pallets:
        raise ValueError("min_pallets must not exceed max_pallets")
    runs = []
    candidates = []
    for n in range(min_pallets, max_pallets + 1):
        plant = C02Plant(
            n, controller=controller, unit_timing=unit_timing, initial_seed=initial_seed
        )
        result = plant.run()
        result.pop("deadlock_witness")  # solve_c02(n) exposes the full graph
        runs.append(result)
        if (
            not result["deadlock"]
            and result["throughput"]
            and plant.filled_at is not None
            and plant.filled_at <= plant.warmup
        ):
            candidates.append(result)
    best = min(
        candidates,
        default=None,
        key=lambda r: (
            -r["throughput"],
            r["average_throughput_time"],
            r["num_pallets"],
        ),
    )
    # Their MATLAB listing ranks only the 10..49 experiment. A shortened
    # study can evaluate just the productive loads in its intersection.
    published_scores = [
        (
            _simevents_listing3_value(r["throughput"], r["average_throughput_time"]),
            r["num_pallets"],
        )
        for r in candidates
        if 10 <= r["num_pallets"] <= 49
    ]
    score, published_best = min(published_scores, default=(None, None))
    return {
        "objective": "maximum measured throughput, then minimum mean part time, then fewest pallets",
        "best_num_pallets": best["num_pallets"] if best is not None else None,
        "simevents_listing_3": {
            "objective": "minimize abs(throughput - mean part time in seconds) * throughput",
            "published_pallet_range": [10, 49],
            "evaluated_populations": len(published_scores),
            "best_num_pallets": published_best,
            "objective_value": score,
        },
        "runs": runs,
    }
