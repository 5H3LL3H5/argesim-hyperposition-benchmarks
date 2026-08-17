"""ARGESIM C20: Complex Production System.

The small public components at the top remain useful independently.  The full
scenario engine below adds the official order books, alternative routes,
workstation generations, setup/tool changes, failures, transport, due dates,
and replication summaries while retaining HyperTime for event ordering.
"""

from __future__ import annotations

import heapq
import math
import random
import statistics
from collections.abc import Callable, Sequence
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
    identifier: int = 0


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


class C20ConveyorCluster(str, Enum):
    """Failure-impact clusters from Figure 4 of the definition."""

    A = "A"
    B = "B"
    C = "C"


@dataclass
class C20ConveyorElement:
    """One capacity-constrained, constant-speed conveyor element.

    The benchmark specifies a speed of 1 m/s and one-metre parts.  Enforcing
    the corresponding one-second entry headway gives an element of length
    ``L`` its specified capacity of ``floor(L)`` parts without discretising
    the belt into cells.
    """

    name: str
    length: float
    cluster: C20ConveyorCluster
    speed: float = 1.0
    part_length: float = 1.0
    next_entry: float = 0.0

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("a conveyor element needs a name")
        if not math.isfinite(self.length) or self.length <= 0.0:
            raise ValueError("conveyor length must be positive and finite")
        if not math.isfinite(self.speed) or self.speed <= 0.0:
            raise ValueError("conveyor speed must be positive and finite")
        if not math.isfinite(self.part_length) or self.part_length <= 0.0:
            raise ValueError("part length must be positive and finite")
        if self.part_length > self.length:
            raise ValueError("a part must fit on its conveyor element")
        self.cluster = C20ConveyorCluster(self.cluster)

    @property
    def capacity(self) -> int:
        return max(1, math.floor(self.length / self.part_length))

    @property
    def travel_time(self) -> float:
        return self.length / self.speed

    @property
    def entry_headway(self) -> float:
        return self.part_length / self.speed


@dataclass(frozen=True)
class C20ConveyorFailure:
    element: str
    cluster: C20ConveyorCluster
    start: float
    finish: float


@dataclass(frozen=True)
class C20TransportTrace:
    source_area: int
    target_area: int
    departure: float
    arrival: float
    distance: float
    elements: tuple[str, ...]
    capacity_delay: float
    failure_delay: float


class C20ConveyorNetwork:
    """Reusable C20 transport model for the dimensioned two-cycle layout.

    Areas are numbered as in Figure 4: source/sink 0, lower-left 1,
    lower-right 2, and upper-right 3.  The outer and inner cycles provide the
    two directed alternatives between areas.  Processing-area ingress and
    egress use the 26 m depth from Figure 5; a same-area transfer traverses
    its 55 m local loop.  In PSc4, exactly one element fails at a time and is
    selected with the official A/B/C probabilities followed by a uniform
    choice within the selected cluster.
    """

    _AREA_ORDER = (0, 3, 2, 1)
    _CLUSTER_WEIGHTS = (0.50, 0.35, 0.15)

    def __init__(
        self,
        *,
        seed: int = 20,
        failures: bool = False,
        speed: float = 1.0,
        part_length: float = 1.0,
    ) -> None:
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("seed must be an integer")
        self.rng = random.Random(seed)
        self.failures_enabled = bool(failures)
        self.elements: dict[str, C20ConveyorElement] = {}
        for area in (1, 2, 3):
            self._add(f"ingress_{area}", 26.0, C20ConveyorCluster.A, speed, part_length)
            self._add(f"egress_{area}", 26.0, C20ConveyorCluster.A, speed, part_length)
            self._add(f"local_{area}", 55.0, C20ConveyorCluster.A, speed, part_length)
        # Figure 4 gives 138 m horizontally and 20 m vertically.  Splitting
        # at the area junctions yields the following dimensioned links.
        lengths = (69.0, 20.0, 69.0, 20.0)
        for index, source in enumerate(self._AREA_ORDER):
            target = self._AREA_ORDER[(index + 1) % 4]
            self._add(
                f"outer_{source}_{target}",
                lengths[index],
                C20ConveyorCluster.C,
                speed,
                part_length,
            )
            self._add(
                f"inner_{target}_{source}",
                lengths[index],
                C20ConveyorCluster.B,
                speed,
                part_length,
            )
        self.failures: list[C20ConveyorFailure] = []
        self._next_failure = (
            self.rng.gammavariate(2.0, 0.5 * 3600.0)
            if self.failures_enabled
            else math.inf
        )
        self.distance = 0.0
        self.capacity_delay = 0.0
        self.failure_delay = 0.0

    def _add(
        self,
        name: str,
        length: float,
        cluster: C20ConveyorCluster,
        speed: float,
        part_length: float,
    ) -> None:
        self.elements[name] = C20ConveyorElement(
            name,
            length,
            cluster,
            speed,
            part_length,
        )

    def _ensure_failures(self, until: float) -> None:
        while self._next_failure <= until:
            cluster = self.rng.choices(
                tuple(C20ConveyorCluster),
                weights=self._CLUSTER_WEIGHTS,
                k=1,
            )[0]
            candidates = tuple(
                element for element in self.elements.values() if element.cluster is cluster
            )
            selected = self.rng.choice(candidates)
            finish = self._next_failure + 600.0
            self.failures.append(
                C20ConveyorFailure(selected.name, cluster, self._next_failure, finish)
            )
            # Only one element is disrupted at a time; the next MTBF starts
            # after the fixed repair interval.
            self._next_failure = finish + self.rng.gammavariate(2.0, 0.5 * 3600.0)

    def _ring_path(self, source: int, target: int, *, outer: bool) -> tuple[str, ...]:
        order = self._AREA_ORDER
        if not outer:
            order = tuple(reversed(order))
        position = order.index(source)
        path = []
        while order[position] != target:
            next_position = (position + 1) % len(order)
            left = order[position]
            right = order[next_position]
            prefix = "outer" if outer else "inner"
            path.append(f"{prefix}_{left}_{right}")
            position = next_position
        return tuple(path)

    def _path_cost(self, path: Sequence[str], departure: float) -> float:
        cost = 0.0
        for name in path:
            element = self.elements[name]
            cost += element.travel_time + max(0.0, element.next_entry - departure)
            for failure in self.failures:
                if (
                    failure.element == name
                    and failure.start <= departure < failure.finish
                ):
                    cost += failure.finish - departure
        return cost

    def _select_path(self, source: int, target: int, departure: float) -> tuple[str, ...]:
        if source == target:
            return () if source == 0 else (f"local_{source}",)
        outer = self._ring_path(source, target, outer=True)
        inner = self._ring_path(source, target, outer=False)
        # Deterministic tie breaking keeps seeded replications reproducible.
        return min((outer, inner), key=lambda path: (self._path_cost(path, departure), path))

    def _traverse(
        self,
        element: C20ConveyorElement,
        departure: float,
    ) -> tuple[float, float, float]:
        queued_start = max(departure, element.next_entry)
        capacity_delay = queued_start - departure
        start = queued_start
        # A failed belt cannot accept another part.  Move the actual entry to
        # the end of any repair already in progress before reserving headway.
        for failure in self.failures:
            if (
                failure.element == element.name
                and failure.start <= start < failure.finish
            ):
                start = failure.finish
        element.next_entry = start + element.entry_headway
        arrival = start + element.travel_time
        failure_delay = start - queued_start
        for failure in self.failures:
            if failure.element != element.name:
                continue
            if start >= failure.finish or arrival <= failure.start:
                continue
            if start < failure.start:
                delay = failure.finish - failure.start
            else:
                delay = failure.finish - start
                start = failure.finish
            arrival += delay
            failure_delay += delay
        return arrival, capacity_delay, failure_delay

    def transport(self, departure: float, source_area: int, target_area: int) -> C20TransportTrace:
        """Reserve a route and return its physically scheduled arrival."""

        if source_area not in {0, 1, 2, 3} or target_area not in {0, 1, 2, 3}:
            raise ValueError("C20 areas must be numbered 0 through 3")
        if not math.isfinite(departure) or departure < 0.0:
            raise ValueError("departure must be non-negative and finite")
        self._ensure_failures(departure + 2_000.0)
        path = list(self._select_path(source_area, target_area, departure))
        if source_area != target_area and source_area != 0:
            path.insert(0, f"egress_{source_area}")
        if source_area != target_area and target_area != 0:
            path.append(f"ingress_{target_area}")
        now = departure
        capacity_delay = 0.0
        failure_delay = 0.0
        distance = 0.0
        for name in path:
            element = self.elements[name]
            now, queued, disrupted = self._traverse(element, now)
            capacity_delay += queued
            failure_delay += disrupted
            distance += element.length
        self.distance += distance
        self.capacity_delay += capacity_delay
        self.failure_delay += failure_delay
        return C20TransportTrace(
            source_area,
            target_area,
            departure,
            now,
            distance,
            tuple(path),
            capacity_delay,
            failure_delay,
        )


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
    """Return the first official alternative for backwards compatibility."""

    return list(get_process_plans(product_type)[0])


def get_process_plans(product_type: str) -> tuple[tuple[Operation, ...], ...]:
    """Return all Table-2 process-plan alternatives."""

    o = Operation
    plans = {
        "A": ((o.O2, o.O1),),
        "B": (
            (o.O2, o.O1, o.O3, o.O1),
            (o.O3, o.O1, o.O2, o.O1),
        ),
        "C": (
            (o.O2, o.O1, o.O4, o.O3, o.O1),
            (o.O4, o.O3, o.O1, o.O2, o.O1),
        ),
        "D": (
            (o.O2, o.O1, o.O5, o.O3, o.O1),
            (o.O5, o.O3, o.O1, o.O2, o.O1),
        ),
        "E": (
            (o.O2, o.O1, o.O6, o.O5, o.O3, o.O1),
            (o.O6, o.O5, o.O3, o.O1, o.O2, o.O1),
        ),
    }
    try:
        return plans[product_type]
    except KeyError as exc:
        raise ValueError(f"Unknown product type: {product_type}") from exc


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
    """Return the deterministic Table-1 processing duration in seconds."""

    if product_type not in {"A", "B", "C", "D", "E"}:
        raise ValueError(f"Unknown product type: {product_type}")
    base_time = 20.0
    if ws_type == WorkStationType.I:
        base_time = 20.0
    elif ws_type == WorkStationType.II:
        base_time = 30.0
    elif ws_type == WorkStationType.III:
        base_time = {"B": 40.0, "C": 44.0, "D": 44.0, "E": 50.0}.get(
            product_type, 44.0
        )
    elif ws_type == WorkStationType.IV:
        base_time = 120.0
    elif ws_type == WorkStationType.V:
        base_time = 90.0 if product_type == "E" else 60.0
    if not isinstance(rng, random.Random):
        raise TypeError("rng must be random.Random")
    return base_time


def _generate_orders(
    appearance_strategy: Callable[[float], float],
    rush_decrease: float,
    rng: random.Random,
    count: int = 5000,
) -> list[Order]:
    """Generate 5000 orders complying with benchmark distribution."""
    product_choices = ["A", "B", "C", "D", "E"]
    weights = [0.40, 0.25, 0.10, 0.10, 0.15]
    orders = []
    current_time = 0.0
    due_factors = {
        "A": (13.0, 20.0),
        "B": (10.0, 12.0),
        "C": (9.0, 26.0),
        "D": (7.0, 10.0),
        "E": (6.0, 10.0),
    }
    nominal_work = {"A": 44.0, "B": 104.0, "C": 168.0, "D": 168.0, "E": 324.0}
    for identifier in range(count):
        current_time += rng.expovariate(1.0 / 15.0)
        release_date = current_time
        product_type = rng.choices(product_choices, weights=weights)[0]
        low, high = due_factors[product_type]
        due_gap = rng.uniform(low, high) * nominal_work[product_type]
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
                identifier,
            )
        )
    return orders


def _seeded_rng(seed: int) -> random.Random:
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    return random.Random(seed)


def generate_osc1_order_book(seed: int = 42, *, count: int = 5000) -> list[Order]:
    """Generate OSc1 order book (full information)."""
    return _generate_orders(
        lambda _release: 0.0,
        rush_decrease=0.0,
        rng=_seeded_rng(seed),
        count=count,
    )


def generate_osc2_order_book(seed: int = 42, *, count: int = 5000) -> list[Order]:
    """Generate OSc2 order book (medium info)."""
    rng = _seeded_rng(seed)
    appearance_rng = _seeded_rng(seed + 2_000_033)
    return _generate_orders(
        lambda release: max(
            0.0,
            release - appearance_rng.gammavariate(29.4, 1.0) - 90.0,
        ),
        rush_decrease=0.10,
        rng=rng,
        count=count,
    )


def generate_osc3_order_book(seed: int = 42, *, count: int = 5000) -> list[Order]:
    """Generate OSc3 order book (reactive)."""
    return _generate_orders(
        lambda release: release,
        rush_decrease=0.20,
        rng=_seeded_rng(seed),
        count=count,
    )


# --- Full 12-scenario production benchmark ---


class C20OrderScenario(str, Enum):
    OSC1 = "OSc1"
    OSC2 = "OSc2"
    OSC3 = "OSc3"


class C20PlantScenario(str, Enum):
    PSC1 = "PSc1"
    PSC2 = "PSc2"
    PSC3 = "PSc3"
    PSC4 = "PSc4"


C20_PRODUCT_WEIGHTS = {"A": 0.40, "B": 0.90, "C": 1.42, "D": 1.42, "E": 2.21}


@dataclass(frozen=True)
class C20OrderResult:
    identifier: int
    product_type: str
    release_date: float
    completion_date: float
    due_date: float
    throughput_time: float
    tardiness: float
    weighted_tardiness: float
    max_nok_violations: int
    max_ok_violations: int
    disruption_nok: int


@dataclass(frozen=True)
class C20ReplicationResult:
    order_scenario: C20OrderScenario
    plant_scenario: C20PlantScenario
    seed: int
    makespan: float
    median_throughput_time: float
    tardy_orders: int
    weighted_tardiness: float
    max_nok_parts: int
    max_ok_parts: int
    completed_orders: int
    orders: tuple[C20OrderResult, ...]
    transport_distance: float = 0.0
    conveyor_failures: int = 0
    conveyor_capacity_delay: float = 0.0
    conveyor_failure_delay: float = 0.0


@dataclass(frozen=True)
class C20Statistic:
    median: float
    first_quartile: float
    third_quartile: float

    @property
    def iqr(self) -> float:
        return self.third_quartile - self.first_quartile


@dataclass(frozen=True)
class C20ScenarioSummary:
    order_scenario: C20OrderScenario
    plant_scenario: C20PlantScenario
    replications: int
    makespan: C20Statistic
    throughput_time: C20Statistic
    tardy_orders: C20Statistic
    weighted_tardiness: C20Statistic
    max_nok_parts: C20Statistic
    max_ok_parts: C20Statistic


@dataclass
class _C20Machine:
    name: str
    ws_type: WorkStationType
    generation: int
    next_failure: float
    mttr: float
    failure_shape: float
    failure_scale_hours: float
    area: int = 0
    busy: bool = False
    last_operation: Operation | None = None
    tool_usage: float = 0.0

    def supports(self, operation: Operation, product: str) -> bool:
        if self.ws_type is not get_operation_ws(operation):
            return False
        if self.ws_type is WorkStationType.II:
            limits = {1: {"A", "B"}, 2: {"A", "B", "C", "D"}, 3: {"A", "B", "C", "D", "E"}}
            return product in limits[self.generation]
        if self.ws_type is WorkStationType.III:
            return product in {"B", "C", "D", "E"}
        if self.ws_type is WorkStationType.IV:
            return product == "E" and operation is Operation.O6
        if self.ws_type is WorkStationType.V:
            return (operation is Operation.O4 and product == "C") or (
                operation is Operation.O5 and product in {"D", "E"}
            )
        return True

    def processing_time(self, operation: Operation, product: str) -> float:
        if self.ws_type is WorkStationType.I:
            return 20.0
        if self.ws_type is WorkStationType.II:
            return {1: 30.0, 2: 27.0, 3: 24.0}[self.generation]
        if self.ws_type is WorkStationType.III:
            return {"B": 40.0, "C": 44.0, "D": 44.0, "E": 50.0}[product]
        if self.ws_type is WorkStationType.IV:
            return 120.0
        if self.ws_type is WorkStationType.V:
            return 90.0 if product == "E" else 60.0
        raise AssertionError(operation)

    def complete(
        self,
        start: float,
        duration: float,
        rng: random.Random,
        *,
        damage_on_failure: bool = True,
    ) -> tuple[float, bool]:
        """Advance work through calendar-time gamma failures.

        A workstation is empty during tool and operation changes in the
        definition.  ``damage_on_failure=False`` therefore lets a setup
        resume after repair without incorrectly scrapping a part.
        """

        if self.failure_shape <= 0.0:
            return start + duration, False
        while self.next_failure <= start:
            repair_finish = self.next_failure + self.mttr
            if start < repair_finish:
                start = repair_finish
            self.next_failure = repair_finish + rng.gammavariate(
                self.failure_shape, self.failure_scale_hours * 3600.0
            )
        remaining = duration
        now = start
        while now + remaining > self.next_failure:
            failure_time = self.next_failure
            remaining -= self.next_failure - now
            now = self.next_failure + self.mttr
            self.next_failure = now + rng.gammavariate(
                self.failure_shape, self.failure_scale_hours * 3600.0
            )
            if damage_on_failure and self.ws_type is not WorkStationType.I:
                # Table 1: every type except I damages the in-process part.
                return failure_time + self.mttr, True
        return now + remaining, False


@dataclass
class _C20Context:
    order: Order
    plan: tuple[Operation, ...]
    index: int = 0
    previous_completion: float | None = None
    max_nok: int = 0
    max_ok: int = 0
    disruption_nok: int = 0
    area: int = 0


@dataclass(frozen=True)
class _C20Task:
    context: int
    operation: Operation
    ready: float
    area: int


_FAILURES = {
    C20PlantScenario.PSC2: {
        "I": (4.450, 0.100, 160.0),
        "II1": (2.400, 0.125, 135.0),
        "II2": (3.750, 0.100, 135.0),
        "II3": (15.000, 0.050, 135.0),
        "III": (6.120, 0.100, 220.0),
        "IV": (8.340, 0.100, 365.0),
        "V": (10.140, 0.100, 300.0),
    },
    C20PlantScenario.PSC3: {
        "I": (1.115, 0.200, 160.0),
        "II1": (0.742, 0.225, 135.0),
        "II2": (0.940, 0.200, 135.0),
        "II3": (1.667, 0.150, 135.0),
        "III": (1.530, 0.200, 220.0),
        "IV": (2.085, 0.200, 365.0),
        "V": (2.535, 0.100, 300.0),
    },
}
_FAILURES[C20PlantScenario.PSC4] = _FAILURES[C20PlantScenario.PSC3]


def _machine_failure_key(ws_type: WorkStationType, generation: int) -> str:
    return "II" + str(generation) if ws_type is WorkStationType.II else ws_type.name


def _c20_machines(scenario: C20PlantScenario, rng: random.Random) -> list[_C20Machine]:
    definitions = (
        *((WorkStationType.I, 0, index + 1, 1 + index // 2) for index in range(6)),
        *((WorkStationType.II, 1, index + 1, 1) for index in range(2)),
        (WorkStationType.II, 2, 3, 1),
        (WorkStationType.II, 3, 4, 1),
        *((WorkStationType.III, 0, index + 1, 2) for index in range(3)),
        *((WorkStationType.IV, 0, index + 1, 3) for index in range(2)),
        *((WorkStationType.V, 0, index + 1, 2 + index // 2) for index in range(4)),
    )
    machines = []
    failures = _FAILURES.get(scenario, {})
    for ws_type, generation, number, area in definitions:
        key = _machine_failure_key(ws_type, generation)
        shape, scale, mttr = failures.get(key, (0.0, 0.0, 0.0))
        next_failure = math.inf if shape == 0.0 else rng.gammavariate(shape, scale * 3600.0)
        suffix = f"g{generation}" if generation else ""
        machines.append(
            _C20Machine(
                f"{ws_type.name}{suffix}.{number}",
                ws_type,
                generation,
                next_failure,
                mttr,
                shape,
                scale,
                area,
            )
        )
    return machines


def _c20_order_book(
    scenario: C20OrderScenario, seed: int, count: int
) -> list[Order]:
    generators = {
        C20OrderScenario.OSC1: generate_osc1_order_book,
        C20OrderScenario.OSC2: generate_osc2_order_book,
        C20OrderScenario.OSC3: generate_osc3_order_book,
    }
    return generators[scenario](seed, count=count)


def _c20_priority(
    task: _C20Task,
    contexts: Sequence[_C20Context],
    now: float,
) -> tuple[float, ...]:
    order = contexts[task.context].order
    if order.appearance_date <= now:
        return (
            0.0,
            0.0 if order.rush_order_flag else 1.0,
            order.due_date,
            task.ready,
            float(order.identifier),
        )
    return (1.0, task.ready, float(order.identifier), 0.0, 0.0)


def run_c20_replication(
    order_scenario: C20OrderScenario | str,
    plant_scenario: C20PlantScenario | str,
    *,
    seed: int = 20,
    order_count: int = 5000,
    transport_time: float | None = None,
) -> C20ReplicationResult:
    """Run one complete C20 scenario replication.

    By default, transport uses :class:`C20ConveyorNetwork`, including the
    official dimensions, speed, part capacity, inner/outer routing, and PSc4
    element failures.  Passing ``transport_time`` explicitly retains a fixed
    point-to-point delay for backwards-compatible reduced experiments; source
    and sink trips are still included.
    """

    selected_orders = C20OrderScenario(order_scenario)
    selected_plant = C20PlantScenario(plant_scenario)
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    if not isinstance(order_count, int) or isinstance(order_count, bool) or order_count <= 0:
        raise ValueError("order_count must be a positive integer")
    if transport_time is not None and (
        not math.isfinite(transport_time) or transport_time < 0.0
    ):
        raise ValueError("transport_time must be non-negative and finite")
    rng = random.Random(seed + 1_000_003)
    orders = _c20_order_book(selected_orders, seed, order_count)
    contexts = [
        _C20Context(
            order,
            get_process_plans(order.product_type)[
                order.identifier % len(get_process_plans(order.product_type))
            ],
        )
        for order in orders
    ]
    machines = _c20_machines(selected_plant, rng)
    queues: dict[tuple[WorkStationType, int], list[_C20Task]] = {
        (kind, area): [] for kind in WorkStationType for area in (1, 2, 3)
    }
    events: list[tuple[float, int, str, int, int]] = []
    sequence = 0
    for context_index, context in enumerate(contexts):
        sequence += 1
        heapq.heappush(
            events,
            (
                context.order.earliest_release_date,
                sequence,
                "release",
                context_index,
                0,
            ),
        )
    completed: list[C20OrderResult] = []
    conveyor = C20ConveyorNetwork(
        seed=seed + 2_000_033,
        failures=selected_plant is C20PlantScenario.PSC4,
    )

    def candidate_areas(operation: Operation, product: str) -> tuple[int, ...]:
        return tuple(
            sorted(
                {
                    machine.area
                    for machine in machines
                    if machine.supports(operation, product)
                }
            )
        )

    def route_distance(source: int, target: int, now: float) -> float:
        if transport_time is not None:
            return transport_time
        path = conveyor._select_path(source, target, now)
        distance = sum(conveyor.elements[name].length for name in path)
        if source != target and source != 0:
            distance += conveyor.elements[f"egress_{source}"].length
        if source != target and target != 0:
            distance += conveyor.elements[f"ingress_{target}"].length
        return distance

    def choose_area(
        operation: Operation,
        product: str,
        source: int,
        now: float,
    ) -> int:
        areas = candidate_areas(operation, product)
        if not areas:
            raise RuntimeError(f"no workstation can perform {operation.value} for {product}")

        def score(area: int) -> tuple[float, float, int]:
            eligible = sum(
                machine.area == area and machine.supports(operation, product)
                for machine in machines
            )
            queued = len(queues[(get_operation_ws(operation), area)])
            return (queued / eligible, route_distance(source, area, now), area)

        return min(areas, key=score)

    def transport_arrival(now: float, source: int, target: int) -> float:
        if transport_time is not None:
            return now + transport_time
        return conveyor.transport(now, source, target).arrival

    def schedule_ready(
        context_index: int,
        operation: Operation,
        now: float,
        source: int,
        *,
        not_before: float | None = None,
    ) -> None:
        nonlocal sequence
        context = contexts[context_index]
        target = choose_area(operation, context.order.product_type, source, now)
        arrival = transport_arrival(now, source, target)
        if not_before is not None:
            arrival = max(arrival, not_before)
        sequence += 1
        heapq.heappush(
            events,
            (arrival, sequence, "ready", context_index, target),
        )

    def restart_from_source(context_index: int, now: float, source: int) -> None:
        """Discharge an NOK part and introduce its replacement at area 0."""

        context = contexts[context_index]
        at_sink = transport_arrival(now, source, 0)
        context.area = 0
        schedule_ready(context_index, context.plan[0], at_sink, 0)

    def dispatch(now: float) -> None:
        nonlocal sequence
        made_progress = True
        while made_progress:
            made_progress = False
            for machine_index, machine in enumerate(machines):
                if machine.busy:
                    continue
                queue = queues[(machine.ws_type, machine.area)]
                candidates = [
                    (index, task)
                    for index, task in enumerate(queue)
                    if task.ready <= now
                    and machine.supports(
                        task.operation, contexts[task.context].order.product_type
                    )
                ]
                if not candidates:
                    continue
                queue_index, task = min(
                    candidates,
                    key=lambda item: _c20_priority(item[1], contexts, now),
                )
                queue.pop(queue_index)
                context = contexts[task.context]
                order = context.order
                duration = machine.processing_time(task.operation, order.product_type)
                setup = 0.0
                if machine.ws_type is WorkStationType.III:
                    if machine.tool_usage + duration > 2500.0:
                        setup += 120.0
                        machine.tool_usage = 0.0
                    machine.tool_usage += duration
                if (
                    machine.ws_type is WorkStationType.V
                    and machine.last_operation is not None
                    and machine.last_operation is not task.operation
                ):
                    setup += 300.0
                machine.last_operation = task.operation
                setup_finish, _ = machine.complete(
                    now,
                    setup,
                    rng,
                    damage_on_failure=False,
                )
                event_kind: str | None = None
                if context.previous_completion is not None:
                    delay = setup_finish - context.previous_completion
                    previous = context.plan[context.index - 1]
                    if (
                        order.product_type == "C"
                        and previous is Operation.O4
                        and task.operation is Operation.O3
                        and delay > 360.0
                    ):
                        event_kind = "expired_nok"
                    elif (
                        order.product_type == "E"
                        and previous is Operation.O6
                        and task.operation is Operation.O5
                        and delay > 300.0
                    ):
                        event_kind = "expired_ok"
                if event_kind is not None:
                    finish = setup_finish
                    damaged = False
                else:
                    finish, damaged = machine.complete(
                        setup_finish,
                        duration,
                        rng,
                    )
                machine.busy = True
                sequence += 1
                if event_kind is None:
                    event_kind = "damaged" if damaged else "done"
                heapq.heappush(
                    events,
                    (finish, sequence, event_kind, task.context, machine_index),
                )
                made_progress = True

    while events:
        now = events[0][0]
        batch = []
        while events and events[0][0] == now:
            batch.append(heapq.heappop(events))
        for _time, _seq, kind, context_index, value in batch:
            context = contexts[context_index]
            if kind == "release":
                schedule_ready(
                    context_index,
                    context.plan[context.index],
                    now,
                    0,
                )
            elif kind == "ready":
                operation = context.plan[context.index]
                context.area = value
                queues[(get_operation_ws(operation), value)].append(
                    _C20Task(context_index, operation, now, value)
                )
            elif kind == "sink":
                order = context.order
                tardiness = max(0.0, now - order.due_date)
                completed.append(
                    C20OrderResult(
                        order.identifier,
                        order.product_type,
                        order.earliest_release_date,
                        now,
                        order.due_date,
                        now - order.earliest_release_date,
                        tardiness,
                        C20_PRODUCT_WEIGHTS[order.product_type] * tardiness,
                        context.max_nok,
                        context.max_ok,
                        context.disruption_nok,
                    )
                )
            else:
                machine = machines[value]
                machine.busy = False
                context.area = machine.area
                if kind == "damaged":
                    context.disruption_nok += 1
                    context.index = 0
                    context.previous_completion = None
                    restart_from_source(context_index, now, machine.area)
                    continue
                if kind == "expired_nok":
                    context.max_nok += 1
                    context.index = 0
                    context.previous_completion = None
                    restart_from_source(context_index, now, machine.area)
                    continue
                if kind == "expired_ok":
                    context.max_ok += 1
                    context.index -= 1
                    context.previous_completion = None
                    repeated = context.plan[context.index]
                    schedule_ready(
                        context_index,
                        repeated,
                        now,
                        machine.area,
                    )
                    continue
                context.previous_completion = now
                context.index += 1
                if context.index >= len(context.plan):
                    sequence += 1
                    sink_arrival = transport_arrival(now, machine.area, 0)
                    heapq.heappush(
                        events,
                        (sink_arrival, sequence, "sink", context_index, 0),
                    )
                else:
                    previous = context.plan[context.index - 1]
                    current = context.plan[context.index]
                    not_before = None
                    if (
                        context.order.product_type in {"D", "E"}
                        and previous is Operation.O5
                        and current is Operation.O3
                    ):
                        not_before = now + 600.0
                    schedule_ready(
                        context_index,
                        current,
                        now,
                        machine.area,
                        not_before=not_before,
                    )
        dispatch(now)

    if len(completed) != order_count:
        raise RuntimeError(
            f"C20 deadlocked with {len(completed)}/{order_count} completed orders"
        )
    completed.sort(key=lambda value: value.identifier)
    first_release = min(order.earliest_release_date for order in orders)
    last_completion = max(result.completion_date for result in completed)
    makespan = last_completion - first_release
    return C20ReplicationResult(
        selected_orders,
        selected_plant,
        seed,
        makespan,
        float(statistics.median(result.throughput_time for result in completed)),
        sum(result.tardiness > 0.0 for result in completed),
        sum(result.weighted_tardiness for result in completed),
        sum(result.max_nok_violations for result in completed),
        sum(result.max_ok_violations for result in completed),
        len(completed),
        tuple(completed),
        conveyor.distance if transport_time is None else 0.0,
        sum(failure.start <= last_completion for failure in conveyor.failures),
        conveyor.capacity_delay if transport_time is None else 0.0,
        conveyor.failure_delay if transport_time is None else 0.0,
    )


def _c20_statistic(values: Sequence[float]) -> C20Statistic:
    ordered = sorted(float(value) for value in values)

    def percentile(fraction: float) -> float:
        position = fraction * (len(ordered) - 1)
        lower = int(math.floor(position))
        upper = int(math.ceil(position))
        if lower == upper:
            return ordered[lower]
        return ordered[lower] + (position - lower) * (ordered[upper] - ordered[lower])

    return C20Statistic(percentile(0.5), percentile(0.25), percentile(0.75))


def run_c20_experiment(
    *,
    replications: int = 10,
    order_count: int = 5000,
    seed: int = 20,
) -> tuple[C20ScenarioSummary, ...]:
    """Run all 3 x 4 scenarios and report Task A--D median/IQR values."""

    if not isinstance(replications, int) or isinstance(replications, bool) or replications < 10:
        raise ValueError("the official experiment requires at least 10 replications")
    summaries = []
    for order_scenario in C20OrderScenario:
        for plant_scenario in C20PlantScenario:
            runs = tuple(
                run_c20_replication(
                    order_scenario,
                    plant_scenario,
                    seed=seed + index,
                    order_count=order_count,
                )
                for index in range(replications)
            )
            summaries.append(
                C20ScenarioSummary(
                    order_scenario,
                    plant_scenario,
                    replications,
                    _c20_statistic(tuple(run.makespan for run in runs)),
                    _c20_statistic(tuple(run.median_throughput_time for run in runs)),
                    _c20_statistic(tuple(float(run.tardy_orders) for run in runs)),
                    _c20_statistic(tuple(run.weighted_tardiness for run in runs)),
                    _c20_statistic(tuple(float(run.max_nok_parts) for run in runs)),
                    _c20_statistic(tuple(float(run.max_ok_parts) for run in runs)),
                )
            )
    return tuple(summaries)
