"""Causal, finite-storage material flow for the dimensioned C20 graph."""

from __future__ import annotations

import heapq
import math
import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field

from .c20_layout import C20Layout


@dataclass(frozen=True)
class C20FlowTrip:
    part: int
    source: str
    target: str
    requested: float
    arrived: float
    distance: float
    tracks: tuple[str, ...]
    paused_on_failed_belts: float


@dataclass
class _Part:
    identifier: int
    node: str | None
    track: str | None = None
    target: str | None = None
    path: deque[str] = field(default_factory=deque)
    ready: float = 0.0
    on_arrival: Callable[[C20FlowTrip], None] | None = None
    on_departure: Callable[[], None] | None = None
    source: str = ""
    requested: float = 0.0
    travelled: list[str] = field(default_factory=list)
    distance: float = 0.0
    paused: float = 0.0


@dataclass
class _TrackState:
    parts: deque[int] = field(default_factory=deque)
    next_entry: float = 0.0
    next_exit: float = 0.0
    failed_until: float = 0.0
    maximum_occupancy: int = 0


class C20Flow:
    """Shared event calendar, FIFO conveyors and single-place junctions.

    A part never relinquishes its upstream place until the next place accepts
    it. Travel completion alone does not free conveyor capacity. Following
    parts leave at least one second apart after a blockage clears. Failures
    pause in-flight work and stop admission/departure, rather than adding an
    independently booked delay to each future trip.
    """

    def __init__(
        self,
        *,
        layout: C20Layout | None = None,
        seed: int = 20,
        failures: bool = False,
        trace: bool = False,
    ) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        self.layout = layout or C20Layout()
        self.rng = random.Random(seed)
        self.now = 0.0
        self.events: list[tuple[float, int, Callable[[], None]]] = []
        self.sequence = 0
        self.parts: dict[int, _Part] = {}
        self.at_node: dict[str, int] = {}
        self.node_free_at = dict.fromkeys(self.layout.nodes, 0.0)
        self.closed_nodes: set[str] = set()
        self.tracks = {name: _TrackState() for name in self.layout.tracks}
        self._track_rank = {name: index for index, name in enumerate(self.tracks)}
        self._occupied_tracks: set[str] = set()
        self._failed_tracks: set[str] = set()
        self.on_change: Callable[[], None] | None = None
        self.trace_enabled = trace
        self.trace: list[tuple[float, str, int, str, int]] = []
        self.completed_trips: list[C20FlowTrip] = []
        self.failures: list[tuple[str, float, float]] = []
        self.movement_count = 0
        self._wake_times: set[float] = set()
        self._pumping = False
        self._notify_pending = False
        self._route_cache: dict[tuple[str, str, frozenset[str]], tuple[str, ...]] = {}
        if failures:
            self._schedule_failure()

    def call_at(self, when: float, callback: Callable[[], None]) -> None:
        if not math.isfinite(when) or when < self.now:
            raise ValueError("C20 events must be finite and cannot be backdated")
        self.sequence += 1
        heapq.heappush(self.events, (when, self.sequence, callback))

    def _wake_at(self, when: float) -> None:
        if when <= self.now or when in self._wake_times:
            return
        self._wake_times.add(when)

        def wake() -> None:
            self._wake_times.discard(when)
            self._pump()
            self._notify()

        self.call_at(when, wake)

    def _notify(self) -> None:
        if self.on_change is None or self._notify_pending:
            return
        self._notify_pending = True

        def notify() -> None:
            self._notify_pending = False
            if self.on_change is not None:
                self.on_change()

        self.call_at(self.now, notify)

    def set_open(self, node: str, opened: bool) -> None:
        if node not in self.layout.nodes:
            raise ValueError("unknown C20 node")
        if opened:
            self.closed_nodes.discard(node)
        else:
            self.closed_nodes.add(node)
        self._pump()

    def can_insert(self, node: str) -> bool:
        return (
            node not in self.at_node
            and node not in self.closed_nodes
            and self.node_free_at[node] <= self.now
        )

    def insert(self, identifier: int, node: str) -> bool:
        if identifier in self.parts:
            raise ValueError("part already exists in the transport system")
        if node not in self.layout.nodes:
            raise ValueError("unknown C20 insertion point")
        if not self.can_insert(node):
            if self.node_free_at[node] > self.now:
                self._wake_at(self.node_free_at[node])
            return False
        self.parts[identifier] = _Part(identifier, node)
        self.at_node[node] = identifier
        if self.trace_enabled:
            self.trace.append((self.now, "insert", identifier, node, 1))
        self._notify()
        return True

    def remove(self, identifier: int) -> None:
        part = self.parts[identifier]
        if part.node is None or part.target is not None:
            raise ValueError("only a stopped part can be removed")
        if self.trace_enabled:
            self.trace.append((self.now, "remove", identifier, part.node, 0))
        del self.at_node[part.node]
        self.node_free_at[part.node] = self.now + 1.0
        del self.parts[identifier]
        self._wake_at(self.now + 1.0)
        self._pump()
        self._notify()

    def route(self, source: str, target: str) -> tuple[str, ...]:
        self._failed_tracks = {
            name
            for name in self._failed_tracks
            if self.tracks[name].failed_until > self.now
        }
        unavailable = frozenset(self._failed_tracks)
        key = source, target, unavailable
        if key not in self._route_cache:
            try:
                path = self.layout.shortest_path(source, target, forbidden=unavailable)
            except ValueError:
                # An unavailable unique exit is waited for; topology is not
                # changed into an invented reverse or point-to-point edge.
                path = self.layout.shortest_path(source, target)
            self._route_cache[key] = path
        return self._route_cache[key]

    def send(
        self,
        identifier: int,
        target: str,
        on_arrival: Callable[[C20FlowTrip], None],
        *,
        on_departure: Callable[[], None] | None = None,
    ) -> None:
        part = self.parts[identifier]
        if part.node is None or part.target is not None:
            raise ValueError("part already has an active journey")
        path = self.route(part.node, target)
        part.source, part.requested = part.node, self.now
        part.target, part.path = target, deque(path)
        part.on_arrival, part.on_departure = on_arrival, on_departure
        part.travelled, part.distance, part.paused = [], 0.0, 0.0
        if not path:
            self._arrived(part)
        else:
            self._pump()

    def _arrived(self, part: _Part) -> None:
        if part.target is None:
            raise RuntimeError("arrival without a destination")
        trip = C20FlowTrip(
            part.identifier,
            part.source,
            part.target,
            part.requested,
            self.now,
            part.distance,
            tuple(part.travelled),
            part.paused,
        )
        self.completed_trips.append(trip)
        callback = part.on_arrival
        part.target, part.on_arrival, part.on_departure = None, None, None
        if callback is not None:
            self.call_at(self.now, lambda: callback(trip))

    def _record(self, kind: str, identifier: int, name: str) -> None:
        self.movement_count += 1
        if self.trace_enabled:
            self.trace.append(
                (self.now, kind, identifier, name, len(self.tracks[name].parts))
            )

    def _pump(self) -> None:
        if self._pumping:
            return
        self._pumping = True
        any_progress = False
        try:
            progress = True
            while progress:
                progress = False
                # Release downstream places before considering new admissions.
                # Preserve the layout's tie order while visiting only occupied
                # tracks. Set insertion order must not become a routing policy.
                for name in sorted(
                    self._occupied_tracks, key=self._track_rank.__getitem__
                ):
                    state = self.tracks[name]
                    if state.failed_until > self.now:
                        continue
                    part = self.parts[state.parts[0]]
                    target = self.layout.tracks[name].target
                    if (
                        part.ready > self.now
                        or state.next_exit > self.now
                        or not self.can_insert(target)
                    ):
                        continue
                    state.parts.popleft()
                    if not state.parts:
                        self._occupied_tracks.remove(name)
                    state.next_exit = self.now + 1.0
                    part.node, part.track = target, None
                    self.at_node[target] = part.identifier
                    part.travelled.append(name)
                    part.distance += self.layout.tracks[name].length
                    self._record("exit", part.identifier, name)
                    if target == part.target:
                        self._arrived(part)
                    progress = any_progress = True
                for node, identifier in tuple(self.at_node.items()):
                    part = self.parts[identifier]
                    if part.target is None or not part.path:
                        continue
                    name = part.path[0]
                    track, state = self.layout.tracks[name], self.tracks[name]
                    if track.source != node:
                        raise RuntimeError("discontinuous C20 route")
                    if (
                        len(state.parts) >= track.capacity
                        or state.next_entry > self.now
                        or state.failed_until > self.now
                    ):
                        continue
                    del self.at_node[node]
                    self.node_free_at[node] = self.now + 1.0
                    part.node, part.track = None, name
                    part.path.popleft()
                    part.ready = self.now + track.length  # fixed 1 m/s
                    state.parts.append(identifier)
                    self._occupied_tracks.add(name)
                    state.next_entry = self.now + 1.0
                    state.maximum_occupancy = max(
                        state.maximum_occupancy, len(state.parts)
                    )
                    self._record("enter", identifier, name)
                    if part.on_departure is not None:
                        callback, part.on_departure = part.on_departure, None
                        self.call_at(self.now, callback)
                    progress = any_progress = True
            relevant = self._occupied_tracks | {
                self.parts[identifier].path[0]
                for identifier in self.at_node.values()
                if self.parts[identifier].path
            }
            for name in sorted(relevant, key=self._track_rank.__getitem__):
                state = self.tracks[name]
                track = self.layout.tracks[name]
                if state.parts:
                    head = self.parts[state.parts[0]]
                    self._wake_at(
                        max(
                            head.ready,
                            state.next_exit,
                            state.failed_until,
                            self.node_free_at[track.target],
                        )
                    )
                identifier = self.at_node.get(track.source)
                if identifier is not None:
                    part = self.parts[identifier]
                    if part.path and part.path[0] == name:
                        self._wake_at(max(state.next_entry, state.failed_until))
            if any_progress:
                self._notify()
        finally:
            self._pumping = False

    def fail_track(self, name: str, duration: float) -> None:
        if name not in self.tracks or not math.isfinite(duration) or duration <= 0:
            raise ValueError(
                "failure needs an existing track and positive finite duration"
            )
        state = self.tracks[name]
        if state.failed_until > self.now:
            raise ValueError("track is already failed")
        finish = self.now + duration
        state.failed_until = finish
        self._failed_tracks.add(name)
        for identifier in state.parts:
            part = self.parts[identifier]
            if part.ready > self.now:
                part.ready += duration
            part.paused += duration
        self.failures.append((name, self.now, finish))
        self._wake_at(finish)
        self._notify()

    def _schedule_failure(self) -> None:
        when = self.now + self.rng.gammavariate(2.0, 1800.0)

        def fail() -> None:
            cluster = self.rng.choices(("A", "B", "C"), (0.50, 0.35, 0.15))[0]
            candidates = [
                name
                for name, track in self.layout.tracks.items()
                if track.cluster == cluster
            ]
            self.fail_track(self.rng.choice(candidates), 600.0)
            # One failed central track at a time; the next MTBF starts after repair.
            self.call_at(self.now + 600.0, self._schedule_failure)

        self.call_at(when, fail)

    def run(
        self,
        *,
        until: float | None = None,
        done: Callable[[], bool] | None = None,
        max_events: int = 5_000_000,
    ) -> int:
        if until is not None and (not math.isfinite(until) or until < self.now):
            raise ValueError("run horizon must be finite and not in the past")
        count = 0
        while self.events and (done is None or not done()):
            when, _, callback = self.events[0]
            if until is not None and when > until:
                break
            heapq.heappop(self.events)
            self.now = when
            callback()
            count += 1
            if count > max_events:
                raise RuntimeError("C20 event limit exceeded")
        if until is not None and (done is None or not done()):
            self.now = until
        return count

    def assert_conservation(self) -> None:
        if self._occupied_tracks != {
            name for name, state in self.tracks.items() if state.parts
        }:
            raise RuntimeError("C20 occupied-track index is inconsistent")
        present = list(self.at_node.values())
        for node, identifier in self.at_node.items():
            part = self.parts[identifier]
            if part.node != node or part.track is not None:
                raise RuntimeError("C20 node ownership is inconsistent")
        for name, state in self.tracks.items():
            if len(state.parts) > self.layout.tracks[name].capacity:
                raise RuntimeError("C20 conveyor capacity exceeded")
            present.extend(state.parts)
            for identifier in state.parts:
                part = self.parts[identifier]
                if part.track != name or part.node is not None:
                    raise RuntimeError("C20 conveyor ownership is inconsistent")
        if sorted(present) != sorted(self.parts):
            raise RuntimeError("C20 lost or duplicated a part")
