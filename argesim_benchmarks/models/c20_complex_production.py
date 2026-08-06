"""ARGESIM C20: Complex Production System.

This module provides an implementation of the C20 benchmark utilizing HyperTime
to ensure proper restricted NSA-DEVS timing validation.

Note: While this implementation uses HyperTime to preserve strict causal ordering,
it is not formally derived into atomic or coupled DEVS components. The repository's
`nsa_devs` core currently only provides a restricted relay chain reference and
lacks a general DEVS simulation framework for formal component derivation.
"""

from __future__ import annotations

import heapq
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction

from nsa_devs.hypertime import HyperTime


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
    time: HyperTime
    priority: int
    action: Callable[[], None] = field(compare=False)


class SimulationEnvironment:
    """Minimal DES event loop utilizing HyperTime for causal ordering."""

    def __init__(self) -> None:
        self.now: HyperTime = HyperTime(Fraction(0), 0)
        self._events: list[Event] = []
        self._event_counter = 0

    def schedule(self, macro_delay: float, action: Callable[[], None], micro_delay: int = 1) -> None:
        """Schedule an action at now + delay.

        Uses HyperTime to preserve strict analytical order for restricted NSA-DEVS.
        """
        self._event_counter += 1

        # Advance macro time if there is a real delay
        if macro_delay > 0:
            target_time = HyperTime(self.now.macro + Fraction(macro_delay).limit_denominator(), 0)
        else:
            # Advance purely in micro-steps for causal chains happening at the same macro time
            target_time = self.now.after_epsilon(micro_delay)

        heapq.heappush(
            self._events,
            Event(target_time, self._event_counter, action),
        )

    def run(self, until_macro: float) -> None:
        """Execute events until the specified macro time."""
        limit = Fraction(until_macro).limit_denominator()
        while self._events and self._events[0].time.macro <= limit:
            event = heapq.heappop(self._events)
            self.now = event.time
            event.action()
        # Cap the clock at the until limit
        self.now = HyperTime(limit, 0)


class Conveyor:
    """Abstract conveyor to handle transport delays with HyperTime."""

    def __init__(self, env: SimulationEnvironment, transport_time: float) -> None:
        self.env = env
        self.transport_time = transport_time

    def transport(self, order: Order, on_arrival: Callable[[Order], None]) -> None:
        self.env.schedule(self.transport_time, lambda: on_arrival(order))


class WorkStation:
    """A simple resource for processing orders with HyperTime scheduling."""

    def __init__(self, env: SimulationEnvironment, ws_type: WorkStationType) -> None:
        self.env = env
        self.ws_type = ws_type
        self.busy = False
        self.queue: list[tuple[Order, float, Callable[[Order], None]]] = []
        self.processed_count = 0
        self.history: list[tuple[float, int]] = []

    def request(self, order: Order, delay: float, on_finish: Callable[[Order], None]) -> None:
        """Request the workstation to process an order."""
        if self.busy:
            self.queue.append((order, delay, on_finish))
            self._record_history()
        else:
            self._start_processing(order, delay, on_finish)

    def _start_processing(self, order: Order, delay: float, on_finish: Callable[[Order], None]) -> None:
        self.busy = True
        self._record_history()
        self.env.schedule(delay, lambda: self._finish_processing(order, on_finish))

    def _finish_processing(self, current_order: Order, on_finish: Callable[[Order], None]) -> None:
        self.processed_count += 1
        self.busy = False
        self._record_history()

        # Fire callback first before taking next from queue,
        # so order proceeds down its route
        on_finish(current_order)

        if self.queue:
            next_order, next_delay, next_on_finish = self.queue.pop(0)
            self._start_processing(next_order, next_delay, next_on_finish)

    def _record_history(self) -> None:
        """Record the queue length for trajectories/plotting."""
        queue_len = len(self.queue) + (1 if self.busy else 0)
        self.history.append((float(self.env.now.macro), queue_len))


def get_process_plan(product_type: str) -> list[Operation]:
    """Return the operation sequence based on Table 2."""
    if product_type == "A":
        return [Operation.O2, Operation.O1]
    elif product_type == "B":
        return [Operation.O2, Operation.O1, Operation.O3, Operation.O1]
    elif product_type == "C":
        return [Operation.O2, Operation.O1, Operation.O4, Operation.O3, Operation.O1]
    elif product_type == "D":
        return [Operation.O2, Operation.O1, Operation.O5, Operation.O3, Operation.O1]
    elif product_type == "E":
        return [Operation.O2, Operation.O1, Operation.O6, Operation.O5, Operation.O3, Operation.O1]
    raise ValueError(f"Unknown product type: {product_type}")

def get_operation_ws(op: Operation) -> WorkStationType:
    """Map operations to workstation types based on Table 1."""
    mapping = {
        Operation.O1: WorkStationType.I,
        Operation.O2: WorkStationType.II,
        Operation.O3: WorkStationType.III,
        Operation.O4: WorkStationType.V,
        Operation.O5: WorkStationType.V,
        Operation.O6: WorkStationType.IV,
    }
    return mapping[op]

def get_processing_time(ws_type: WorkStationType, product_type: str) -> float:
    """Processing time mapping with basic stochasticity."""
    base_time = 10.0
    if ws_type == WorkStationType.I:
        base_time = 20.0
    elif ws_type == WorkStationType.II:
        base_time = 30.0
    elif ws_type == WorkStationType.III:
        base_time = 44.0
    elif ws_type == WorkStationType.IV:
        base_time = 120.0
    elif ws_type == WorkStationType.V:
        base_time = 60.0
    # Simulate a gamma or normal distribution-like variance
    return max(1.0, random.gauss(base_time, base_time * 0.1))


def _generate_orders(appearance_strategy: Callable[[float], float], rush_decrease: float) -> list[Order]:
    """Generate 5000 orders complying with benchmark distribution."""
    product_choices = ["A", "B", "C", "D", "E"]
    weights = [0.40, 0.25, 0.10, 0.10, 0.15]

    orders = []
    current_time = 0.0

    for i in range(5000):
        # Earliest release date follows exponential inter-arrival
        inter_arrival = random.expovariate(1.0 / 15.0)
        current_time += inter_arrival
        release_date = current_time

        # Product type distribution
        ptype = random.choices(product_choices, weights=weights)[0]

        # Determine due gap based on random work content (simplified representation)
        a, b = 6, 26 # Range from Table 2 parameters
        due_gap = random.uniform(a, b) * 120.0 # Approximation of sum of ops

        # Rush order flag based on product type (0% for A, 10% for B, 20% for others)
        rush_chance = 0.0
        if ptype == "B": rush_chance = 0.10
        elif ptype in ["C", "D", "E"]: rush_chance = 0.20

        is_rush = random.random() < rush_chance

        if is_rush:
            due_gap *= (1.0 - rush_decrease)

        due_date = release_date + due_gap
        appearance_date = appearance_strategy(release_date)

        orders.append(Order(ptype, release_date, due_date, appearance_date, is_rush))

    return orders


def generate_osc1_order_book() -> list[Order]:
    """Generate OSc1 order book (full information)."""
    return _generate_orders(lambda r: 0.0, rush_decrease=0.0)

def generate_osc2_order_book() -> list[Order]:
    """Generate OSc2 order book (medium info)."""
    # Offset simulated by reducing the warning horizon
    return _generate_orders(lambda r: max(0.0, r - random.gammavariate(29.4, 1.0) - 90.0), rush_decrease=0.10)

def generate_osc3_order_book() -> list[Order]:
    """Generate OSc3 order book (reactive)."""
    return _generate_orders(lambda r: r, rush_decrease=0.20)
