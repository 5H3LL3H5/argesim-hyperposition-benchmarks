"""C20 production controller coupled to the causal, dimensioned transport model.

The controller is an explicit benchmark choice: release up to 30 simultaneous
parts, dispatch by rush flag/due date, choose the nearest idle eligible machine,
and store waiting parts in the nearest accessible FIFO buffer. Machine
locations, processing parameters and pre-process constraints are prescribed by
the definition, not chosen by the controller.
"""

from __future__ import annotations

import heapq
import random
import statistics
from dataclasses import dataclass

from .c20_complex_production import (
    C20_PRODUCT_WEIGHTS,
    C20OrderResult,
    C20OrderScenario,
    C20PlantScenario,
    C20ReplicationResult,
    Operation,
    Order,
    WorkStationType,
    _c20_machines,
    _c20_order_book,
    get_process_plans,
)
from .c20_flow import C20Flow, C20FlowTrip

# Table 1: area.slot, including the nonconsecutive positions of type I.
C20_MACHINE_LOCATIONS = {
    "I.1": "a1:ws1",
    "I.2": "a1:ws4",
    "I.3": "a2:ws1",
    "I.4": "a2:ws5",
    "I.5": "a3:ws1",
    "I.6": "a3:ws4",
    "IIg1.1": "a1:ws2",
    "IIg1.2": "a1:ws3",
    "IIg2.3": "a1:ws5",
    "IIg3.4": "a1:ws6",
    "III.1": "a2:ws2",
    "III.2": "a2:ws3",
    "III.3": "a2:ws4",
    "IV.1": "a3:ws2",
    "IV.2": "a3:ws3",
    "V.1": "a2:ws6",
    "V.2": "a2:ws7",
    "V.3": "a3:ws5",
    "V.4": "a3:ws6",
}


@dataclass
class _Job:
    order: Order
    plan: tuple[Operation, ...]
    index: int = 0
    phase: str = "unreleased"
    previous_completion: float | None = None
    not_before: float = 0.0
    machine: int | None = None
    buffer: str | None = None
    max_nok: int = 0
    max_ok: int = 0
    disruption_nok: int = 0


class C20Production:
    """One terminating order book, with physical storage for every active part."""

    def __init__(
        self,
        order_scenario: C20OrderScenario,
        plant_scenario: C20PlantScenario,
        *,
        seed: int,
        order_count: int,
        wip_limit: int = 30,
        trace: bool = False,
    ) -> None:
        order_scenario = C20OrderScenario(order_scenario)
        plant_scenario = C20PlantScenario(plant_scenario)
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise TypeError("seed must be an integer")
        if (
            isinstance(order_count, bool)
            or not isinstance(order_count, int)
            or order_count <= 0
        ):
            raise ValueError("order_count must be a positive integer")
        if (
            isinstance(wip_limit, bool)
            or not isinstance(wip_limit, int)
            or wip_limit <= 0
        ):
            raise ValueError("wip_limit must be a positive integer")
        self.order_scenario, self.plant_scenario, self.seed = (
            order_scenario,
            plant_scenario,
            seed,
        )
        self.wip_limit = wip_limit
        self.flow = C20Flow(
            seed=seed + 2_000_033,
            failures=plant_scenario is C20PlantScenario.PSC4,
            trace=trace,
        )
        self.rng = random.Random(seed + 1_000_003)
        self.machines = _c20_machines(plant_scenario, self.rng)
        self.machine_nodes = [C20_MACHINE_LOCATIONS[m.name] for m in self.machines]
        self.jobs: dict[int, _Job] = {}
        self.active: set[int] = set()
        self.pending: list[tuple[tuple[float, ...], int]] = []
        for order in _c20_order_book(order_scenario, seed, order_count):
            plans = get_process_plans(order.product_type)
            job = _Job(order, plans[order.identifier % len(plans)])
            self.jobs[order.identifier] = job
            self.flow.call_at(
                order.earliest_release_date, lambda job=job: self._release(job)
            )
        self.buffer_owners: dict[str, int] = {}
        self.completed: list[C20OrderResult] = []
        self.operation_trace: list[tuple[float, str, int, str, str]] = []
        self.trace_enabled = trace
        self.maximum_wip = 0
        self.maximum_buffer_reservations = 0
        self._dispatching = False
        self._distance_cache: dict[tuple[str, str], float] = {}
        for name, node in self.flow.layout.nodes.items():
            if node.kind == "workstation" and name not in self.machine_nodes:
                self.flow.set_open(name, False)
        self.flow.on_change = self.dispatch

    def _record(self, kind: str, job: _Job, operation: Operation, machine: int) -> None:
        if self.trace_enabled:
            self.operation_trace.append(
                (
                    self.flow.now,
                    kind,
                    job.order.identifier,
                    operation.value,
                    self.machine_nodes[machine],
                )
            )

    def _priority(self, job: _Job) -> tuple[float, ...]:
        # Only released orders are admitted; their appearance date is already
        # reached in every OSc. Future orders are never used for dispatch.
        rush = (
            self.order_scenario is not C20OrderScenario.OSC1
            and job.order.rush_order_flag
        )
        return (
            0.0 if rush else 1.0,
            job.order.due_date,
            job.order.earliest_release_date,
            float(job.order.identifier),
        )

    def _release(self, job: _Job) -> None:
        job.phase = "pending"
        heapq.heappush(self.pending, (self._priority(job), job.order.identifier))
        self.dispatch()

    def _distance(self, source: str, target: str) -> float:
        key = source, target
        if key not in self._distance_cache:
            path = self.flow.layout.shortest_path(source, target)
            self._distance_cache[key] = sum(
                self.flow.layout.tracks[name].length for name in path
            )
        return self._distance_cache[key]

    def _source(self, job: _Job) -> str:
        node = self.flow.parts[job.order.identifier].node
        if node is None:
            raise RuntimeError("dispatch attempted while a part was on a conveyor")
        return node

    def _front_of_buffer(self, job: _Job) -> bool:
        if job.buffer is None:
            return True
        node = self.flow.layout.nodes[job.buffer]
        # A rear part cannot reserve a machine ahead of a front part which must
        # pass through the same column. Reservations include approaching parts.
        return not any(
            owner != job.order.identifier
            and self.flow.layout.nodes[name].area == node.area
            and self.flow.layout.nodes[name].slot == node.slot
            and self.flow.layout.nodes[name].level < node.level
            for name, owner in self.buffer_owners.items()
        )

    def _leave(self, job: _Job, target: str, callback) -> None:
        source_machine = job.machine
        source_buffer = job.buffer
        job.machine = None
        job.phase = "travelling"

        def departed() -> None:
            if source_machine is not None:
                self.machines[source_machine].busy = False
            self.dispatch()

        def arrived(trip: C20FlowTrip) -> None:
            # Hold a buffer reservation until its owner has left the column;
            # retaining it through the journey is a conservative control choice.
            if source_buffer is not None:
                del self.buffer_owners[source_buffer]
                if job.buffer == source_buffer:
                    job.buffer = None
            callback(trip)
            self.dispatch()

        self.flow.send(job.order.identifier, target, arrived, on_departure=departed)

    def _buffer(self, job: _Job) -> bool:
        if job.buffer is not None:
            return False
        source = self._source(job)
        choices = []
        for area in (1, 2, 3):
            for column in range(1, 11):
                # A later arrival must not occupy a rear slot in front of an
                # earlier reservation which is still approaching the column.
                owners = [
                    owner
                    for name, owner in self.buffer_owners.items()
                    if self.flow.layout.nodes[name].area == area
                    and self.flow.layout.nodes[name].slot == column
                ]
                if any(self.jobs[owner].phase != "waiting" for owner in owners):
                    continue
                # Enter through level 3, filling the downstream end first.
                for level in (1, 2, 3):
                    name = f"a{area}:buffer{column}.{level}"
                    approach = (f"a{area}:buffer{column}.{z}" for z in range(level, 4))
                    if all(slot not in self.buffer_owners for slot in approach):
                        choices.append((self._distance(source, name), name))
                        break
        if not choices:
            return False
        _, target = min(choices)
        self.buffer_owners[target] = job.order.identifier
        self.maximum_buffer_reservations = max(
            self.maximum_buffer_reservations, len(self.buffer_owners)
        )

        def arrived(_trip: C20FlowTrip) -> None:
            job.phase, job.buffer = "waiting", target

        self._leave(job, target, arrived)
        # Destination reservation is stored separately from the source buffer.
        job.buffer = target
        return True

    def _to_machine(self, job: _Job, index: int) -> None:
        machine, target = self.machines[index], self.machine_nodes[index]
        operation = job.plan[job.index]
        duration = machine.processing_time(operation, job.order.product_type)
        setup = 0.0
        if (
            machine.ws_type is WorkStationType.III
            and machine.tool_usage + duration > 2500.0
        ):
            setup = 120.0
            machine.tool_usage = 0.0
        if (
            machine.ws_type is WorkStationType.V
            and machine.last_operation is not None
            and machine.last_operation is not operation
        ):
            setup = 300.0
        machine.busy = True
        self.flow.set_open(target, False)
        finish, _ = machine.complete(
            self.flow.now, setup, self.rng, damage_on_failure=False
        )

        def setup_done() -> None:
            machine.last_operation = operation
            self.flow.set_open(target, True)

        self.flow.call_at(finish, setup_done)

        def arrived(_trip: C20FlowTrip) -> None:
            job.machine, job.phase = index, "processing"
            # An idle failure during transit may postpone the actual start.
            start, _ = machine.complete(
                self.flow.now, 0.0, self.rng, damage_on_failure=False
            )
            self.flow.call_at(
                start, lambda: self._start(job, index, operation, duration)
            )

        self._leave(job, target, arrived)

    def _start(
        self, job: _Job, index: int, operation: Operation, duration: float
    ) -> None:
        machine = self.machines[index]
        now = self.flow.now
        if now < job.not_before:
            raise RuntimeError("C20 MIN constraint violated by dispatch")
        delay = (
            0.0 if job.previous_completion is None else now - job.previous_completion
        )
        previous = None if job.index == 0 else job.plan[job.index - 1]
        if (
            job.order.product_type == "C"
            and previous is Operation.O4
            and operation is Operation.O3
            and delay > 360.0
        ):
            job.max_nok += 1
            job.phase = "scrap"
            self._record("max_nok", job, operation, index)
            self.dispatch()
            return
        if (
            job.order.product_type == "E"
            and previous is Operation.O6
            and operation is Operation.O5
            and delay > 300.0
        ):
            job.max_ok += 1
            job.index -= 1
            job.previous_completion = None
            job.phase = "waiting"
            self._record("max_ok", job, operation, index)
            self.dispatch()
            return
        self._record("start", job, operation, index)
        finish, damaged = machine.complete(now, duration, self.rng)
        # In type III a disrupted attempt also consumes tool life, but only
        # until the disruption (repair time does not wear the tool).
        if machine.ws_type is WorkStationType.III:
            machine.tool_usage += (
                max(0.0, finish - now - machine.mttr) if damaged else duration
            )

        def completed() -> None:
            if damaged:
                job.disruption_nok += 1
                job.phase = "scrap"
                self._record("damaged", job, operation, index)
            else:
                self._record("finish", job, operation, index)
                job.previous_completion = self.flow.now
                job.index += 1
                job.phase = "finished" if job.index == len(job.plan) else "waiting"
                job.not_before = self.flow.now
                if (
                    job.index < len(job.plan)
                    and operation is Operation.O5
                    and job.plan[job.index] is Operation.O3
                ):
                    job.not_before += 600.0
                    self.flow.call_at(job.not_before, self.dispatch)
            self.dispatch()

        self.flow.call_at(finish, completed)

    def _sink(self, job: _Job, *, scrap: bool) -> None:
        def arrived(_trip: C20FlowTrip) -> None:
            self.flow.remove(job.order.identifier)
            self.active.remove(job.order.identifier)
            if scrap:
                job.index, job.previous_completion, job.not_before = 0, None, 0.0
                job.phase = "pending"
                heapq.heappush(
                    self.pending, (self._priority(job), job.order.identifier)
                )
            else:
                order, now = job.order, self.flow.now
                tardiness = max(0.0, now - order.due_date)
                self.completed.append(
                    C20OrderResult(
                        order.identifier,
                        order.product_type,
                        order.earliest_release_date,
                        now,
                        order.due_date,
                        now - order.earliest_release_date,
                        tardiness,
                        C20_PRODUCT_WEIGHTS[order.product_type] * tardiness,
                        job.max_nok,
                        job.max_ok,
                        job.disruption_nok,
                    )
                )
                job.phase = "complete"

        self._leave(job, "a0:in", arrived)

    def dispatch(self) -> None:
        if self._dispatching:
            return
        self._dispatching = True
        try:
            candidates = sorted(
                (
                    self.jobs[identifier]
                    for identifier in self.active
                    if self.jobs[identifier].phase in {"waiting", "finished", "scrap"}
                ),
                key=self._priority,
            )
            for job in candidates:
                if not self._front_of_buffer(job):
                    continue
                if job.phase in {"finished", "scrap"}:
                    self._sink(job, scrap=job.phase == "scrap")
                    continue
                eligible = [
                    index
                    for index, machine in enumerate(self.machines)
                    if not machine.busy
                    and machine.supports(job.plan[job.index], job.order.product_type)
                ]
                if self.flow.now >= job.not_before and eligible:
                    source = self._source(job)
                    chosen = min(
                        eligible,
                        key=lambda index: (
                            self._distance(source, self.machine_nodes[index]),
                            index,
                        ),
                    )
                    self._to_machine(job, chosen)
                elif job.buffer is None:
                    self._buffer(job)
            if len(self.flow.parts) < self.wip_limit and self.pending:
                job = self.jobs[self.pending[0][1]]
                if self.flow.insert(job.order.identifier, "a0:out"):
                    heapq.heappop(self.pending)
                    self.active.add(job.order.identifier)
                    job.phase = "waiting"
                    self.maximum_wip = max(self.maximum_wip, len(self.flow.parts))
                    self.flow.call_at(self.flow.now, self.dispatch)
        finally:
            self._dispatching = False

    def run(self) -> C20ReplicationResult:
        previous_progress = (self.flow.movement_count, len(self.completed))

        def watchdog() -> None:
            nonlocal previous_progress
            current = (self.flow.movement_count, len(self.completed))
            if current == previous_progress and all(
                job.phase != "unreleased" for job in self.jobs.values()
            ):
                raise RuntimeError(
                    "C20 progress limit: no part movement or completed orders for 24 simulated hours"
                )
            previous_progress = current
            self.flow.call_at(self.flow.now + 86400.0, watchdog)

        # PSc4's autonomous failure calendar must not conceal a stalled plant
        # by producing an endless stream of failure/repair events. This is a
        # declared execution guard, not a claimed proof of physical deadlock.
        self.flow.call_at(self.flow.now + 86400.0, watchdog)
        self.flow.run(done=lambda: len(self.completed) == len(self.jobs))
        self.flow.assert_conservation()
        if len(self.completed) != len(self.jobs):
            raise RuntimeError(
                f"C20 deadlocked with {len(self.completed)}/{len(self.jobs)} completed orders"
            )
        if (
            self.flow.parts
            or self.buffer_owners
            or any(machine.busy for machine in self.machines)
        ):
            raise RuntimeError(
                "C20 completed orders left physical parts or reservations behind"
            )
        ordered = tuple(sorted(self.completed, key=lambda result: result.identifier))
        trips = self.flow.completed_trips
        failure_delay = sum(trip.paused_on_failed_belts for trip in trips)
        total_delay = sum(
            trip.arrived - trip.requested - trip.distance for trip in trips
        )
        return C20ReplicationResult(
            self.order_scenario,
            self.plant_scenario,
            self.seed,
            max(result.completion_date for result in ordered)
            - min(result.release_date for result in ordered),
            float(statistics.median(result.throughput_time for result in ordered)),
            sum(result.tardiness > 0 for result in ordered),
            sum(result.weighted_tardiness for result in ordered),
            sum(result.max_nok_violations for result in ordered),
            sum(result.max_ok_violations for result in ordered),
            len(ordered),
            ordered,
            sum(trip.distance for trip in trips),
            len(self.flow.failures),
            max(0.0, total_delay - failure_delay),
            failure_delay,
            sum(result.tardiness for result in ordered),
        )
