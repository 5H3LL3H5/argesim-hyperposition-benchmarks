"""ARGESIM C22: Non-standard Queuing Policies.

Implements four variants of a queuing system (Basic, Jockeying, Reneging, Classing)
using an event-based discrete event simulation (DES) core.
"""

from __future__ import annotations

import heapq
import random
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass(order=True)
class Event:
    """A scheduled simulation event."""

    time: float
    priority: int
    sequence: int
    action: Callable[[], None] = field(compare=False)


class Simulator:
    """A simple discrete-event simulator engine."""

    def __init__(self) -> None:
        self.time: float = 0.0
        self.events: list[Event] = []
        self._sequence: int = 0
        self.running: bool = True

    def schedule(self, delay: float, priority: int, action: Callable[[], None]) -> None:
        """Schedule an action to occur after a delay."""
        self._sequence += 1
        heapq.heappush(
            self.events,
            Event(self.time + delay, priority, self._sequence, action),
        )

    def run(self) -> None:
        """Run the simulation until no events remain or stopped."""
        while self.running and self.events:
            event = heapq.heappop(self.events)
            self.time = event.time
            event.action()


@dataclass
class Entity:
    id: int
    creation_time: float
    enter_queue_time: float = 0.0
    queue_wait_time: float = 0.0  # Sum of time spent in queues (for jockeying)
    reneged: bool = False
    entity_class: int = 0
    assigned_queue: int = -1


class BaseSystem:
    """Base class for all queuing models."""

    # Event priorities (lower number = higher priority / executed first)
    PRIO_LEAVE_SERVER = 1
    PRIO_ENTER_SERVER = 2
    PRIO_RENEGE = 3
    PRIO_JOCKEY = 4
    PRIO_ARRIVE = 5
    PRIO_OPERATOR = 6

    def __init__(self, sim: Simulator, stochastic: bool = False, large: bool = False):
        self.sim = sim
        self.stochastic = stochastic
        self.large = large
        self.num_queues = 40 if large else 4
        self.num_entities = 5000 if large else (500 if stochastic else 100)
        self.interarrival_time = 0.1 if large else 1.0
        self.service_time_mode = 4.5
        self.service_time_hw = 2.0

        self.queues: list[list[Entity]] = [[] for _ in range(self.num_queues)]
        self.servers: list[Entity | None] = [None for _ in range(self.num_queues)]

        self.entities_created = 0
        self.entities_terminated = 0

        # Statistics
        self.terminated_ids: list[int] = []
        self.termination_times: list[float] = []
        self.lqt_max = 0
        self.lqt_integral = 0.0
        self.last_time = 0.0
        self.wait_times: list[float] = []

        # For variant ordering (used in 1.4 optional)
        self.arrive_priority = self.PRIO_ARRIVE

        # Start generator
        self.sim.schedule(1.0, self.arrive_priority, self.generate_entity)

    def update_stats(self) -> None:
        dt = self.sim.time - self.last_time
        lqt = sum(len(q) for q in self.queues)
        self.lqt_integral += lqt * dt
        if lqt > self.lqt_max:
            self.lqt_max = lqt
        self.last_time = self.sim.time

    def get_service_time(self) -> float:
        if not self.stochastic:
            return self.service_time_mode
        else:
            # Symmetric triangular distribution
            # Note: The problem asks for triangular with mode 4.5 and half-width 2.0.
            # random.triangular(low, high, mode)
            return random.triangular(
                self.service_time_mode - self.service_time_hw,
                self.service_time_mode + self.service_time_hw,
                self.service_time_mode,
            )

    def get_interarrival_time(self) -> float:
        if not self.stochastic:
            return self.interarrival_time
        else:
            return random.expovariate(1.0 / self.interarrival_time)

    def total_length(self, i: int) -> int:
        """Length of queue i including server."""
        return len(self.queues[i]) + (1 if self.servers[i] is not None else 0)

    def choose_queue(self) -> int:
        """Find the shortest line (queue + server). Break ties with smallest index."""
        min_len = min(self.total_length(i) for i in range(self.num_queues))
        for i in range(self.num_queues):
            if self.total_length(i) == min_len:
                return i
        return 0

    def generate_entity(self) -> None:
        self.update_stats()
        if self.entities_created >= self.num_entities:
            return

        self.entities_created += 1
        entity = Entity(id=self.entities_created, creation_time=self.sim.time)
        self.on_entity_arrive(entity)

        if self.entities_created < self.num_entities:
            self.sim.schedule(
                self.get_interarrival_time(), self.arrive_priority, self.generate_entity
            )

    def on_entity_arrive(self, entity: Entity) -> None:
        q_idx = self.choose_queue()
        entity.assigned_queue = q_idx
        entity.enter_queue_time = self.sim.time
        self.queues[q_idx].append(entity)
        self.check_enter_server(q_idx)

    def check_enter_server(self, q_idx: int) -> None:
        if self.servers[q_idx] is None and self.queues[q_idx]:
            # Use schedule to enforce priority
            self.sim.schedule(
                0.0, self.PRIO_ENTER_SERVER, lambda idx=q_idx: self.enter_server(idx)
            )

    def enter_server(self, q_idx: int) -> None:
        if self.servers[q_idx] is None and self.queues[q_idx]:
            self.update_stats()
            entity = self.queues[q_idx].pop(0)
            self.servers[q_idx] = entity
            entity.queue_wait_time += self.sim.time - entity.enter_queue_time
            self.wait_times.append(entity.queue_wait_time)
            self.sim.schedule(
                self.get_service_time(),
                self.PRIO_LEAVE_SERVER,
                lambda idx=q_idx: self.leave_server(idx),
            )
            self.post_enter_server(q_idx, entity)

    def post_enter_server(self, q_idx: int, entity: Entity) -> None:
        pass

    def leave_server(self, q_idx: int) -> None:
        self.update_stats()
        entity = self.servers[q_idx]
        self.servers[q_idx] = None
        if entity is not None:
            self.terminated_ids.append(entity.id)
            self.termination_times.append(self.sim.time)
            self.entities_terminated += 1
            if self.entities_terminated >= self.num_entities:
                self.sim.running = False
        self.check_enter_server(q_idx)
        self.post_leave_server(q_idx)

    def post_leave_server(self, q_idx: int) -> None:
        pass


class JockeyingSystem(BaseSystem):
    def __init__(self, sim: Simulator, stochastic: bool = False, large: bool = False):
        super().__init__(sim, stochastic, large)
        # Event order:
        # 1. leave server
        # 2. enter server
        # 3. jockey (we make it lower priority than enter server)
        # 4. arrive
        self.jockey_events = 0
        self.jockey_records: list[tuple[float, int, int, int]] = []

    def post_leave_server(self, q_idx: int) -> None:
        self.check_jockeying()

    def post_enter_server(self, q_idx: int, entity: Entity) -> None:
        self.check_jockeying()

    def check_jockeying(self) -> None:
        # Jockeying happens immediately, when a queue (incl. server) is at least shorter by 2 than another one.
        # We schedule it at priority 3 or 4, but the text says "immediately".
        # We will schedule a single jockey check event at 0.0 delay with PRIO_JOCKEY to ensure it happens
        # after any leave/enter server events at the same time.
        self.sim.schedule(0.0, self.PRIO_JOCKEY, self.do_jockey)

    def do_jockey(self) -> None:
        while True:
            lengths = [self.total_length(i) for i in range(self.num_queues)]
            min_len = min(lengths)

            # Find destination queue
            dest_cands = [i for i in range(self.num_queues) if lengths[i] == min_len]
            if not dest_cands:
                break
            dest_q = dest_cands[0]  # smallest queue number

            # Find source queue
            # Must be at least 2 longer than dest_q (so lengths[src] >= min_len + 2)
            src_cands = [
                i
                for i in range(self.num_queues)
                if lengths[i] >= min_len + 2 and self.queues[i]
            ]
            if not src_cands:
                break

            # Nearest to dest_q
            nearest_dist = min(abs(i - dest_q) for i in src_cands)
            nearest_srcs = [i for i in src_cands if abs(i - dest_q) == nearest_dist]
            src_q = nearest_srcs[0]  # smallest number if tie

            # Perform jockeying
            self.update_stats()
            entity = self.queues[src_q].pop(-1)  # detach last element

            # Update waiting time for visited queues
            entity.queue_wait_time += self.sim.time - entity.enter_queue_time
            entity.enter_queue_time = self.sim.time
            entity.assigned_queue = dest_q

            self.queues[dest_q].append(entity)
            self.jockey_events += 1
            if not self.stochastic:
                self.jockey_records.append(
                    (self.sim.time, entity.id, src_q + 1, dest_q + 1)
                )

            # Since a queue changed, check if it can enter server
            self.check_enter_server(dest_q)


class RenegingSystem(BaseSystem):
    def __init__(self, sim: Simulator, stochastic: bool = False, large: bool = False):
        super().__init__(sim, stochastic, large)
        self.t_r = 9.0
        self.renege_events = 0
        self.renege_records: list[tuple[float, int]] = []

    def on_entity_arrive(self, entity: Entity) -> None:
        super().on_entity_arrive(entity)
        self.sim.schedule(
            self.t_r, self.PRIO_RENEGE, lambda e=entity: self.do_renege(e)
        )

    def do_renege(self, entity: Entity) -> None:
        if entity.assigned_queue != -1 and entity in self.queues[entity.assigned_queue]:
            self.update_stats()
            self.queues[entity.assigned_queue].remove(entity)
            entity.reneged = True
            entity.queue_wait_time = self.t_r
            self.wait_times.append(entity.queue_wait_time)

            self.renege_events += 1
            if not self.stochastic:
                self.renege_records.append((self.sim.time, entity.id))

            self.entities_terminated += 1
            if self.entities_terminated >= self.num_entities:
                self.sim.running = False


class ClassingSystem(BaseSystem):
    def __init__(self, sim: Simulator, stochastic: bool = False, large: bool = False):
        super().__init__(sim, stochastic, large)
        self.n_c = 5
        self.t_c = 10.0
        self.current_class = 0
        self.det_class_counter = 1

        # operator loop
        self.sim.schedule(self.t_c, self.PRIO_OPERATOR, self.operator_call)

        self.class_wait_times: dict[int, list[float]] = {
            i: [] for i in range(1, self.n_c + 1)
        }

    def generate_entity(self) -> None:
        self.update_stats()
        if self.entities_created >= self.num_entities:
            return

        self.entities_created += 1

        # Assign class
        if self.stochastic:
            c = random.randint(1, self.n_c)
        else:
            c = self.det_class_counter
            self.det_class_counter = (self.det_class_counter % self.n_c) + 1

        entity = Entity(
            id=self.entities_created, creation_time=self.sim.time, entity_class=c
        )
        self.on_entity_arrive(entity)

        # Wake up operator if stalled
        if (
            self.current_class == 0
            and sum(self.total_length(i) for i in range(self.num_queues)) > 0
        ):
            self.sim.schedule(0.0, self.PRIO_OPERATOR, self.operator_call)

        if self.entities_created < self.num_entities:
            self.sim.schedule(
                self.get_interarrival_time(), self.arrive_priority, self.generate_entity
            )

    def operator_call(self) -> None:
        if self.entities_terminated >= self.num_entities:
            return

        total_in_system = sum(self.total_length(i) for i in range(self.num_queues))
        if total_in_system == 0:
            self.current_class = 0  # Stalled
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

        # Wait until all entities of current_class have been served
        # We do this by checking at each leave_server if they are done
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
                self.sim.schedule(
                    0.0,
                    self.PRIO_ENTER_SERVER,
                    lambda idx=q_idx: self.enter_server(idx),
                )

    def enter_server(self, q_idx: int) -> None:
        if (
            self.servers[q_idx] is None
            and self.queues[q_idx]
            and self.queues[q_idx][0].entity_class == self.current_class
        ):
            self.update_stats()
            entity = self.queues[q_idx].pop(0)
            self.servers[q_idx] = entity
            entity.queue_wait_time += self.sim.time - entity.enter_queue_time
            self.wait_times.append(entity.queue_wait_time)
            self.class_wait_times[entity.entity_class].append(entity.queue_wait_time)
            self.sim.schedule(
                self.get_service_time(),
                self.PRIO_LEAVE_SERVER,
                lambda idx=q_idx: self.leave_server(idx),
            )

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
                self.sim.schedule(0.0, self.PRIO_OPERATOR, self.operator_call)


def run_model(
    system_cls: type[BaseSystem], stochastic: bool, large: bool, variant: bool = False
) -> dict[str, Any]:
    # Reset random seed for reproducibility in stochastic mode
    random.seed(42)

    sim = Simulator()
    system = system_cls(sim, stochastic, large)

    if variant:
        system.arrive_priority = 0  # Highest priority to execute before leave_server

    sim.run()

    # Finalize stats
    system.update_stats()
    avg_lqt = system.lqt_integral / sim.time if sim.time > 0 else 0.0
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
        "deterministic": run_model(BaseSystem, False, False),
        "deterministic_variant": run_model(BaseSystem, False, False, variant=True),
        "stochastic": run_model(BaseSystem, True, False),
        "stochastic_large": run_model(BaseSystem, True, True),
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
