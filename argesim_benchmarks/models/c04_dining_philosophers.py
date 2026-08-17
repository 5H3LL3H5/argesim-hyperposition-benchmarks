"""ARGESIM C04: Dining Philosophers strategy benchmark.

The original benchmark intentionally leaves the implementation formalism open.
This executable version implements the four strategies used in the published
comparative study: unprotected acquisition, waiter, cleaning/ordered forks, and
put-back.  Every run accounts for the complete simulation horizon, so state
fractions sum to one even after a deadlock.
"""

from __future__ import annotations

import heapq
import math
import random
import statistics
from dataclasses import dataclass
from enum import Enum


class C04Strategy(str, Enum):
    UNPROTECTED = "unprotected"
    WAITER = "waiter"
    CLEANING = "cleaning"
    PUT_BACK = "put-back"


class C04State(str, Enum):
    THINKING = "thinking"
    WAITING = "waiting"
    EATING = "eating"


@dataclass(frozen=True)
class C04Replication:
    strategy: C04Strategy
    seed: int
    horizon: float
    thinking_fraction: float
    waiting_fraction: float
    eating_fraction: float
    meals: int
    deadlocked: bool
    philosopher_meals: tuple[int, ...]
    philosopher_fractions: tuple[tuple[float, float, float], ...]

    def __post_init__(self) -> None:
        total = self.thinking_fraction + self.waiting_fraction + self.eating_fraction
        if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-12):
            raise ValueError("C04 state-time fractions must sum to one")
        if sum(self.philosopher_meals) != self.meals:
            raise ValueError("C04 individual meal counts must equal total meals")
        if len(self.philosopher_meals) != len(self.philosopher_fractions):
            raise ValueError("C04 individual result dimensions must agree")
        if any(
            not math.isclose(sum(fractions), 1.0, rel_tol=0.0, abs_tol=1.0e-12)
            for fractions in self.philosopher_fractions
        ):
            raise ValueError("each C04 philosopher's state fractions must sum to one")

    @property
    def meal_count_range(self) -> int:
        """Return the replication's max-minus-min fairness diagnostic."""

        return max(self.philosopher_meals) - min(self.philosopher_meals)


@dataclass(frozen=True)
class C04Summary:
    strategy: C04Strategy
    replications: int
    mean_thinking_fraction: float
    mean_waiting_fraction: float
    mean_eating_fraction: float
    median_meals: float
    deadlock_probability: float
    mean_meal_count_range: float


class _C04Simulation:
    def __init__(
        self,
        strategy: C04Strategy,
        *,
        seed: int,
        horizon: float,
        philosophers: int,
        retry_delay: float,
        acquisition_delay: float,
    ) -> None:
        self.strategy = strategy
        self.seed = seed
        self.rng = random.Random(seed)
        self.horizon = horizon
        self.size = philosophers
        self.retry_delay = retry_delay
        self.acquisition_delay = acquisition_delay
        self.now = 0.0
        self.sequence = 0
        self.events: list[tuple[float, int, str, int]] = []
        self.state = [C04State.THINKING] * philosophers
        self.changed = [0.0] * philosophers
        self.totals = [
            {state: 0.0 for state in C04State} for _ in range(philosophers)
        ]
        self.fork_owner: list[int | None] = [None] * philosophers
        self.held: list[set[int]] = [set() for _ in range(philosophers)]
        self.waiter_admitted: set[int] = set()
        self.pending_second: set[int] = set()
        self.meals = 0
        self.meal_counts = [0] * philosophers

    def schedule(self, when: float, kind: str, philosopher: int) -> None:
        self.sequence += 1
        heapq.heappush(self.events, (when, self.sequence, kind, philosopher))

    def transition(self, philosopher: int, state: C04State) -> None:
        old = self.state[philosopher]
        self.totals[philosopher][old] += self.now - self.changed[philosopher]
        self.state[philosopher] = state
        self.changed[philosopher] = self.now

    def duration(self) -> float:
        return self.rng.uniform(0.5, 1.5)

    def forks(self, philosopher: int) -> tuple[int, int]:
        return philosopher, (philosopher + 1) % self.size

    def acquire(self, philosopher: int, fork: int) -> bool:
        if self.fork_owner[fork] is None:
            self.fork_owner[fork] = philosopher
            self.held[philosopher].add(fork)
            return True
        return self.fork_owner[fork] == philosopher

    def release_all(self, philosopher: int) -> None:
        for fork in tuple(self.held[philosopher]):
            self.fork_owner[fork] = None
        self.held[philosopher].clear()

    def start_eating(self, philosopher: int) -> None:
        self.transition(philosopher, C04State.EATING)
        self.schedule(self.now + self.duration(), "done", philosopher)

    def try_acquire(self, philosopher: int) -> bool:
        if self.state[philosopher] is not C04State.WAITING:
            return False
        left, right = self.forks(philosopher)

        if self.strategy is C04Strategy.WAITER:
            if philosopher not in self.waiter_admitted:
                if len(self.waiter_admitted) >= self.size - 1:
                    return False
                self.waiter_admitted.add(philosopher)
            if self.fork_owner[left] is None and self.fork_owner[right] is None:
                self.acquire(philosopher, left)
                self.acquire(philosopher, right)
                self.start_eating(philosopher)
                return True
            return False

        if self.strategy is C04Strategy.CLEANING:
            # Clean/ordered transfer abstraction: a philosopher takes both
            # forks atomically in the global fork order.  This preserves the
            # resource-order invariant of the clean-fork protocol.
            first, second = sorted((left, right))
            if self.fork_owner[first] is None and self.fork_owner[second] is None:
                self.acquire(philosopher, first)
                self.acquire(philosopher, second)
                self.start_eating(philosopher)
                return True
            return False

        if self.strategy is C04Strategy.PUT_BACK:
            if not self.held[philosopher] and self.acquire(philosopher, left):
                self.pending_second.add(philosopher)
                self.schedule(
                    self.now + self.acquisition_delay, "second", philosopher
                )
            elif not self.held[philosopher]:
                self.schedule(self.now + self.retry_delay, "retry", philosopher)
            return False

        # Deliberately unsafe left-then-right acquisition.  A philosopher
        # retains the left fork while waiting and can therefore deadlock.
        if not self.held[philosopher] and self.acquire(philosopher, left):
            self.pending_second.add(philosopher)
            self.schedule(self.now + self.acquisition_delay, "second", philosopher)
        elif left in self.held[philosopher] and self.acquire(philosopher, right):
            # Resource release wakes blocked philosophers.  Retaining the
            # first fork must not turn a temporary conflict into an artificial
            # permanent block; only the circular-wait case is a deadlock.
            self.start_eating(philosopher)
            return True
        return False

    def wake_waiters(self) -> None:
        # Stable cyclic scanning avoids depending on set/hash iteration order.
        made_progress = True
        while made_progress:
            made_progress = False
            for philosopher in range(self.size):
                if self.try_acquire(philosopher):
                    made_progress = True

    def run(self) -> C04Replication:
        for philosopher in range(self.size):
            self.schedule(self.duration(), "hungry", philosopher)

        while self.events:
            when, _sequence, kind, philosopher = heapq.heappop(self.events)
            if when > self.horizon:
                break
            self.now = when
            if kind == "hungry":
                if self.state[philosopher] is C04State.THINKING:
                    self.transition(philosopher, C04State.WAITING)
                    self.try_acquire(philosopher)
            elif kind == "retry":
                if self.state[philosopher] is C04State.WAITING:
                    self.try_acquire(philosopher)
            elif kind == "second":
                self.pending_second.discard(philosopher)
                if self.state[philosopher] is not C04State.WAITING:
                    continue
                _left, right = self.forks(philosopher)
                if self.acquire(philosopher, right):
                    self.start_eating(philosopher)
                elif self.strategy is C04Strategy.PUT_BACK:
                    self.release_all(philosopher)
                    self.schedule(self.now + self.retry_delay, "retry", philosopher)
            elif kind == "done":
                if self.state[philosopher] is C04State.EATING:
                    self.meals += 1
                    self.meal_counts[philosopher] += 1
                    self.release_all(philosopher)
                    self.waiter_admitted.discard(philosopher)
                    self.transition(philosopher, C04State.THINKING)
                    self.schedule(self.now + self.duration(), "hungry", philosopher)
                    self.wake_waiters()

        deadlocked = (
            self.strategy is C04Strategy.UNPROTECTED
            and all(state is C04State.WAITING for state in self.state)
            and all(len(forks) == 1 for forks in self.held)
            and all(owner is not None for owner in self.fork_owner)
        )
        self.now = self.horizon
        for philosopher in range(self.size):
            self.transition(philosopher, self.state[philosopher])
        scale = self.horizon * self.size
        fractions = {
            state: sum(total[state] for total in self.totals) / scale
            for state in C04State
        }
        individual_fractions = tuple(
            tuple(self.totals[index][state] / self.horizon for state in C04State)
            for index in range(self.size)
        )
        return C04Replication(
            self.strategy,
            self.seed,
            self.horizon,
            fractions[C04State.THINKING],
            fractions[C04State.WAITING],
            fractions[C04State.EATING],
            self.meals,
            deadlocked,
            tuple(self.meal_counts),
            individual_fractions,
        )


def run_c04(
    strategy: C04Strategy | str,
    *,
    seed: int = 1,
    horizon: float = 100.0,
    philosophers: int = 5,
    retry_delay: float = 1.0,
    acquisition_delay: float = 0.01,
) -> C04Replication:
    """Run one seeded C04 replication."""

    try:
        selected = C04Strategy(strategy)
    except ValueError as exc:
        raise ValueError(f"unknown C04 strategy: {strategy!r}") from exc
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    if not isinstance(philosophers, int) or isinstance(philosophers, bool):
        raise TypeError("philosophers must be an integer")
    if philosophers < 2:
        raise ValueError("at least two philosophers are required")
    if not math.isfinite(horizon) or horizon <= 0.0:
        raise ValueError("horizon must be positive and finite")
    if not math.isfinite(retry_delay) or retry_delay <= 0.0:
        raise ValueError("retry_delay must be positive and finite")
    if not math.isfinite(acquisition_delay) or acquisition_delay <= 0.0:
        raise ValueError("acquisition_delay must be positive and finite")
    return _C04Simulation(
        selected,
        seed=seed,
        horizon=horizon,
        philosophers=philosophers,
        retry_delay=retry_delay,
        acquisition_delay=acquisition_delay,
    ).run()


def c04_compare_strategies(
    *, replications: int = 100, seed: int = 1, horizon: float = 100.0
) -> tuple[C04Summary, ...]:
    """Compare all published strategies over common-random-number seeds."""

    if not isinstance(replications, int) or isinstance(replications, bool):
        raise TypeError("replications must be an integer")
    if replications <= 0:
        raise ValueError("replications must be positive")
    summaries = []
    for strategy in C04Strategy:
        runs = tuple(
            run_c04(strategy, seed=seed + index, horizon=horizon)
            for index in range(replications)
        )
        summaries.append(
            C04Summary(
                strategy,
                replications,
                statistics.fmean(run.thinking_fraction for run in runs),
                statistics.fmean(run.waiting_fraction for run in runs),
                statistics.fmean(run.eating_fraction for run in runs),
                float(statistics.median(run.meals for run in runs)),
                statistics.fmean(float(run.deadlocked) for run in runs),
                statistics.fmean(run.meal_count_range for run in runs),
            )
        )
    return tuple(summaries)
