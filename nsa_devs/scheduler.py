"""Finite causal relay-chain reference model for restricted NSA-DEVS time."""

from __future__ import annotations

import heapq
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from fractions import Fraction

from .hypertime import HyperTime


@dataclass(frozen=True)
class ProcessedEvent:
    component: int
    input_time: HyperTime
    output_time: HyperTime
    input_payload: int
    output_payload: int


@dataclass(frozen=True)
class RelayResult:
    final_payload: int
    trace: tuple[ProcessedEvent, ...]

    @property
    def checksum(self) -> int:
        """Stable arithmetic checksum used for benchmark result parity."""

        value = 0
        for event in self.trace:
            value = (
                value * 1_000_003
                + event.component * 97
                + event.output_time.micro * 31
                + event.output_payload
            ) % 2_147_483_647
        return value


@dataclass(order=True)
class DesEvent:
    """An event ordered by superdense time, priority, then insertion sequence."""

    time: HyperTime
    priority: int = field(default=0, kw_only=True)
    sequence: int
    name: str = field(compare=False)
    handler: Callable[..., None] = field(compare=False)
    args: tuple[object, ...] = field(compare=False, default=())
    cancelled: bool = field(compare=False, default=False)


class DesScheduler:
    """A deterministic HyperTime discrete-event scheduler.

    At the same macro time and microstep, lower priority numbers run first;
    equal priorities retain insertion order. Priority orders pending events
    only and cannot precede a handler that has already run. Models must assign
    priorities explicitly when simultaneous events need domain-specific order.
    """

    def __init__(self, initial_time: HyperTime | None = None):
        if initial_time is not None and not isinstance(initial_time, HyperTime):
            raise TypeError("initial_time must be HyperTime")
        self.time = initial_time if initial_time is not None else HyperTime.at(0)
        self.events: list[DesEvent] = []
        self.event_sequence = 0

    def schedule(
        self,
        delay_minutes: float,
        name: str,
        handler: Callable[..., None],
        *args: object,
        microsteps: int = 1,
        priority: int = 0,
    ) -> DesEvent:
        if isinstance(delay_minutes, bool):
            raise TypeError("delay must be a real number")
        delay = float(delay_minutes)
        if not math.isfinite(delay) or delay < 0.0:
            raise ValueError("delay must be finite and non-negative")
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if not callable(handler):
            raise TypeError("handler must be callable")
        if not isinstance(microsteps, int) or isinstance(microsteps, bool):
            raise TypeError("microsteps must be an integer")
        if microsteps <= 0:
            raise ValueError("microsteps must be positive")
        target_time = (
            self.time.after_epsilon(microsteps)
            if delay == 0.0
            else self.time.after_finite(delay)
        )
        return self.schedule_at(target_time, name, handler, *args, priority=priority)

    def schedule_at(
        self,
        time: HyperTime,
        name: str,
        handler: Callable[..., None],
        *args: object,
        priority: int = 0,
    ) -> DesEvent:
        """Schedule at an absolute superdense time and return a cancel token."""

        if not isinstance(time, HyperTime):
            raise TypeError("time must be HyperTime")
        if time < self.time:
            raise ValueError("cannot schedule an event in the past")
        if not isinstance(name, str) or not name:
            raise ValueError("name must be a non-empty string")
        if not callable(handler):
            raise TypeError("handler must be callable")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise TypeError("priority must be an integer")
        event = DesEvent(
            time, self.event_sequence, name, handler, args, priority=priority
        )
        heapq.heappush(
            self.events,
            event,
        )
        self.event_sequence += 1
        return event

    @staticmethod
    def cancel(event: DesEvent) -> None:
        """Cancel a pending event; cancellation is idempotent."""

        if not isinstance(event, DesEvent):
            raise TypeError("event must be DesEvent")
        event.cancelled = True

    def _process_next(self) -> bool:
        while self.events:
            event = heapq.heappop(self.events)
            if event.cancelled:
                continue
            self.time = event.time
            event.handler(*event.args)
            return True
        return False

    def _discard_cancelled(self) -> None:
        while self.events and self.events[0].cancelled:
            heapq.heappop(self.events)

    def run(self, until: float, *, max_events: int = 1_000_000) -> int:
        if isinstance(until, bool):
            raise TypeError("until must be a real number")
        until_value = float(until)
        if not math.isfinite(until_value):
            raise ValueError("until must be finite")
        if not isinstance(max_events, int) or isinstance(max_events, bool):
            raise TypeError("max_events must be an integer")
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        until_time = HyperTime.at(until_value)
        if until_time.macro < self.time.macro:
            raise ValueError("until cannot precede the current scheduler time")
        processed = 0
        # A finite macro-time horizon includes every microstep at that macro
        # time. This lets zero-delay event cascades settle before run returns.
        while True:
            self._discard_cancelled()
            if not self.events or self.events[0].time.macro > until_time.macro:
                break
            if processed >= max_events:
                raise RuntimeError("scheduler exceeded max_events")
            if self._process_next():
                processed += 1
        if self.time.macro < until_time.macro:
            self.time = until_time
        return processed

    def run_until_idle(self, *, max_events: int = 1_000_000) -> int:
        """Drain the queue, including finite and infinitesimal event cascades."""

        if not isinstance(max_events, int) or isinstance(max_events, bool):
            raise TypeError("max_events must be an integer")
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        processed = 0
        while True:
            self._discard_cancelled()
            if not self.events:
                break
            if processed >= max_events:
                raise RuntimeError("scheduler exceeded max_events")
            if self._process_next():
                processed += 1
        return processed


@dataclass(order=True)
class _QueuedInput:
    time: HyperTime
    sequence: int
    component: int = field(compare=False)
    payload: int = field(compare=False)


def run_relay_chain(
    length: int,
    initial_payload: int = 0,
    start_time: HyperTime | None = None,
    input_delay_microsteps: int = 1,
) -> RelayResult:
    """Run a finite acyclic chain of deterministic Mealy-style relays.

    Each component increments the payload and emits after a positive
    infinitesimal delay. The function models only the finite reference case;
    it is not a general coupled NSA-DEVS simulator.
    """

    if not isinstance(length, int) or isinstance(length, bool):
        raise TypeError("length must be an integer")
    if length <= 0:
        raise ValueError("length must be positive")
    if not isinstance(input_delay_microsteps, int) or isinstance(
        input_delay_microsteps, bool
    ):
        raise TypeError("input delay must be an integer")
    if input_delay_microsteps <= 0:
        raise ValueError("input delay must be positive")
    if not isinstance(initial_payload, int) or isinstance(initial_payload, bool):
        raise TypeError("initial_payload must be an integer")
    if start_time is not None and not isinstance(start_time, HyperTime):
        raise TypeError("start_time must be HyperTime")

    initial_time = start_time if start_time is not None else HyperTime(Fraction(0), 0)
    queue: list[_QueuedInput] = [_QueuedInput(initial_time, 0, 0, initial_payload)]
    trace: list[ProcessedEvent] = []
    sequence = 1

    while queue:
        item = heapq.heappop(queue)
        output_time = item.time.after_epsilon(input_delay_microsteps)
        output_payload = item.payload + 1
        trace.append(
            ProcessedEvent(
                component=item.component,
                input_time=item.time,
                output_time=output_time,
                input_payload=item.payload,
                output_payload=output_payload,
            )
        )

        next_component = item.component + 1
        if next_component < length:
            heapq.heappush(
                queue,
                _QueuedInput(output_time, sequence, next_component, output_payload),
            )
            sequence += 1

    return RelayResult(final_payload=trace[-1].output_payload, trace=tuple(trace))
