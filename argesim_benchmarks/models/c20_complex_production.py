"""ARGESIM C20: Complex Production System.

This module provides a specification stub for the C20 benchmark.
It contains basic types and a minimal DES loop, but the full 12-scenario
logic and workstation routing are not fully implemented.
"""

from __future__ import annotations

import heapq
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


class WorkStationType(Enum):
    I = "WS1"
    II = "WS2"
    III = "WS3"
    IV = "WS4"
    V = "WS5"

class Operation(Enum):
    O1 = "O1"
    O2 = "O2"
    O3 = "O3"
    O4 = "O4"
    O5 = "O5"
    O6 = "O6"

@dataclass(frozen=True)
class Order:
    product_type: str
    earliest_release_date: float
    due_date: float
    appearance_date: float
    rush_order_flag: bool


@dataclass(order=True)
class Event:
    time: float
    priority: int
    action: Callable[[], None] = field(compare=False)


class SimulationEnvironment:
    """Minimal DES event loop."""

    def __init__(self) -> None:
        self.now: float = 0.0
        self._events: list[Event] = []
        self._event_counter = 0

    def schedule(self, delay: float, action: Callable[[], None]) -> None:
        """Schedule an action at now + delay."""
        self._event_counter += 1
        heapq.heappush(
            self._events,
            Event(self.now + delay, self._event_counter, action),
        )

    def run(self, until: float) -> None:
        """Execute events until the specified time."""
        while self._events and self._events[0].time <= until:
            event = heapq.heappop(self._events)
            self.now = event.time
            event.action()
        self.now = until


class WorkStation:
    """A simple resource for processing orders."""

    def __init__(self, env: SimulationEnvironment, ws_type: WorkStationType) -> None:
        self.env = env
        self.ws_type = ws_type
        self.busy = False
        self.queue: list[Order] = []
        self.processed_count = 0

    def request(self, order: Order, delay: float) -> None:
        """Request the workstation to process an order."""
        if self.busy:
            self.queue.append((order, delay))
        else:
            self._start_processing(order, delay)

    def _start_processing(self, order: Order, delay: float) -> None:
        self.busy = True
        self.env.schedule(delay, self._finish_processing)

    def _finish_processing(self) -> None:
        self.processed_count += 1
        if self.queue:
            next_order, next_delay = self.queue.pop(0)
            self._start_processing(next_order, next_delay)
        else:
            self.busy = False

def generate_osc1_order_book() -> list[Order]:
    """Generate a minimal OSc1 order book (full information)."""
    return [
        Order("A", 1.0, 822.5, 0.0, False),
        Order("B", 2.0, 1525.5, 0.0, False),
        Order("C", 3.0, 2000.0, 0.0, False),
    ]

def generate_osc2_order_book() -> list[Order]:
    """Generate a minimal OSc2 order book (medium info)."""
    return [
        Order("A", 1.0, 822.5, 7.8, False),
        Order("B", 2.0, 1525.5, 47.7, False),
        Order("C", 3.0, 2000.0, 100.0, False),
    ]

def generate_osc3_order_book() -> list[Order]:
    """Generate a minimal OSc3 order book (reactive)."""
    return [
        Order("A", 1.0, 822.5, 1.0, False),
        Order("B", 2.0, 1525.5, 2.0, False),
        Order("C", 3.0, 2000.0, 3.0, False),
    ]
