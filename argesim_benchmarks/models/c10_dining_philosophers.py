"""ARGESIM C10: Dining Philosophers II.

The benchmark investigates concurrent access and deadlock detection in a discrete
event simulation. Five philosophers share five chopsticks. Each philosopher
needs two chopsticks to eat (the one to their left and the one to their right).
They follow this strategy:
1. First, pick up the chopstick to the left.
2. Then, pick up the chopstick to the right.

Time for thinking and eating follows a discrete uniform distribution in the
interval [1, 10].
All philosophers start with a thinking period.

Simultaneous access rule: If a hungry philosopher wants to take his left
chopstick at the exact same time as the philosopher on his left wants to take
his right chopstick (which is the same chopstick), the philosopher on the right
gets the chopstick first. The philosopher on the left must wait.
Deadlock: Occurs when all 5 philosophers are holding their left chopstick and
waiting for the right chopstick. The simulation terminates.
"""

from __future__ import annotations

import heapq
import random
import statistics
from dataclasses import dataclass, field
from enum import Enum


class PhilosopherState(Enum):
    THINKING = "thinking"
    WAITING_LEFT = "waiting_left"
    WAITING_RIGHT = "waiting_right"
    EATING = "eating"


@dataclass(order=True)
class _Event:
    time: int
    sequence: int
    philosopher_id: int = field(compare=False)
    action: str = field(compare=False)


@dataclass(frozen=True)
class TaskAResult:
    termination_time: int
    avg_thinking_time_per_philosopher: tuple[float, ...]
    std_thinking_time_per_philosopher: tuple[float, ...]
    avg_waiting_time_per_philosopher: tuple[float, ...]
    std_waiting_time_per_philosopher: tuple[float, ...]
    avg_eating_time_per_philosopher: tuple[float, ...]
    std_eating_time_per_philosopher: tuple[float, ...]
    overall_avg_thinking_time: float
    overall_std_thinking_time: float
    overall_avg_waiting_time: float
    overall_std_waiting_time: float
    overall_avg_eating_time: float
    overall_std_eating_time: float
    chopstick_utilisation: tuple[float, ...]
    overall_chopstick_utilisation: float


@dataclass(frozen=True)
class TaskBResult:
    runs_count: int
    max_termination_time: int
    min_termination_time: int


def run_c10_simulation(seed: int | None = None) -> TaskAResult:
    """Run a single instance of the C10 simulation until deadlock."""
    rng = random.Random(seed)

    # 5 philosophers: 0, 1, 2, 3, 4
    # Chopsticks: chopstick i is to the left of philosopher i.
    # Therefore, philosopher i needs chopstick i (left) and chopstick (i+1)%5 (right).
    # Wait, the problem says: "the chopstick to the left of his bowl" and "chopstick to the right".
    # Let's define: Left chopstick for philosopher i is i.
    # Right chopstick for philosopher i is (i+1)%5.

    # Simultaneous access rule:
    # "the philosopher sitting on the right gets the chopstick (to the left of his bowl) first and the philosopher to his left must wait"
    # In our numbering, if philosopher i and philosopher i+1 want the same chopstick at the same time:
    # Philosopher i wants his RIGHT chopstick (which is (i+1)%5).
    # Philosopher i+1 wants his LEFT chopstick (which is (i+1)%5).
    # "philosopher sitting on the right" is philosopher i+1 (because he is to the right of philosopher i if we go counter-clockwise? Let's check.)
    # The rule says: "one of the hungry philosophers (having already got hold of the chopstick to the left of his own bowl) wants to take the chopstick to the right of his bowl at exactly the same time instant as his right neighbour (who is also hungry) is about to pick up the chopstick to the left of his bowl (which is the chopstick to the right of his left neighbour's bowl)."
    # Okay, so philosopher A wants right chopstick, philosopher B (right neighbour of A) wants left chopstick.
    # A's right chopstick = B's left chopstick.
    # The rule says: "the philosopher sitting on the right gets the chopstick (to the left of his bowl) first".
    # So B gets it first.
    # That means when allocating chopsticks, if multiple philosophers want the same chopstick at the same time,
    # the one who wants it as their LEFT chopstick has higher priority than the one who wants it as their RIGHT chopstick.
    # Left chopstick request > Right chopstick request.

    num_philosophers = 5

    chopstick_free = [True] * num_philosophers

    # Track states
    states = [PhilosopherState.THINKING] * num_philosophers

    # Time tracking
    current_time = 0

    # Statistics tracking
    thinking_times = [[] for _ in range(num_philosophers)]
    waiting_times = [[] for _ in range(num_philosophers)]
    eating_times = [[] for _ in range(num_philosophers)]
    chopstick_usage_time = [0] * num_philosophers

    state_start_time = [0] * num_philosophers

    queue: list[_Event] = []
    sequence = 0

    def schedule(time: int, p_id: int, action: str):
        nonlocal sequence
        heapq.heappush(queue, _Event(time, sequence, p_id, action))
        sequence += 1

    def transition(p_id: int, new_state: PhilosopherState):
        now = current_time
        old_state = states[p_id]
        duration = now - state_start_time[p_id]
        if duration > 0:
            if old_state == PhilosopherState.THINKING:
                thinking_times[p_id].append(duration)
            elif old_state in (PhilosopherState.WAITING_LEFT, PhilosopherState.WAITING_RIGHT):
                waiting_times[p_id].append(duration)
            elif old_state == PhilosopherState.EATING:
                eating_times[p_id].append(duration)
        states[p_id] = new_state
        state_start_time[p_id] = now

    for i in range(num_philosophers):
        # All 5 philosophers start with a thinking period
        t_think = rng.randint(1, 10)
        schedule(t_think, i, "hungry")

    while queue:
        # We need to process all events at the current time together to handle simultaneous access.
        current_time = queue[0].time

        events_now = []
        while queue and queue[0].time == current_time:
            events_now.append(heapq.heappop(queue))

        for ev in events_now:
            if ev.action == "hungry":
                transition(ev.philosopher_id, PhilosopherState.WAITING_LEFT)
            elif ev.action == "done_eating":
                p_id = ev.philosopher_id
                left_c = p_id
                right_c = (p_id + 1) % 5
                chopstick_free[left_c] = True
                chopstick_free[right_c] = True

                t_think = rng.randint(1, 10)
                transition(p_id, PhilosopherState.THINKING)
                schedule(current_time + t_think, p_id, "hungry")

        # Now, try to allocate chopsticks.
        # To handle priority, we iterate over all chopsticks.
        # For each chopstick, we see who wants it.
        # Philosopher i wants chopstick i (left) if in state WAITING_LEFT.
        # Philosopher i-1 wants chopstick i (right) if in state WAITING_RIGHT.
        # Note: Philosopher wants RIGHT chopstick if they are in WAITING_RIGHT.
        # Their right chopstick is (p_id + 1) % 5. So if chopstick is C, then p_id is (C - 1) % 5.

        allocation_changed = True
        while allocation_changed:
            allocation_changed = False
            for c in range(num_philosophers):
                if not chopstick_free[c]:
                    continue

                left_requester = c # Philosopher c wants chopstick c as their left chopstick
                right_requester = (c - 1) % 5 # Philosopher c-1 wants chopstick c as their right chopstick

                req_left = (states[left_requester] == PhilosopherState.WAITING_LEFT)
                req_right = (states[right_requester] == PhilosopherState.WAITING_RIGHT)

                if req_left and req_right:
                    # Simultaneous access conflict! Left requester (who wants it as LEFT chopstick) wins.
                    # This corresponds to "philosopher sitting on the right gets the chopstick (to the left of his bowl) first".
                    chopstick_free[c] = False
                    # We just allocated a left chopstick to left_requester
                    # Now left_requester is waiting for right chopstick
                    states[left_requester] = PhilosopherState.WAITING_RIGHT # Still waiting, but for right chopstick now
                    # We do not call transition because they are still conceptually 'waiting'.
                    # But if we want to track waiting_left vs waiting_right times, we could.
                    # The problem asks for "waiting" times together, so we just update the state.
                    allocation_changed = True
                elif req_left:
                    chopstick_free[c] = False
                    states[left_requester] = PhilosopherState.WAITING_RIGHT
                    allocation_changed = True
                elif req_right:
                    chopstick_free[c] = False
                    # right_requester gets their right chopstick! Now they have both.
                    transition(right_requester, PhilosopherState.EATING)
                    t_eat = rng.randint(1, 10)
                    schedule(current_time + t_eat, right_requester, "done_eating")
                    allocation_changed = True

        # Check deadlock: All 5 are waiting for their right chopstick.
        if all(s == PhilosopherState.WAITING_RIGHT for s in states):
            # Deadlock detected.
            # End all states to record their current duration.
            for i in range(num_philosophers):
                transition(i, PhilosopherState.WAITING_RIGHT) # This records the final waiting time
            break

        # Update chopstick usage times.
        # But wait, chopstick usage is continuous over time.
        # Actually, it's easier to just compute it at the end if we just add (next_time - current_time) for each used chopstick.
        if queue:
            next_time = queue[0].time
            duration = next_time - current_time
            for c in range(num_philosophers):
                if not chopstick_free[c]:
                    chopstick_usage_time[c] += duration

    # Compute statistics
    def safe_mean(lst):
        return float(statistics.mean(lst)) if lst else 0.0

    def safe_stdev(lst):
        return float(statistics.stdev(lst)) if len(lst) > 1 else 0.0

    avg_thinking = tuple(safe_mean(thinking_times[i]) for i in range(num_philosophers))
    std_thinking = tuple(safe_stdev(thinking_times[i]) for i in range(num_philosophers))
    avg_waiting = tuple(safe_mean(waiting_times[i]) for i in range(num_philosophers))
    std_waiting = tuple(safe_stdev(waiting_times[i]) for i in range(num_philosophers))
    avg_eating = tuple(safe_mean(eating_times[i]) for i in range(num_philosophers))
    std_eating = tuple(safe_stdev(eating_times[i]) for i in range(num_philosophers))

    all_thinking = [t for sublist in thinking_times for t in sublist]
    all_waiting = [t for sublist in waiting_times for t in sublist]
    all_eating = [t for sublist in eating_times for t in sublist]

    overall_avg_thinking = safe_mean(all_thinking)
    overall_std_thinking = safe_stdev(all_thinking)
    overall_avg_waiting = safe_mean(all_waiting)
    overall_std_waiting = safe_stdev(all_waiting)
    overall_avg_eating = safe_mean(all_eating)
    overall_std_eating = safe_stdev(all_eating)

    termination_time = current_time

    chopstick_utilisation = tuple(chopstick_usage_time[i] / termination_time if termination_time > 0 else 0.0 for i in range(num_philosophers))
    overall_chopstick_utilisation = sum(chopstick_usage_time) / (num_philosophers * termination_time) if termination_time > 0 else 0.0

    return TaskAResult(
        termination_time=termination_time,
        avg_thinking_time_per_philosopher=avg_thinking,
        std_thinking_time_per_philosopher=std_thinking,
        avg_waiting_time_per_philosopher=avg_waiting,
        std_waiting_time_per_philosopher=std_waiting,
        avg_eating_time_per_philosopher=avg_eating,
        std_eating_time_per_philosopher=std_eating,
        overall_avg_thinking_time=overall_avg_thinking,
        overall_std_thinking_time=overall_std_thinking,
        overall_avg_waiting_time=overall_avg_waiting,
        overall_std_waiting_time=overall_std_waiting,
        overall_avg_eating_time=overall_avg_eating,
        overall_std_eating_time=overall_std_eating,
        chopstick_utilisation=chopstick_utilisation,
        overall_chopstick_utilisation=overall_chopstick_utilisation,
    )


def c10_task_a() -> TaskAResult:
    """Task i: Single simulation run until a deadlock is reached."""
    # We just run one simulation with an arbitrary seed (e.g. 42 or None).
    # Using 42 for reproducibility.
    return run_c10_simulation(seed=42)


def c10_task_b(runs: int = 50) -> TaskBResult:
    """Task ii: Performing at least 50 simulation runs (ending in a deadlock)."""
    termination_times = []
    for i in range(runs):
        res = run_c10_simulation(seed=i)
        termination_times.append(res.termination_time)

    return TaskBResult(
        runs_count=runs,
        max_termination_time=max(termination_times),
        min_termination_time=min(termination_times),
    )
