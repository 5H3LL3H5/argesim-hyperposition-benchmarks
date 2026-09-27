"""ARGESIM C06: Emergency Department - Follow-up Treatment."""

from __future__ import annotations

import heapq
import math
import random
from collections.abc import Callable
from enum import Enum

from nsa_devs import DesScheduler


class Simulation:
    """C06 adapter around the reusable superdense-time DES scheduler."""

    def __init__(self, seed: int = 42):
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise TypeError("seed must be an integer")
        self.seed = seed
        self.scheduler = DesScheduler()
        self.rng = random.Random(seed)

    @property
    def now(self) -> float:
        return float(self.scheduler.time.macro)

    @property
    def events(self) -> list[object]:
        return self.scheduler.events

    def schedule(self, delay: float, action: Callable[[], None]) -> None:
        self.scheduler.schedule(delay, "C06-event", action)

    def run(self, until: float = math.inf, *, max_events: int = 1_000_000) -> int:
        if math.isinf(until) and until > 0.0:
            return self.scheduler.run_until_idle(max_events=max_events)
        return self.scheduler.run(until, max_events=max_events)


class QueueDiscipline(Enum):
    FIFO = 1
    PRIORITY = 2


class Resource:
    def __init__(
        self,
        env: Simulation,
        capacity: int,
        discipline: QueueDiscipline = QueueDiscipline.FIFO,
        name: str = "",
    ):
        if not isinstance(capacity, int) or isinstance(capacity, bool):
            raise TypeError("resource capacity must be an integer")
        if capacity < 0:
            raise ValueError("resource capacity must be non-negative")
        if not isinstance(discipline, QueueDiscipline):
            raise TypeError("discipline must be QueueDiscipline")
        self.env = env
        self.capacity = capacity
        self.discipline = discipline
        self.name = name

        self.in_use = 0
        self.queue: list[tuple[float, int, Callable[[], None]]] = []
        self._seq = 0

    def request(self, priority: int = 0) -> Callable[[Callable[[], None]], None]:
        def do_request(callback: Callable[[], None]) -> None:
            if not callable(callback):
                raise TypeError("resource request callback must be callable")
            if self.in_use < self.capacity:
                self.in_use += 1
                self.env.schedule(0.0, callback)
            else:
                if self.discipline == QueueDiscipline.FIFO:
                    self.queue.append((0.0, len(self.queue), callback))
                else:
                    # Lowest priority number = highest priority
                    self._seq += 1
                    heapq.heappush(self.queue, (priority, self._seq, callback))

        return do_request

    def set_capacity(self, new_capacity: int) -> None:
        if not isinstance(new_capacity, int) or isinstance(new_capacity, bool):
            raise TypeError("resource capacity must be an integer")
        if new_capacity < 0:
            raise ValueError("resource capacity must be non-negative")
        self.capacity = new_capacity
        while self.in_use < self.capacity and self.queue:
            if self.discipline == QueueDiscipline.FIFO:
                _, _, callback = self.queue.pop(0)
            else:
                _, _, callback = heapq.heappop(self.queue)
            self.in_use += 1
            self.env.schedule(0.0, callback)

    def release(self) -> None:
        if self.in_use <= 0:
            raise RuntimeError(f"cannot release idle resource {self.name!r}")
        self.in_use -= 1
        if self.in_use < self.capacity and self.queue:
            if self.discipline == QueueDiscipline.FIFO:
                _, _, callback = self.queue.pop(0)
            else:
                _, _, callback = heapq.heappop(self.queue)
            self.in_use += 1
            self.env.schedule(0.0, callback)


class Facilities:
    def __init__(
        self,
        env: Simulation,
        discipline: QueueDiscipline = QueueDiscipline.FIFO,
    ):
        self.registration = Resource(
            env,
            capacity=1,
            discipline=discipline,
            name="Registration",
        )
        self.cw1 = Resource(env, capacity=0, discipline=discipline, name="CW1")
        self.cw2 = Resource(env, capacity=0, discipline=discipline, name="CW2")
        self.xray = Resource(env, capacity=0, discipline=discipline, name="X-Ray")
        self.plaster = Resource(env, capacity=0, discipline=discipline, name="Plaster")

        self.cw2_queue_was_large = False
        self.cw1_transferred_doctor_turn = False
        self.cw2_transferred_doctor_turn = False


def exp_dist(env: Simulation, mean: float) -> float:
    """Sample an exponential duration expressed by its mean in minutes."""

    if not math.isfinite(mean) or mean <= 0.0:
        raise ValueError("exponential mean must be positive and finite")
    return env.rng.expovariate(1.0 / mean)

def triangular_dist(
    rng: random.Random, low: float, mode: float, high: float
) -> float:
    return rng.triangular(low, high, mode)


class Patient:
    def __init__(self, env: Simulation, id: int, type_: int):
        self.env = env
        self.id = id
        self.type_ = type_
        self.rng = random.Random((env.seed << 32) ^ id)
        self.arrival_time = env.now
        self.end_time = 0.0
        self.ward = 0  # 1 for CW1, 2 for CW2



_CW1_TREATMENT = (1.5, 3.2, 5.0)
_CW2_TREATMENT = (2.8, 4.1, 6.3)


def _update_doctor_exchange(
    facilities: Facilities,
    *,
    task_b_active: bool,
) -> None:
    """Apply the Task-B hysteresis for exchanging one CW1 and CW2 doctor."""

    if not task_b_active:
        return
    cw2_queue_len = len(facilities.cw2.queue)
    if not facilities.cw2_queue_was_large and cw2_queue_len > 20:
        facilities.cw2_queue_was_large = True
    elif facilities.cw2_queue_was_large and cw2_queue_len <= 5:
        facilities.cw2_queue_was_large = False


def _ward_treatment_time(
    patient: Patient,
    facilities: Facilities,
    *,
    task_b_active: bool,
) -> float:
    """Sample the treating doctor's service time for the selected casualty ward.

    Task B exchanges one of the two doctors between CW1 and CW2 while the
    CW2 queue is above the hysteresis threshold.  The ward capacities remain
    unchanged; one alternating service in each ward therefore uses the other
    ward's doctor-time distribution.
    """

    if patient.ward not in (1, 2):
        raise ValueError("patient must be assigned to CW1 or CW2 before treatment")

    local = _CW1_TREATMENT if patient.ward == 1 else _CW2_TREATMENT
    if not task_b_active or not facilities.cw2_queue_was_large:
        return triangular_dist(patient.rng, *local)

    if patient.ward == 1:
        facilities.cw1_transferred_doctor_turn = (
            not facilities.cw1_transferred_doctor_turn
        )
        transferred = facilities.cw1_transferred_doctor_turn
        distribution = _CW2_TREATMENT if transferred else _CW1_TREATMENT
    else:
        facilities.cw2_transferred_doctor_turn = (
            not facilities.cw2_transferred_doctor_turn
        )
        transferred = facilities.cw2_transferred_doctor_turn
        distribution = _CW1_TREATMENT if transferred else _CW2_TREATMENT

    return triangular_dist(patient.rng, *distribution)


def process_patient(
    env: Simulation,
    patient: Patient,
    facilities: Facilities,
    on_finish: Callable[[Patient], None],
    task_b_active: bool = False,
) -> None:

    def check_doctor_swap() -> None:
        _update_doctor_exchange(facilities, task_b_active=task_b_active)

    def ward_treatment_time() -> float:
        return _ward_treatment_time(
            patient,
            facilities,
            task_b_active=task_b_active,
        )

    req_reg = facilities.registration.request(priority=0)

    def after_registration_req() -> None:
        delay = triangular_dist(patient.rng, 0.2, 0.5, 1.0)

        def after_delay() -> None:
            facilities.registration.release()

            # Decide ward
            if patient.rng.random() < 0.6:
                patient.ward = 1
                ward_res = facilities.cw1
            else:
                patient.ward = 2
                ward_res = facilities.cw2

            check_doctor_swap()

            req_ward = ward_res.request(priority=0)
            req_ward(lambda: after_ward_1(ward_res))
            check_doctor_swap()

        env.schedule(delay, after_delay)

    def after_ward_1(ward_res: Resource) -> None:
        delay = ward_treatment_time()

        def after_delay() -> None:
            ward_res.release()
            check_doctor_swap()

            if patient.type_ == 1:
                # Type 1: X-ray -> Ward -> Leave
                req_xray = facilities.xray.request(priority=0)
                req_xray(lambda: after_xray_type1(ward_res))
            elif patient.type_ == 2:
                # Type 2: Plaster -> Leave
                req_plaster = facilities.plaster.request(priority=0)
                req_plaster(after_plaster_type2)
            elif patient.type_ == 3:
                # Ward -> X-ray -> plaster -> X-ray -> ward -> leave.
                req_xray = facilities.xray.request(priority=0)
                req_xray(lambda: after_xray_1_type3(ward_res))
            elif patient.type_ == 4:
                # Type 4: Leave
                patient.end_time = env.now
                on_finish(patient)

        env.schedule(delay, after_delay)

    def after_xray_type1(ward_res: Resource) -> None:
        delay = triangular_dist(patient.rng, 2.0, 2.8, 4.1)

        def after_delay() -> None:
            facilities.xray.release()
            req_ward = ward_res.request(priority=-1)
            req_ward(lambda: after_ward_2_type1(ward_res))

        env.schedule(delay, after_delay)

    def after_ward_2_type1(ward_res: Resource) -> None:
        delay = ward_treatment_time()

        def after_delay() -> None:
            ward_res.release()
            check_doctor_swap()
            patient.end_time = env.now
            on_finish(patient)

        env.schedule(delay, after_delay)

    def after_plaster_type2() -> None:
        delay = triangular_dist(patient.rng, 3.0, 3.8, 4.7)

        def after_delay() -> None:
            facilities.plaster.release()
            patient.end_time = env.now
            on_finish(patient)

        env.schedule(delay, after_delay)

    def after_xray_1_type3(ward_res: Resource) -> None:
        delay = triangular_dist(patient.rng, 2.0, 2.8, 4.1)

        def after_delay() -> None:
            facilities.xray.release()
            req_plaster = facilities.plaster.request(priority=0)
            req_plaster(lambda: after_plaster_type3(ward_res))

        env.schedule(delay, after_delay)

    def after_plaster_type3(ward_res: Resource) -> None:
        delay = triangular_dist(patient.rng, 3.0, 3.8, 4.7)

        def after_delay() -> None:
            facilities.plaster.release()
            req_xray = facilities.xray.request(priority=-1)
            req_xray(lambda: after_xray_2_type3(ward_res))

        env.schedule(delay, after_delay)

    def after_xray_2_type3(ward_res: Resource) -> None:
        delay = triangular_dist(patient.rng, 2.0, 2.8, 4.1)

        def after_delay() -> None:
            facilities.xray.release()
            req_ward = ward_res.request(priority=-1)
            req_ward(lambda: after_ward_2_type3(ward_res))

        env.schedule(delay, after_delay)

    def after_ward_2_type3(ward_res: Resource) -> None:
        delay = ward_treatment_time()

        def after_delay() -> None:
            ward_res.release()
            check_doctor_swap()
            patient.end_time = env.now
            on_finish(patient)

        env.schedule(delay, after_delay)

    req_reg(after_registration_req)


def generate_patients(
    env: Simulation,
    facilities: Facilities,
    num_patients: int,
    on_finish: Callable[[Patient], None],
    task_b_active: bool = False,
) -> None:
    """Generate arrivals from 07:30 while treatment facilities open at 08:00."""

    def spawn_patient(i: int) -> None:
        if i >= num_patients:
            return

        r = env.rng.random()
        if r < 0.35:
            ptype = 1
        elif r < 0.55:
            ptype = 2
        elif r < 0.60:
            ptype = 3
        else:
            ptype = 4

        p = Patient(env, i, ptype)
        process_patient(env, p, facilities, on_finish, task_b_active)

        delay = exp_dist(env, 0.3)
        env.schedule(delay, lambda: spawn_patient(i + 1))

    env.schedule(0.0, lambda: spawn_patient(0))


def open_facilities(facilities: Facilities) -> None:
    """Open the treatment resources at minute 30 (08:00)."""

    facilities.cw1.set_capacity(2)
    facilities.cw2.set_capacity(2)
    facilities.xray.set_capacity(2)
    facilities.plaster.set_capacity(1)


def _summarize_patients(patients: list[Patient]) -> dict[str, float]:
    times_by_type: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}
    treatment_times = []
    for patient in patients:
        treatment_time = patient.end_time - patient.arrival_time
        treatment_times.append(treatment_time)
        times_by_type[patient.type_].append(treatment_time)

    overall = sum(treatment_times) / len(treatment_times)
    metrics = {"overall": overall}
    for patient_type, values in times_by_type.items():
        metrics[f"type_{patient_type}"] = (
            sum(values) / len(values) if values else 0.0
        )
    variance = sum((value - overall) ** 2 for value in treatment_times) / len(
        treatment_times
    )
    metrics["std_dev"] = math.sqrt(variance)
    return metrics


def solve_c06(
    *,
    discipline: QueueDiscipline = QueueDiscipline.FIFO,
    task_b_active: bool = False,
    seed: int = 42,
    num_patients: int = 250,
) -> dict[str, float]:
    """Run one reproducible C06 policy through the shared DES scheduler."""

    if not isinstance(num_patients, int) or isinstance(num_patients, bool):
        raise TypeError("num_patients must be an integer")
    if num_patients <= 0:
        raise ValueError("num_patients must be positive")
    if not isinstance(task_b_active, bool):
        raise TypeError("task_b_active must be bool")
    env = Simulation(seed=seed)
    facilities = Facilities(env, discipline=discipline)
    finished_patients: list[Patient] = []

    generate_patients(
        env,
        facilities,
        num_patients,
        finished_patients.append,
        task_b_active=task_b_active,
    )
    env.schedule(30.0, lambda: open_facilities(facilities))
    env.run()
    if len(finished_patients) != num_patients:
        raise RuntimeError("C06 simulation ended before every patient completed")
    return _summarize_patients(finished_patients)


def solve_c06_task_a() -> dict[str, float]:
    """Run the FIFO baseline."""

    return solve_c06()


def solve_c06_task_b() -> dict[str, float]:
    """Run the benchmark's capacity-preserving doctor-swap policy."""

    return solve_c06(task_b_active=True)


def solve_c06_task_c() -> dict[str, float]:
    """Give returning patients priority at treatment resources."""

    return solve_c06(discipline=QueueDiscipline.PRIORITY)
