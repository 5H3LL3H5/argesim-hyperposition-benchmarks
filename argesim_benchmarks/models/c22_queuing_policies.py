"""ARGESIM C22: Non-standard Queuing Policies.

Implements four variants of a queuing system (Basic, Jockeying, Reneging, Classing)
using formal NSA-DEVS modeling and execution algorithms.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass
from fractions import Fraction
from typing import Any

from nsa_devs import DesScheduler, HyperTime


class AtomicModel:
    """Base class for a formal DEVS Atomic model."""

    def __init__(self, name: str):
        self.name = name
        self.sigma: HyperTime | None = HyperTime(Fraction(0))
        self.phase: str = "active"

    def time_advance(self) -> HyperTime | None:
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


class DevsSimulator:
    """Single-atomic DEVS adapter using the shared HyperTime scheduler."""

    def __init__(self, model: AtomicModel):
        if not isinstance(model, AtomicModel):
            raise TypeError("model must be AtomicModel")
        self.model = model
        self.scheduler = DesScheduler()

        # Schedule the first internal transition
        self.schedule_internal(model)

    @property
    def time(self) -> HyperTime:
        return self.scheduler.time

    @property
    def events(self):
        return self.scheduler.events

    def schedule_internal(self, model: AtomicModel) -> None:
        ta = model.time_advance()
        if ta is not None:
            target = self.time
            if ta.macro > 0:
                target = target.after_finite(ta.macro)
            if ta.micro > 0:
                target = target.after_epsilon(ta.micro)

            self.scheduler.schedule_at(
                target,
                f"{model.name}:internal",
                self._execute_internal,
                model,
            )

    def _execute_internal(self, model: AtomicModel) -> None:
        _ = model.output_function()
        model.internal_transition()
        self.schedule_internal(model)

    def run(self, *, max_events: int = 1_000_000) -> int:
        if not isinstance(max_events, int) or isinstance(max_events, bool):
            raise TypeError("max_events must be an integer")
        if max_events <= 0:
            raise ValueError("max_events must be positive")
        return self.scheduler.run_until_idle(max_events=max_events)


@dataclass
class Entity:
    id: int
    creation_time: float
    enter_queue_time: float = 0.0
    queue_wait_time: float = 0.0
    reneged: bool = False
    entity_class: int = 0
    assigned_queue: int = -1
    in_service: bool = False
    terminated: bool = False


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
        for option_name, option in (
            ("stochastic", stochastic),
            ("large", large),
            ("variant", variant),
        ):
            if not isinstance(option, bool):
                raise TypeError(f"{option_name} must be bool")
        if rng is not None and not isinstance(rng, random.Random):
            raise TypeError("rng must be random.Random")
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
        self.creation_times: list[float] = []

        self.terminated_ids: list[int] = []
        self.termination_times: list[float] = []
        self.lqt_max = 0
        self.lqt_integral = 0.0
        self.last_time = 0.0
        self.wait_times: list[float] = []
        # Duplicate macro times retain the specified order of concurrent
        # transitions, so the deterministic lqt(t) can be plotted as steps.
        self.lqt_trace: list[tuple[float, int]] = [(0.0, 0)]

        # State encoding for DEVS phase:
        # "wait_arrive", "wait_leave", "process_internal", "done"

        # Because DEVS Atomic only has ONE time advance, we use a custom event list internally
        # to manage concurrent events, and time_advance just returns the difference to the next internal event.
        # This encapsulates the system as a monolithic DEVS Atomic model.

        self._internal_events: list[tuple[HyperTime, int, int, str, Any]] = []
        self._internal_seq = 0
        self.current_time = HyperTime(Fraction(0))

        # C22 explicitly places the first entity at t=1 for every experiment.
        self.schedule_event(1.0, 5 if not variant else 0, "arrive", None)
        self.update_sigma()

    def schedule_event(
        self, delay: float, priority: int, event_type: str, payload: Any = None
    ) -> None:
        if isinstance(delay, bool) or not isinstance(delay, (int, float)):
            raise TypeError("event delay must be a real number")
        if delay < 0.0:
            raise ValueError("event delay must be non-negative")
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise TypeError("event priority must be an integer")
        if priority < 0:
            raise ValueError("event priority must be non-negative")
        if not isinstance(event_type, str) or not event_type:
            raise ValueError("event_type must be a non-empty string")
        self._internal_seq += 1
        # NSA-DEVS encoding: finite delay + epsilon priority
        if delay > 0:
            target_time = self.current_time.after_finite(delay)
            if priority > 0:
                target_time = target_time.after_epsilon(priority)
        else:
            target_time = HyperTime(
                self.current_time.macro,
                max(priority, self.current_time.micro + 1),
            )

        heapq.heappush(
            self._internal_events,
            (target_time, priority, self._internal_seq, event_type, payload),
        )

    def schedule_eps_event(
        self, priority: int, event_type: str, payload: Any = None
    ) -> None:
        if not isinstance(priority, int) or isinstance(priority, bool):
            raise TypeError("event priority must be an integer")
        if priority < 0:
            raise ValueError("event priority must be non-negative")
        if not isinstance(event_type, str) or not event_type:
            raise ValueError("event_type must be a non-empty string")
        self._internal_seq += 1
        target_time = HyperTime(
            self.current_time.macro,
            max(priority, self.current_time.micro + 1),
        )
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
            if macro_diff < 0 or (
                macro_diff == 0 and next_time.micro < self.current_time.micro
            ):
                self.sigma = HyperTime(Fraction(0))  # catch up
            elif macro_diff == 0:
                self.sigma = HyperTime(
                    Fraction(0), next_time.micro - self.current_time.micro
                )
            else:
                self.sigma = HyperTime(macro_diff, next_time.micro)

    def time_advance(self) -> HyperTime | None:
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

        self.lqt_max = max(self.lqt_max, sum(len(q) for q in self.queues))
        if not self.stochastic:
            queue_length = sum(len(q) for q in self.queues)
            if queue_length != self.lqt_trace[-1][1]:
                self.lqt_trace.append((float(self.current_time.macro), queue_length))
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
        self.creation_times.append(float(self.current_time.macro))
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
            while entity.reneged and self.queues[q_idx]:
                entity = self.queues[q_idx].pop(0)
            if entity.reneged:
                return
            self.servers[q_idx] = entity
            entity.assigned_queue = -1
            entity.in_service = True
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
            entity.in_service = False
            entity.terminated = True
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
        super().__init__(name, stochastic, large, variant, rng)
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
        super().__init__(name, stochastic, large, variant, rng)
        self.t_r = 9.0
        self.renege_events = 0
        self.renege_records: list[tuple[float, int]] = []

    def process_entity_arrival(self, entity: Entity) -> None:
        super().process_entity_arrival(entity)
        self.schedule_event(self.t_r, 3, "renege", entity)

    def handle_renege(self, entity: Entity) -> None:
        q_idx = entity.assigned_queue
        if q_idx == -1 or entity.in_service or entity.terminated:
            return
        queue = self.queues[q_idx]
        try:
            queue.remove(entity)
        except ValueError:
            return
        entity.assigned_queue = -1
        entity.reneged = True
        entity.terminated = True
        entity.queue_wait_time += float(self.current_time.macro) - entity.enter_queue_time
        self.wait_times.append(entity.queue_wait_time)

        self.renege_events += 1
        if not self.stochastic:
            self.renege_records.append((float(self.current_time.macro), entity.id))

        self.terminated_ids.append(entity.id)
        self.termination_times.append(float(self.current_time.macro))
        self.entities_terminated += 1
        self.check_enter_server(q_idx)


class ClassingSystem(BaseDevsSystem):
    def __init__(
        self,
        name: str,
        stochastic: bool = False,
        large: bool = False,
        variant: bool = False,
        rng: random.Random | None = None,
    ):
        super().__init__(name, stochastic, large, variant, rng)
        self.n_c = 5
        self.t_c = 10.0
        self.current_class = 0
        # C22 §4 assigns deterministic classes 1, 2, ..., nC, 1, ...
        # The operator itself calls them in the opposite direction.
        self.det_class_counter = 1
        self.operator_started = False

        self.schedule_event(self.t_c, 6, "operator")
        self.class_wait_times: dict[int, list[float]] = {
            i: [] for i in range(1, self.n_c + 1)
        }

    def process_entity_arrival(self, entity: Entity) -> None:
        super().process_entity_arrival(entity)
        if self.operator_started and entity.entity_class == self.current_class:
            q_idx = entity.assigned_queue
            self.reorder_queues()
            self.check_enter_server(q_idx)

    def handle_arrive(self) -> None:
        if self.entities_created >= self.num_entities:
            return

        self.entities_created += 1
        self.creation_times.append(float(self.current_time.macro))

        if self.stochastic:
            c = self.rng.randint(1, self.n_c)
        else:
            c = self.det_class_counter
            self.det_class_counter = c % self.n_c + 1

        entity = Entity(
            id=self.entities_created,
            creation_time=float(self.current_time.macro),
            entity_class=c,
        )
        self.process_entity_arrival(entity)

        if (
            self.operator_started
            and self.current_class == 0
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

        self.operator_started = True

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
            while entity.reneged and self.queues[q_idx]:
                entity = self.queues[q_idx].pop(0)
            if entity.reneged:
                return
            self.servers[q_idx] = entity
            entity.assigned_queue = -1
            entity.in_service = True
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

    processed_events = sim.run()
    active_entities = sum(len(queue) for queue in system.queues) + sum(
        server is not None for server in system.servers
    )
    if system.entities_created != system.num_entities:
        raise RuntimeError("C22 simulation did not create every configured entity")
    if system.entities_terminated != system.num_entities or active_entities:
        raise RuntimeError("C22 simulation ended with unterminated entities")
    if (
        len(system.terminated_ids) != system.num_entities
        or len(set(system.terminated_ids)) != system.num_entities
        or len(system.termination_times) != system.num_entities
    ):
        raise RuntimeError("C22 entity lifecycle contains a missing or duplicate exit")

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
        "first_arrival_time": system.creation_times[0],
        "entities_created": system.entities_created,
        "entities_terminated": system.entities_terminated,
        "active_entities": active_entities,
        "processed_events": processed_events,
    }

    if not stochastic:
        res["ids_out"] = system.terminated_ids[-20:]
        res["times_out"] = system.termination_times[-20:]
        res["lqt_trace"] = system.lqt_trace

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
