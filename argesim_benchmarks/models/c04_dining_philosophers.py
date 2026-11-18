"""ARGESIM C04: Dining Philosophers strategy benchmark.

The original benchmark intentionally leaves the implementation formalism open.
The policies cover atomic Petri-style acquisition, a hungry state, dirty-fork
cleaning and neighbour request tokens, as well as unsafe and put-back variants.
Cleaning/request delays and the two adversarial holding policies are explicit
modelling choices; the original comparison leaves these timings open.
Every run accounts for the complete horizon, including a deadlock.
"""

from __future__ import annotations

import heapq
import math
import random
import statistics
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum


class C04Strategy(str, Enum):
    ATOMIC = "atomic"
    UNPROTECTED = "unprotected"
    WAITER = "waiter"
    CLEANING = "cleaning"
    REQUESTS = "requests"
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
    completed_cleanings: int = 0
    request_tokens_sent: int = 0

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
        cleaning_delay: float,
        request_delay: float,
        initial_thinking_times: tuple[float, ...] | None,
        conspiracy: str,
        conspirators: tuple[int, ...],
        victims: tuple[int, ...],
    ) -> None:
        self.strategy = strategy
        self.seed = seed
        self.rng = random.Random(seed)
        self.horizon = horizon
        self.size = philosophers
        self.retry_delay = retry_delay
        self.acquisition_delay = acquisition_delay
        self.cleaning_delay = cleaning_delay
        self.request_delay = request_delay
        self.initial_thinking_times = initial_thinking_times
        self.conspiracy = conspiracy
        self.conspirators = frozenset(conspirators)
        self.victims = frozenset(victims)
        self.now = 0.0
        self.sequence = 0
        self.events: list[tuple[float, int, str, int]] = []
        self.state = [C04State.THINKING] * philosophers
        self.changed = [0.0] * philosophers
        self.totals = [{state: 0.0 for state in C04State} for _ in range(philosophers)]
        self.fork_owner: list[int | None] = [None] * philosophers
        self.held: list[set[int]] = [set() for _ in range(philosophers)]
        self.waiter_admitted: set[int] = set()
        self.pending_second: set[int] = set()
        self.meals = 0
        self.meal_counts = [0] * philosophers
        self.fork_clean = [True] * philosophers
        self.cleaning_forks: set[int] = set()
        self.fork_requests: list[dict[int, float]] = [{} for _ in range(philosophers)]
        self.completed_cleanings = 0
        self.request_tokens_sent = 0

    @property
    def uses_cleaning(self) -> bool:
        return self.strategy in {C04Strategy.CLEANING, C04Strategy.REQUESTS}

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
        if self.uses_cleaning and not self.fork_clean[fork]:
            return False
        if self.fork_owner[fork] is None:
            self.fork_owner[fork] = philosopher
            self.held[philosopher].add(fork)
            return True
        return self.fork_owner[fork] == philosopher

    def release_all(self, philosopher: int) -> None:
        retained: set[int] = set()
        if philosopher in self.conspirators:
            if self.conspiracy == "hoard":
                retained = set(self.held[philosopher])
            elif self.conspiracy == "targeted-hold":
                shared = {
                    fork for victim in self.victims for fork in self.forks(victim)
                }
                retained = self.held[philosopher] & shared
        for fork in tuple(self.held[philosopher]):
            if fork not in retained:
                self.fork_owner[fork] = None
                self.held[philosopher].remove(fork)
            if self.uses_cleaning:
                self.fork_clean[fork] = False
                if fork not in self.cleaning_forks:
                    self.cleaning_forks.add(fork)
                    self.schedule(self.now + self.cleaning_delay, "clean", fork)

    def start_eating(self, philosopher: int) -> None:
        for requests in self.fork_requests:
            requests.pop(philosopher, None)
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

        if self.strategy in {
            C04Strategy.ATOMIC,
            C04Strategy.CLEANING,
            C04Strategy.REQUESTS,
        }:
            # Atomic acquisition is the initial Petri-style model. Cleaning
            # adds actual unavailable dirty forks; requests add neighbour
            # priority, ordered by age and philosopher ID to avoid cycles.
            if any(
                self.fork_owner[fork] not in (None, philosopher)
                for fork in (left, right)
            ):
                return False
            if self.uses_cleaning and any(
                not self.fork_clean[fork] for fork in (left, right)
            ):
                return False
            if self.strategy is C04Strategy.REQUESTS:
                for fork in (left, right):
                    requests = self.fork_requests[fork]
                    if requests:
                        preferred = min(requests, key=lambda p: (requests[p], p))
                        if preferred != philosopher:
                            return False
            if self.acquire(philosopher, left) and self.acquire(philosopher, right):
                self.start_eating(philosopher)
                return True
            return False

        if self.strategy is C04Strategy.PUT_BACK:
            if not self.held[philosopher] and self.acquire(philosopher, left):
                self.pending_second.add(philosopher)
                self.schedule(self.now + self.acquisition_delay, "second", philosopher)
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
            delay = (
                self.duration()
                if self.initial_thinking_times is None
                else self.initial_thinking_times[philosopher]
            )
            self.schedule(delay, "hungry", philosopher)

        future_event_pending = False
        while self.events:
            when, _sequence, kind, philosopher = heapq.heappop(self.events)
            if when > self.horizon:
                future_event_pending = True
                break
            self.now = when
            if kind == "hungry":
                if self.state[philosopher] is C04State.THINKING:
                    self.transition(philosopher, C04State.WAITING)
                    if self.strategy is C04Strategy.REQUESTS:
                        self.schedule(
                            self.now + self.request_delay, "request", philosopher
                        )
                    self.try_acquire(philosopher)
            elif kind == "clean":
                self.fork_clean[philosopher] = True
                self.cleaning_forks.remove(philosopher)
                self.completed_cleanings += 1
                self.wake_waiters()
            elif kind == "request":
                if self.state[philosopher] is C04State.WAITING:
                    for fork in self.forks(philosopher):
                        self.fork_requests[fork][philosopher] = self.now
                        self.request_tokens_sent += 1
                    self.wake_waiters()
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
            elif kind == "done" and self.state[philosopher] is C04State.EATING:
                self.meals += 1
                self.meal_counts[philosopher] += 1
                self.release_all(philosopher)
                self.waiter_admitted.discard(philosopher)
                self.transition(philosopher, C04State.THINKING)
                self.schedule(self.now + self.duration(), "hungry", philosopher)
                self.wake_waiters()

        # A conspiracy may also deadlock a nominally protected policy.
        # Pending cleaning/request/retry events can still enable progress and
        # must not be mistaken for a permanent block at the reporting horizon.
        deadlocked = (
            all(state is C04State.WAITING for state in self.state)
            and not self.events
            and not future_event_pending
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
            self.completed_cleanings,
            self.request_tokens_sent,
        )


def run_c04(
    strategy: C04Strategy | str,
    *,
    seed: int = 1,
    horizon: float = 100.0,
    philosophers: int = 5,
    retry_delay: float = 1.0,
    acquisition_delay: float = 0.01,
    cleaning_delay: float = 0.1,
    request_delay: float = 1.0,
    initial_thinking_times: Sequence[float] | None = None,
    conspiracy: str = "none",
    conspirators: Sequence[int] = (),
    victims: Sequence[int] = (),
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
    for name, value in (
        ("cleaning_delay", cleaning_delay),
        ("request_delay", request_delay),
    ):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"{name} must be positive and finite")
    thinking_times = (
        None if initial_thinking_times is None else tuple(initial_thinking_times)
    )
    if thinking_times is not None and (
        len(thinking_times) != philosophers
        or any(not math.isfinite(t) or t < 0.0 for t in thinking_times)
    ):
        raise ValueError(
            "initial_thinking_times must contain one finite non-negative delay per philosopher"
        )
    allies, targets = tuple(conspirators), tuple(victims)
    for group in (allies, targets):
        if len(set(group)) != len(group) or any(
            isinstance(p, bool) or not isinstance(p, int) or not 0 <= p < philosophers
            for p in group
        ):
            raise ValueError(
                "conspiracy groups must contain distinct valid philosopher IDs"
            )
    if set(allies) & set(targets):
        raise ValueError("conspirators and victims must be disjoint")
    if conspiracy not in {"none", "hoard", "targeted-hold"}:
        raise ValueError("unknown conspiracy policy")
    if conspiracy != "none" and (
        not allies
        or not targets
        or selected
        not in {C04Strategy.ATOMIC, C04Strategy.CLEANING, C04Strategy.REQUESTS}
    ):
        raise ValueError(
            "conspiracy requires atomic/cleaning/request policy and nonempty groups"
        )
    if conspiracy == "none" and (allies or targets):
        raise ValueError("conspiracy groups require an active conspiracy policy")
    return _C04Simulation(
        selected,
        seed=seed,
        horizon=horizon,
        philosophers=philosophers,
        retry_delay=retry_delay,
        acquisition_delay=acquisition_delay,
        cleaning_delay=cleaning_delay,
        request_delay=request_delay,
        initial_thinking_times=thinking_times,
        conspiracy=conspiracy,
        conspirators=allies,
        victims=targets,
    ).run()


def c04_refinement_study(
    *, seed: int = 1, horizon: float = 100.0
) -> dict[str, C04Replication]:
    """Run the definition's refinements and explicit adversarial experiments.

    Simultaneous initial hunger makes the unsafe circular wait reproducible.
    Conspiracies begin with philosopher 0 eating before its intended victims;
    they are deliberately unfair model variants, not protective algorithms.
    """
    results = {
        "atomic": run_c04("atomic", seed=seed, horizon=horizon),
        "hungry-deadlock": run_c04(
            "unprotected",
            seed=seed,
            horizon=horizon,
            initial_thinking_times=(0.0,) * 5,
        ),
        "cleaning": run_c04("cleaning", seed=seed, horizon=horizon),
        "neighbour-requests": run_c04("requests", seed=seed, horizon=horizon),
    }
    for policy in ("hoard", "targeted-hold"):
        results[policy] = run_c04(
            "cleaning",
            seed=seed,
            horizon=horizon,
            initial_thinking_times=(0.0, 2.0, 2.0, 2.0, 2.0),
            conspiracy=policy,
            conspirators=(0,),
            victims=(1,),
        )
    return results


def c04_compare_strategies(
    *, replications: int = 100, seed: int = 1, horizon: float = 100.0
) -> tuple[C04Summary, ...]:
    """Compare all implemented strategies over matched replication seeds.

    Different event histories consume different draws; matched seeds alone
    do not establish common-random-number alignment of each activity.
    """

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
