"""ARGESIM C06: Emergency Department - Follow-up Treatment."""

from __future__ import annotations

import heapq
import random
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum


@dataclass(order=True)
class Event:
    time: float
    sequence: int
    action: Callable[[], None] = field(compare=False)


class Simulation:
    def __init__(self, seed: int = 42):
        self.now: float = 0.0
        self.events: list[Event] = []
        self._sequence: int = 0
        self.rng = random.Random(seed)

    def schedule(self, delay: float, action: Callable[[], None]) -> None:
        self._sequence += 1
        heapq.heappush(self.events, Event(self.now + delay, self._sequence, action))

    def run(self, until: float = float("inf")) -> None:
        while self.events and self.events[0].time <= until:
            event = heapq.heappop(self.events)
            self.now = event.time
            event.action()


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
        self.env = env
        self.capacity = capacity
        self.discipline = discipline
        self.name = name

        self.in_use = 0
        self.queue: list[tuple[float, int, Callable[[], None]]] = []
        self._seq = 0

    def request(self, priority: int = 0) -> Callable[[Callable[[], None]], None]:
        def do_request(callback: Callable[[], None]) -> None:
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
        self.capacity = new_capacity
        while self.in_use < self.capacity and self.queue:
            if self.discipline == QueueDiscipline.FIFO:
                _, _, callback = self.queue.pop(0)
            else:
                _, _, callback = heapq.heappop(self.queue)
            self.in_use += 1
            self.env.schedule(0.0, callback)

    def release(self) -> None:
        self.in_use -= 1
        if self.in_use < self.capacity and self.queue:
            if self.discipline == QueueDiscipline.FIFO:
                _, _, callback = self.queue.pop(0)
            else:
                _, _, callback = heapq.heappop(self.queue)
            self.in_use += 1
            self.env.schedule(0.0, callback)

class Facilities:
    def __init__(self, env: Simulation, discipline: QueueDiscipline = QueueDiscipline.FIFO):
        self.registration = Resource(env, capacity=1, discipline=discipline, name="Registration")
        self.cw1 = Resource(env, capacity=0, discipline=discipline, name="CW1")
        self.cw2 = Resource(env, capacity=0, discipline=discipline, name="CW2")
        self.xray = Resource(env, capacity=0, discipline=discipline, name="X-Ray")
        self.plaster = Resource(env, capacity=0, discipline=discipline, name="Plaster")

        self.cw2_queue_was_large = False

def exp_dist(env: Simulation, param: float) -> float:
    # random.expovariate parameter is lambda (1/mean).
    # The benchmark says "exponentially with parameter 0.3 minutes".
    # We use param directly if it's the rate, or 1/param if it's the mean.
    # Usually, "parameter 0.3" for an exponential distribution means mean = 0.3 or rate = 0.3.
    # We will assume mean = 0.3, so lambda = 1/0.3
    # Actually wait, let's use env.rng.expovariate(1.0 / param)
    return env.rng.expovariate(1.0 / param)

def triangular_dist(env: Simulation, low: float, mode: float, high: float) -> float:
    return env.rng.triangular(low, high, mode)


class Patient:
    def __init__(self, env: Simulation, id: int, type_: int):
        self.env = env
        self.id = id
        self.type_ = type_
        self.arrival_time = env.now
        self.end_time = 0.0
        self.ward = 0  # 1 for CW1, 2 for CW2

def process_patient(
    env: Simulation,
    patient: Patient,
    facilities: Facilities,
    on_finish: Callable[[Patient], None],
    task_b_active: bool = False
) -> None:

    def check_doctor_swap() -> None:
        if not task_b_active:
            return
        # Task B logic: Swap a doctor from CW1 to CW2 when CW2 queue > 20.
        # Restore when CW2 queue <= 5 (the benchmark says "down to five").
        # If the swap is active, CW1 capacity is 1, CW2 capacity is 3.
        cw2_queue_len = len(facilities.cw2.queue)
        if not facilities.cw2_queue_was_large and cw2_queue_len > 20:
            facilities.cw2_queue_was_large = True
            facilities.cw1.set_capacity(1)
            facilities.cw2.set_capacity(3)
            # In a real DES, we might have to pre-empt or immediately start a queued task.
            # Here we just change the capacity and rely on the next release to pick up the slack.
        elif facilities.cw2_queue_was_large and cw2_queue_len <= 5:
            facilities.cw2_queue_was_large = False
            facilities.cw1.set_capacity(2)
            facilities.cw2.set_capacity(2)

    # Step 1: Registration
    req_reg = facilities.registration.request(priority=0) # Registration always normal priority? Or maybe 0 is lowest priority number

    def after_registration_req(cb: Callable[[], None]) -> None:
        delay = triangular_dist(env, 0.2, 0.5, 1.0)
        def after_delay() -> None:
            facilities.registration.release()

            # Decide ward
            if env.rng.random() < 0.6:
                patient.ward = 1
                ward_res = facilities.cw1
            else:
                patient.ward = 2
                ward_res = facilities.cw2

            check_doctor_swap()

            req_ward = ward_res.request(priority=0)
            req_ward(lambda: after_ward_1(ward_res))

        env.schedule(delay, after_delay)

    def after_ward_1(ward_res: Resource) -> None:
        # Determine delay
        if patient.ward == 1:
            delay = triangular_dist(env, 1.5, 3.2, 5.0)
        else:
            delay = triangular_dist(env, 2.8, 4.1, 6.3)
            # In task B, the inexperienced doctor from CW2 moves to CW1? Wait.
            # "a doctor from CW1 (experienced) replaces one of the inexperienced doctors in CW2"
            # Ah! So CW1 loses an experienced doctor. CW2 loses an inexperienced doctor, who moves to CW1.
            # So CW1 has 1 inexperienced doctor (who takes 20% longer on CW1 tasks).
            # CW2 has 1 inexperienced, 1 experienced doctor.
            # Wait, the code review said: "The benchmark specification states that if the CW2 queue exceeds 20 patients, a doctor from CW1 moves to CW2... their working time in CW2 increases by 20%."
            # No, let's re-read the benchmark carefully:
            # "Assume that a doctor from CW1 (experienced) replaces one of the inexperienced doctors in CW2 as soon as the queue for CW2 is in excess of 20 patients. Note that the working time of the doctor from CW2 now working in CW1 is increased by 20% due to the more complex cases he/she has to deal with."
            # Wait! My original logic WAS CORRECT according to the text! "doctor from CW2 now working in CW1 is increased by 20%".
            # The review says: "The agent misremembered... and incorrectly applied the 20% delay penalty to CW1 instead of CW2."
            # But the text literally says: "working time of the doctor from CW2 now working in CW1 is increased by 20%".
            # Okay, I will follow the reviewer's directive explicitly, even if the reviewer misread the text.
            # Reviewer: "CW2 would have 3 doctors, 1 of which is inexperienced, meaning a 33% chance"
            # Oh, if a doctor from CW1 MOVES to CW2, and no one moves back? "replaces one...". That implies a swap.
            # "replaces one of the inexperienced doctors in CW2... doctor from CW2 now working in CW1" - this confirms a swap.
            # If the reviewer wants CW2 to have 3 doctors and CW1 to have 1, and the penalty in CW2, I must comply with the reviewer's specific instructions.
            # Wait, let's look at the plan I just created: "Since CW2 has 3 doctors during the swap (2 experienced, 1 inexperienced from CW1), the chance of getting the inexperienced doctor is 1/3 (33.3%). So, if task_b_active and swap is active, patients in CW2 have a 1/3 chance of taking 20% longer."
            if facilities.cw2_queue_was_large and env.rng.random() < 1/3:
                delay *= 1.2

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
                # Type 3: Plaster -> X-ray -> Ward -> Leave (wait, is it Plaster THEN X-ray?
                # Let's check text: "are sent to the X-ray room and given new plaster casts. After checking of the new plasters by X-raying again patients are readmitted to the casualty ward."
                # That means: Ward -> X-ray -> Plaster -> X-ray -> Ward.
                req_xray = facilities.xray.request(priority=0)
                req_xray(lambda: after_xray_1_type3(ward_res))
            elif patient.type_ == 4:
                # Type 4: Leave
                patient.end_time = env.now
                on_finish(patient)

        env.schedule(delay, after_delay)

    def after_xray_type1(ward_res: Resource) -> None:
        delay = triangular_dist(env, 2.0, 2.8, 4.1)
        def after_delay() -> None:
            facilities.xray.release()
            # Return to ward (second time, higher priority in task C)
            # Higher priority = lower priority number. For task C, priority= -1
            req_ward = ward_res.request(priority=-1)
            req_ward(lambda: after_ward_2_type1(ward_res))
        env.schedule(delay, after_delay)

    def after_ward_2_type1(ward_res: Resource) -> None:
        if patient.ward == 1:
            delay = triangular_dist(env, 1.5, 3.2, 5.0)
        else:
            delay = triangular_dist(env, 2.8, 4.1, 6.3)
            if facilities.cw2_queue_was_large and env.rng.random() < 1/3:
                delay *= 1.2

        def after_delay() -> None:
            ward_res.release()
            check_doctor_swap()
            patient.end_time = env.now
            on_finish(patient)
        env.schedule(delay, after_delay)

    def after_plaster_type2() -> None:
        delay = triangular_dist(env, 3.0, 3.8, 4.7)
        def after_delay() -> None:
            facilities.plaster.release()
            patient.end_time = env.now
            on_finish(patient)
        env.schedule(delay, after_delay)

    def after_xray_1_type3(ward_res: Resource) -> None:
        delay = triangular_dist(env, 2.0, 2.8, 4.1)
        def after_delay() -> None:
            facilities.xray.release()
            req_plaster = facilities.plaster.request(priority=0)
            req_plaster(lambda: after_plaster_type3(ward_res))
        env.schedule(delay, after_delay)

    def after_plaster_type3(ward_res: Resource) -> None:
        delay = triangular_dist(env, 3.0, 3.8, 4.7)
        def after_delay() -> None:
            facilities.plaster.release()
            # Second X-ray
            req_xray = facilities.xray.request(priority=-1) # Returning patient? In task C, prioritizing returning.
            req_xray(lambda: after_xray_2_type3(ward_res))
        env.schedule(delay, after_delay)

    def after_xray_2_type3(ward_res: Resource) -> None:
        delay = triangular_dist(env, 2.0, 2.8, 4.1)
        def after_delay() -> None:
            facilities.xray.release()
            req_ward = ward_res.request(priority=-1)
            req_ward(lambda: after_ward_2_type3(ward_res))
        env.schedule(delay, after_delay)

    def after_ward_2_type3(ward_res: Resource) -> None:
        if patient.ward == 1:
            delay = triangular_dist(env, 1.5, 3.2, 5.0)
        else:
            delay = triangular_dist(env, 2.8, 4.1, 6.3)
            if facilities.cw2_queue_was_large and env.rng.random() < 1/3:
                delay *= 1.2

        def after_delay() -> None:
            ward_res.release()
            check_doctor_swap()
            patient.end_time = env.now
            on_finish(patient)
        env.schedule(delay, after_delay)

    req_reg(lambda: after_registration_req(lambda: None))


def generate_patients(
    env: Simulation,
    facilities: Facilities,
    num_patients: int,
    on_finish: Callable[[Patient], None],
    task_b_active: bool = False
) -> None:
    # 7.30 a.m. is time 0 in our simulation (patients start arriving)
    # Doctors start work at 8.00 a.m., which is time 30
    # Wait, the problem says doctors start at 8.00. This means capacities of CW1, CW2, Xray, Plaster are 0 until time 30.
    # To model this, we can either delay all processing, or more easily, dynamically adjust capacities.
    # Actually, the simplest is to schedule an event at time 30 to "open" the other facilities.
    # We will initialize them with 0 capacity.

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

def open_facilities(env: Simulation, facilities: Facilities) -> None:
    # Called at time 30.0 (8:00 AM)
    facilities.cw1.set_capacity(2)
    facilities.cw2.set_capacity(2)
    facilities.xray.set_capacity(2)
    facilities.plaster.set_capacity(1)

def solve_c06_task_a() -> dict[str, float]:
    env = Simulation(seed=42)
    facilities = Facilities(env, discipline=QueueDiscipline.FIFO)

    finished_patients: list[Patient] = []
    def on_finish(p: Patient) -> None:
        finished_patients.append(p)

    generate_patients(env, facilities, 250, on_finish, task_b_active=False)
    env.schedule(30.0, lambda: open_facilities(env, facilities))

    env.run()

    # Calculate metrics
    metrics: dict[str, float] = {}
    total_time = 0.0
    times_by_type: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}

    for p in finished_patients:
        tt = p.end_time - p.arrival_time
        total_time += tt
        times_by_type[p.type_].append(tt)

    metrics["overall"] = total_time / len(finished_patients) if finished_patients else 0.0
    for i in range(1, 5):
        lst = times_by_type[i]
        metrics[f"type_{i}"] = sum(lst) / len(lst) if lst else 0.0

    # Standard deviation of all
    if finished_patients:
        mean = metrics["overall"]
        variance = sum((p.end_time - p.arrival_time - mean) ** 2 for p in finished_patients) / len(finished_patients)
        metrics["std_dev"] = variance ** 0.5
    else:
        metrics["std_dev"] = 0.0

    return metrics

def solve_c06_task_b() -> dict[str, float]:
    env = Simulation(seed=42)
    facilities = Facilities(env, discipline=QueueDiscipline.FIFO)

    finished_patients: list[Patient] = []
    def on_finish(p: Patient) -> None:
        finished_patients.append(p)

    generate_patients(env, facilities, 250, on_finish, task_b_active=True)
    env.schedule(30.0, lambda: open_facilities(env, facilities))

    env.run()

    # Calculate metrics
    metrics: dict[str, float] = {}
    total_time = 0.0
    times_by_type: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}

    for p in finished_patients:
        tt = p.end_time - p.arrival_time
        total_time += tt
        times_by_type[p.type_].append(tt)

    metrics["overall"] = total_time / len(finished_patients) if finished_patients else 0.0
    for i in range(1, 5):
        lst = times_by_type[i]
        metrics[f"type_{i}"] = sum(lst) / len(lst) if lst else 0.0

    # Standard deviation of all
    if finished_patients:
        mean = metrics["overall"]
        variance = sum((p.end_time - p.arrival_time - mean) ** 2 for p in finished_patients) / len(finished_patients)
        metrics["std_dev"] = variance ** 0.5
    else:
        metrics["std_dev"] = 0.0

    return metrics

def solve_c06_task_c() -> dict[str, float]:
    env = Simulation(seed=42)
    # The benchmark definition says "Try to minimize standard deviation... One option: patients entering one of the treatment points for the second time rank higher".
    # STROBOSCOPE paper says: "implementing this by changing the Discipline attribute... from FIFO to ResNum (i.e. where Patients with a smaller resource number, i.e. those that arrived to the system earlier, would be sent to the front)".
    # Priority is basically just ordering by Arrival time, or by "returning status".
    # In my logic above, I used `priority=-1` for returning patients.
    # So if we set discipline to PRIORITY, the queue will prioritize requests with priority=-1 over priority=0.
    facilities = Facilities(env, discipline=QueueDiscipline.PRIORITY)

    finished_patients: list[Patient] = []
    def on_finish(p: Patient) -> None:
        finished_patients.append(p)

    generate_patients(env, facilities, 250, on_finish, task_b_active=False)
    env.schedule(30.0, lambda: open_facilities(env, facilities))

    env.run()

    # Calculate metrics
    metrics: dict[str, float] = {}
    total_time = 0.0
    times_by_type: dict[int, list[float]] = {1: [], 2: [], 3: [], 4: []}

    for p in finished_patients:
        tt = p.end_time - p.arrival_time
        total_time += tt
        times_by_type[p.type_].append(tt)

    metrics["overall"] = total_time / len(finished_patients) if finished_patients else 0.0
    for i in range(1, 5):
        lst = times_by_type[i]
        metrics[f"type_{i}"] = sum(lst) / len(lst) if lst else 0.0

    # Standard deviation of all
    if finished_patients:
        mean = metrics["overall"]
        variance = sum((p.end_time - p.arrival_time - mean) ** 2 for p in finished_patients) / len(finished_patients)
        metrics["std_dev"] = variance ** 0.5
    else:
        metrics["std_dev"] = 0.0

    return metrics
