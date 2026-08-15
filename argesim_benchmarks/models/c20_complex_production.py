"""ARGESIM C20: Complex Production System.

This module provides an implementation of the C20 benchmark utilizing HyperTime
to ensure proper restricted NSA-DEVS timing validation.

This partial model composes the repository's reusable HyperTime DES scheduler.
It does not claim completion of the benchmark's full production-control tasks.
"""

from __future__ import annotations

import random
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from nsa_devs import DesScheduler, HyperTime


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


class SimulationEnvironment:
    """C20 adapter around the reusable HyperTime DES scheduler."""

    def __init__(self) -> None:
        self.scheduler = DesScheduler()

    @property
    def now(self) -> HyperTime:
        return self.scheduler.time

    def schedule(
        self,
        macro_delay: float,
        action: Callable[[], None],
        micro_delay: int = 1,
    ) -> None:
        """Schedule an action at now + delay."""
        self.scheduler.schedule(
            macro_delay,
            "C20-event",
            action,
            microsteps=micro_delay,
        )

    def run(self, until_macro: float, *, max_events: int = 1_000_000) -> int:
        """Execute events until the specified macro time."""

        return self.scheduler.run(until_macro, max_events=max_events)


class Conveyor:
    """Abstract conveyor to handle transport delays with HyperTime."""

    def __init__(self, env: SimulationEnvironment, transport_time: float) -> None:
        self.env = env
        self.transport_time = transport_time

    def transport(
        self,
        order: Order,
        on_arrival: Callable[[Order], None],
    ) -> None:
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

    def request(
        self,
        order: Order,
        delay: float,
        on_finish: Callable[[Order], None],
    ) -> None:
        """Request the workstation to process an order."""
        if self.busy:
            self.queue.append((order, delay, on_finish))
            self._record_history()
        else:
            self._start_processing(order, delay, on_finish)

    def _start_processing(
        self,
        order: Order,
        delay: float,
        on_finish: Callable[[Order], None],
    ) -> None:
        self.busy = True
        self._record_history()
        self.env.schedule(
            delay,
            lambda: self._finish_processing(order, on_finish),
        )

    def _finish_processing(
        self,
        current_order: Order,
        on_finish: Callable[[Order], None],
    ) -> None:
        self.processed_count += 1
        self.busy = False
        self._record_history()
        on_finish(current_order)
        if self.queue:
            next_order, next_delay, next_on_finish = self.queue.pop(0)
            self._start_processing(next_order, next_delay, next_on_finish)

    def _record_history(self) -> None:
        queue_len = len(self.queue) + (1 if self.busy else 0)
        self.history.append((float(self.env.now.macro), queue_len))


def get_process_plan(product_type: str) -> list[Operation]:
    """Return the operation sequence based on Table 2."""
    if product_type == "A":
        return [Operation.O2, Operation.O1]
    if product_type == "B":
        return [Operation.O2, Operation.O1, Operation.O3, Operation.O1]
    if product_type == "C":
        return [Operation.O2, Operation.O1, Operation.O4, Operation.O3, Operation.O1]
    if product_type == "D":
        return [Operation.O2, Operation.O1, Operation.O5, Operation.O3, Operation.O1]
    if product_type == "E":
        return [
            Operation.O2,
            Operation.O1,
            Operation.O6,
            Operation.O5,
            Operation.O3,
            Operation.O1,
        ]
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


def get_processing_time(
    ws_type: WorkStationType,
    product_type: str,
    *,
    rng: random.Random,
) -> float:
    """Processing time mapping with basic stochasticity."""
    del product_type
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
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return max(1.0, rng.gauss(base_time, base_time * 0.1))


def _generate_orders(
    appearance_strategy: Callable[[float], float],
    rush_decrease: float,
    rng: random.Random,
) -> list[Order]:
    """Generate 5000 orders complying with benchmark distribution."""
    product_choices = ["A", "B", "C", "D", "E"]
    weights = [0.40, 0.25, 0.10, 0.10, 0.15]
    orders = []
    current_time = 0.0
    for _ in range(5000):
        current_time += rng.expovariate(1.0 / 15.0)
        release_date = current_time
        product_type = rng.choices(product_choices, weights=weights)[0]
        due_gap = rng.uniform(6, 26) * 120.0
        rush_chance = 0.0
        if product_type == "B":
            rush_chance = 0.10
        elif product_type in ["C", "D", "E"]:
            rush_chance = 0.20
        is_rush = rng.random() < rush_chance
        if is_rush:
            due_gap *= 1.0 - rush_decrease
        orders.append(
            Order(
                product_type,
                release_date,
                release_date + due_gap,
                appearance_strategy(release_date),
                is_rush,
            )
        )
    return orders


def _seeded_rng(seed: int) -> random.Random:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    return random.Random(seed)


def generate_osc1_order_book(seed: int = 42) -> list[Order]:
    """Generate OSc1 order book (full information)."""
    return _generate_orders(
        lambda _release: 0.0,
        rush_decrease=0.0,
        rng=_seeded_rng(seed),
    )


def generate_osc2_order_book(seed: int = 42) -> list[Order]:
    """Generate OSc2 order book (medium info)."""
    rng = _seeded_rng(seed)
    return _generate_orders(
        lambda release: max(
            0.0,
            release - rng.gammavariate(29.4, 1.0) - 90.0,
        ),
        rush_decrease=0.10,
        rng=rng,
    )


def generate_osc3_order_book(seed: int = 42) -> list[Order]:
    """Generate OSc3 order book (reactive)."""
    return _generate_orders(
        lambda release: release,
        rush_decrease=0.20,
        rng=_seeded_rng(seed),
    )
