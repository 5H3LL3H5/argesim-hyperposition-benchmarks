"""ARGESIM C22: Non-standard Queuing Policies.

Implements four variants of a queuing system (Basic, Jockeying, Reneging, Classing)
using formal NSA-DEVS modeling and execution algorithms.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from nsa_devs.hypertime import HyperTime


class AtomicModel:
    """Base class for a formal DEVS Atomic model."""

    def __init__(self, name: str):
        self.name = name
        self.sigma: HyperTime = HyperTime(Fraction(0))
        self.phase: str = "active"

    def time_advance(self) -> HyperTime:
        """Return the time remaining before the next internal transition."""
        return self.sigma

    def internal_transition(self) -> None:
        """Handle internal state changes."""
        pass

    def external_transition(self, e: HyperTime, payload: Any) -> None:
        """Handle external inputs."""
        pass

    def output_function(self) -> Any:
        """Generate output."""
        return None


@dataclass(order=True)
class EventMsg:
    time: HyperTime
    priority: int
    sequence: int
    model: AtomicModel = field(compare=False)
    payload: Any = field(default=None, compare=False)


class DevsSimulator:
    """Formal DEVS Execution Algorithm."""

    def __init__(self, model: AtomicModel):
        self.model = model
        self.time = HyperTime(Fraction(0))
        self._sequence = 0
        self.events: list[EventMsg] = []

        # Schedule the first internal transition
        self.schedule_internal(model)

    def schedule_internal(self, model: AtomicModel) -> None:
        ta = model.time_advance()
        if ta is not None:
            self._sequence += 1
            target = self.time
            if ta.macro > 0:
                target = target.after_finite(ta.macro)
            if ta.micro > 0:
                target = target.after_epsilon(ta.micro)

            heapq.heappush(self.events, EventMsg(target, 0, self._sequence, model))

    def run(self) -> None:
        while self.events:
            event = heapq.heappop(self.events)
            self.time = event.time

            # Since this is a standalone Atomic model simulation acting as a system,
            # we just process internal transitions. External transitions will be routed
            # through specific internal handlers.

            # Output and internal transition
            _ = event.model.output_function()
            event.model.internal_transition()

            # Note: in a true coupled DEVS, 'out' would be routed to other models via external transitions
            # Here we just reschedule based on the new ta
            self.schedule_internal(event.model)


@dataclass
class Entity:
    id: int
    creation_time: float
    enter_queue_time: float = 0.0
    queue_wait_time: float = 0.0
    reneged: bool = False
    entity_class: int = 0
    assigned_queue: int = -1


class BaseDevsSystem(AtomicModel):
    def __init__(
        self,
        name: str,
        stochastic: bool = False,
        large: bool = False,
        variant: bool = False,
        rng: random.Random | None = None,
    ):
        super().__init__(name)
        self.stochastic = stochastic
        self.large = large
        self.variant = variant
        self.rng = rng or random.Random()
        # C22 Specification Parameters
        self.num_queues = 40 if large else 4
        self.num_entities = 5000 if large else (500 if stochastic else 100)

        self.interarrival_time = 0.1 if large else 1.0
        self.service_time_mode = 4.5
        self.service_time_hw = 2.0

        self.queues: list[list[Entity]] = [[] for _ in range(self.num_queues)]
        self.servers: list[Entity | None] = [None for _ in range(self.num_queues)]

        self.entities_created = 0
        self.entities_terminated = 0

        self.terminated_ids: list[int] = []
        self.termination_times: list[float] = []
        self.lqt_max = 0
        self.lqt_integral = 0.0
        self.last_time = 0.0
        self.wait_times: list[float] = []

        # State encoding for DEVS phase:
        # "wait_arrive", "wait_leave", "process_internal", "done"

        # Because DEVS Atomic only has ONE time advance, we use a custom event list internally
        # to manage concurrent events, and time_advance just returns the difference to the next internal event.
        # This encapsulates the system as a monolithic DEVS Atomic model.

        self._internal_events: list[tuple[HyperTime, int, int, str, Any]] = []
        self._internal_seq = 0
        self.current_time = HyperTime(Fraction(0))

        self.schedule_event(0.0, 5 if not variant else 0, "arrive", None)
        self.update_sigma()

    def schedule_event(
        self, delay: float, priority: int, event_type: str, payload: Any = None
    ) -> None:
        self._internal_seq += 1
        # NSA-DEVS encoding: finite delay + epsilon priority
        if delay > 0:
            target_time = self.current_time.after_finite(delay)
            if priority > 0:
                target_time = target_time.after_epsilon(priority)
        else:
            target_time = self.current_time
            if priority > 0:
                target_time = target_time.after_epsilon(priority)

        heapq.heappush(
            self._internal_events,
            (target_time, priority, self._internal_seq, event_type, payload),
        )

    def schedule_eps_event(
        self, priority: int, event_type: str, payload: Any = None
    ) -> None:
        self._internal_seq += 1
        target_time = self.current_time
        if priority > 0:
            target_time = target_time.after_epsilon(priority)
        heapq.heappush(
            self._internal_events,
            (target_time, priority, self._internal_seq, event_type, payload),
        )

    def update_sigma(self) -> None:
        if not self._internal_events or self.entities_terminated >= self.num_entities:
            self.sigma = None
            self.phase = "done"
        else:
            next_time = self._internal_events[0][0]
            macro_diff = next_time.macro - self.current_time.macro
            micro_diff = next_time.micro - self.current_time.micro
            if macro_diff < 0 or (macro_diff == 0 and micro_diff < 0):
                self.sigma = HyperTime(Fraction(0))  # catch up
            else:
                self.sigma = HyperTime(
                    macro_diff, micro_diff if macro_diff == 0 else next_time.micro
                )

    def time_advance(self) -> HyperTime:
        return self.sigma

    def internal_transition(self) -> None:
        if not self._internal_events:
            return

        # Advance current time to next event
        event = heapq.heappop(self._internal_events)
        target_time, priority, seq, event_type, payload = event
        self.current_time = target_time

        self.update_stats()

        if event_type == "arrive":
            self.handle_arrive()
        elif event_type == "leave":
            self.handle_leave(payload)
        elif event_type == "enter":
            self.handle_enter(payload)
        elif event_type == "jockey":
            self.handle_jockey()
        elif event_type == "renege":
            self.handle_renege(payload)
        elif event_type == "operator":
            self.handle_operator()

        self.update_sigma()

    def update_stats(self) -> None:
        current_macro = float(self.current_time.macro)
        dt = current_macro - self.last_time
        if dt > 0:
            lqt = sum(len(q) for q in self.queues)
            self.lqt_integral += lqt * dt
            if lqt > self.lqt_max:
                self.lqt_max = lqt
            self.last_time = current_macro

    def get_service_time(self) -> float:
        if not self.stochastic:
            return self.service_time_mode
        else:
            return self.rng.triangular(
                self.service_time_mode - self.service_time_hw,
                self.service_time_mode + self.service_time_hw,
                self.service_time_mode,
            )

    def get_interarrival_time(self) -> float:
        if not self.stochastic:
            return self.interarrival_time
        else:
            return self.rng.expovariate(1.0 / self.interarrival_time)

    def total_length(self, i: int) -> int:
        return len(self.queues[i]) + (1 if self.servers[i] is not None else 0)

    def choose_queue(self) -> int:
        min_len = min(self.total_length(i) for i in range(self.num_queues))
        for i in range(self.num_queues):
            if self.total_length(i) == min_len:
                return i
        return 0

    def handle_arrive(self) -> None:
        if self.entities_created >= self.num_entities:
            return

        self.entities_created += 1
        entity = Entity(
            id=self.entities_created, creation_time=float(self.current_time.macro)
        )
        self.process_entity_arrival(entity)

        if self.entities_created < self.num_entities:
            self.schedule_event(
                self.get_interarrival_time(), 5 if not self.variant else 0, "arrive"
            )

    def process_entity_arrival(self, entity: Entity) -> None:
        q_idx = self.choose_queue()
        entity.assigned_queue = q_idx
        entity.enter_queue_time = float(self.current_time.macro)
        self.queues[q_idx].append(entity)
        self.check_enter_server(q_idx)

    def check_enter_server(self, q_idx: int) -> None:
        if self.servers[q_idx] is None and self.queues[q_idx]:
            self.schedule_eps_event(2, "enter", q_idx)

    def handle_enter(self, q_idx: int) -> None:
        if self.servers[q_idx] is None and self.queues[q_idx]:
            entity = self.queues[q_idx].pop(0)
            self.servers[q_idx] = entity
            entity.queue_wait_time += (
                float(self.current_time.macro) - entity.enter_queue_time
            )
            self.wait_times.append(entity.queue_wait_time)

            self.schedule_event(self.get_service_time(), 1, "leave", q_idx)
            self.post_enter_server(q_idx, entity)

    def handle_leave(self, q_idx: int) -> None:
        entity = self.servers[q_idx]
        self.servers[q_idx] = None
        if entity is not None:
            self.terminated_ids.append(entity.id)
            self.termination_times.append(float(self.current_time.macro))
            self.entities_terminated += 1
        self.check_enter_server(q_idx)
        self.post_leave_server(q_idx)

    def post_enter_server(self, q_idx: int, entity: Entity) -> None:
        pass

    def post_leave_server(self, q_idx: int) -> None:
        pass

    def handle_jockey(self) -> None:
        pass

    def handle_renege(self, entity: Entity) -> None:
        pass

    def handle_operator(self) -> None:
        """Process operator call for the next class.

        As per the ARGESIM C22 specification, the operator calls classes in
        descending round-robin order starting with the highest class (nC = 5),
        which then proceeds to the front of their respective queues.
        """
        pass


class JockeyingSystem(BaseDevsSystem):
    def __init__(
        self,
        name: str,
        stochastic: bool = False,
        large: bool = False,
        variant: bool = False,
        rng: random.Random | None = None,
    ):
        super().__init__(name, stochastic, large, variant)
        self.jockey_events = 0
        self.jockey_records: list[tuple[float, int, int, int]] = []

    def post_leave_server(self, q_idx: int) -> None:
        self.schedule_eps_event(4, "jockey")

    def post_enter_server(self, q_idx: int, entity: Entity) -> None:
        self.schedule_eps_event(4, "jockey")

    def handle_jockey(self) -> None:
        while True:
            lengths = [self.total_length(i) for i in range(self.num_queues)]
            min_len = min(lengths)

            dest_cands = [i for i in range(self.num_queues) if lengths[i] == min_len]
            if not dest_cands:
                break
            dest_q = dest_cands[0]

            src_cands = [
                i
                for i in range(self.num_queues)
                if lengths[i] >= min_len + 2 and self.queues[i]
            ]
            if not src_cands:
                break

            nearest_dist = min(abs(i - dest_q) for i in src_cands)
            nearest_srcs = [i for i in src_cands if abs(i - dest_q) == nearest_dist]
            src_q = nearest_srcs[0]

            entity = self.queues[src_q].pop(-1)

            entity.queue_wait_time += (
                float(self.current_time.macro) - entity.enter_queue_time
            )
            entity.enter_queue_time = float(self.current_time.macro)
            entity.assigned_queue = dest_q

            self.queues[dest_q].append(entity)
            self.jockey_events += 1
            if not self.stochastic:
                self.jockey_records.append(
                    (float(self.current_time.macro), entity.id, src_q + 1, dest_q + 1)
                )

            self.check_enter_server(dest_q)


class RenegingSystem(BaseDevsSystem):
    def __init__(
        self,
        name: str,
        stochastic: bool = False,
        large: bool = False,
        variant: bool = False,
        rng: random.Random | None = None,
    ):
        super().__init__(name, stochastic, large, variant)
        self.t_r = 9.0
        self.renege_events = 0
        self.renege_records: list[tuple[float, int]] = []

    def process_entity_arrival(self, entity: Entity) -> None:
        super().process_entity_arrival(entity)
        self.schedule_event(self.t_r, 3, "renege", entity)

    def handle_renege(self, entity: Entity) -> None:
        if entity.assigned_queue != -1 and entity in self.queues[entity.assigned_queue]:
            self.queues[entity.assigned_queue].remove(entity)
            entity.reneged = True
            entity.queue_wait_time = self.t_r
            self.wait_times.append(entity.queue_wait_time)

            self.renege_events += 1
            if not self.stochastic:
                self.renege_records.append((float(self.current_time.macro), entity.id))

            self.entities_terminated += 1


class ClassingSystem(BaseDevsSystem):
    def __init__(
        self,
        name: str,
        stochastic: bool = False,
        large: bool = False,
        variant: bool = False,
        rng: random.Random | None = None,
    ):
        super().__init__(name, stochastic, large, variant)
        self.n_c = 5
        self.t_c = 10.0
        self.current_class = 0
        self.det_class_counter = 1

        self.schedule_event(self.t_c, 6, "operator")
        self.class_wait_times: dict[int, list[float]] = {
            i: [] for i in range(1, self.n_c + 1)
        }

    def handle_arrive(self) -> None:
        if self.entities_created >= self.num_entities:
            return

        self.entities_created += 1

        if self.stochastic:
            c = self.rng.randint(1, self.n_c)
        else:
            c = self.det_class_counter
            self.det_class_counter = (self.det_class_counter % self.n_c) + 1

        entity = Entity(
            id=self.entities_created,
            creation_time=float(self.current_time.macro),
            entity_class=c,
        )
        self.process_entity_arrival(entity)

        if (
            self.current_class == 0
            and sum(self.total_length(i) for i in range(self.num_queues)) > 0
        ):
            self.schedule_eps_event(6, "operator")

        if self.entities_created < self.num_entities:
            self.schedule_event(
                self.get_interarrival_time(), 5 if not self.variant else 0, "arrive"
            )

    def handle_operator(self) -> None:
        """Process operator call for the next class.

        As per the ARGESIM C22 specification, the operator calls classes in
        descending round-robin order starting with the highest class (nC = 5),
        which then proceeds to the front of their respective queues.
        """
        if self.entities_terminated >= self.num_entities:
            return

        total_in_system = sum(self.total_length(i) for i in range(self.num_queues))
        if total_in_system == 0:
            self.current_class = 0
            return

        if self.current_class == 0:
            self.current_class = self.n_c
        else:
            self.current_class -= 1
            if self.current_class == 0:
                self.current_class = self.n_c

        self.reorder_queues()

        for i in range(self.num_queues):
            self.check_enter_server(i)

        self.check_operator_wait()

    def reorder_queues(self) -> None:
        for q in self.queues:
            if not q:
                continue
            called = [e for e in q if e.entity_class == self.current_class]
            others = [e for e in q if e.entity_class != self.current_class]
            q[:] = called + others

    def check_enter_server(self, q_idx: int) -> None:
        if self.servers[q_idx] is None and self.queues[q_idx]:
            if self.queues[q_idx][0].entity_class == self.current_class:
                self.schedule_eps_event(2, "enter", q_idx)

    def handle_enter(self, q_idx: int) -> None:
        if (
            self.servers[q_idx] is None
            and self.queues[q_idx]
            and self.queues[q_idx][0].entity_class == self.current_class
        ):
            entity = self.queues[q_idx].pop(0)
            self.servers[q_idx] = entity
            entity.queue_wait_time += (
                float(self.current_time.macro) - entity.enter_queue_time
            )
            self.wait_times.append(entity.queue_wait_time)
            self.class_wait_times[entity.entity_class].append(entity.queue_wait_time)
            self.schedule_event(self.get_service_time(), 1, "leave", q_idx)

    def post_leave_server(self, q_idx: int) -> None:
        self.check_operator_wait()

    def check_operator_wait(self) -> None:
        if self.current_class != 0:
            count = 0
            for i in range(self.num_queues):
                if (
                    self.servers[i] is not None
                    and self.servers[i].entity_class == self.current_class
                ):
                    count += 1
                count += sum(
                    1 for e in self.queues[i] if e.entity_class == self.current_class
                )

            if count == 0:
                self.schedule_eps_event(6, "operator")


def run_model(
    system_cls: type[BaseDevsSystem],
    stochastic: bool,
    large: bool,
    variant: bool = False,
    seed: int = 42,
) -> dict[str, Any]:
    # Use an isolated random instance to avoid polluting global state
    rng = random.Random(seed)

    system = system_cls("C22_Model", stochastic, large, variant, rng)
    sim = DevsSimulator(system)

    sim.run()

    avg_lqt = system.lqt_integral / float(sim.time.macro) if sim.time.macro > 0 else 0.0
    avg_wait = (
        sum(system.wait_times) / len(system.wait_times) if system.wait_times else 0.0
    )
    max_wait = max(system.wait_times) if system.wait_times else 0.0

    res = {
        "lqt_max": system.lqt_max,
        "lqt_avg": avg_lqt,
        "tq_max": max_wait,
        "tq_avg": avg_wait,
    }

    if not stochastic:
        res["ids_out"] = system.terminated_ids[-20:]
        res["times_out"] = system.termination_times[-20:]

    if isinstance(system, JockeyingSystem):
        res["jockey_events"] = system.jockey_events
        if not stochastic:
            if len(system.jockey_records) > 10:
                res["jockey_table"] = (
                    system.jockey_records[:5] + system.jockey_records[-5:]
                )
            else:
                res["jockey_table"] = system.jockey_records

    if isinstance(system, RenegingSystem):
        res["renege_events"] = system.renege_events
        if not stochastic:
            res["renege_table"] = system.renege_records

    if isinstance(system, ClassingSystem):
        class_stats = {}
        for c in range(1, system.n_c + 1):
            c_times = system.class_wait_times[c]
            if c_times:
                class_stats[c] = {
                    "max": max(c_times),
                    "avg": sum(c_times) / len(c_times),
                }
            else:
                class_stats[c] = {"max": 0.0, "avg": 0.0}
        res["class_stats"] = class_stats

    return res


def c22_basic() -> dict[str, dict[str, Any]]:
    return {
        "deterministic": run_model(BaseDevsSystem, False, False),
        "deterministic_variant": run_model(BaseDevsSystem, False, False, variant=True),
        "stochastic": run_model(BaseDevsSystem, True, False),
        "stochastic_large": run_model(BaseDevsSystem, True, True),
    }


def c22_jockeying() -> dict[str, dict[str, Any]]:
    return {
        "deterministic": run_model(JockeyingSystem, False, False),
        "stochastic": run_model(JockeyingSystem, True, False),
    }


def c22_reneging() -> dict[str, dict[str, Any]]:
    return {
        "deterministic": run_model(RenegingSystem, False, False),
        "stochastic": run_model(RenegingSystem, True, False),
    }


def c22_classing() -> dict[str, dict[str, Any]]:
    return {
        "deterministic": run_model(ClassingSystem, False, False),
        "stochastic": run_model(ClassingSystem, True, False),
    }
