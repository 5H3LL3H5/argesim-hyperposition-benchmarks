"""Finite causal relay-chain reference model for restricted NSA-DEVS time."""

from __future__ import annotations

import heapq
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
    if input_delay_microsteps <= 0:
        raise ValueError("input delay must be positive")

    initial_time = start_time or HyperTime(Fraction(0), 0)
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


