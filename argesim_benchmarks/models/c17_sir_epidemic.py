"""ARGESIM C17R: SIR-type Epidemic with Cellular Automata and Ordinary Differential Equations.

The equations, parameters, initial values and tasks follow the
official C17R definition. State order is ``(S, I, R)``.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from ..hybrid import (
    HybridEventRecord,
    HybridMode,
    HybridReset,
    HybridResult,
    StateEvent,
    simulate_hybrid,
)
from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..runtime import solve_ivp
from nsa_devs.hypertime import HyperTime

C17_INITIAL_STATE: Vector = (9500.0, 500.0, 0.0)


@dataclass(frozen=True)
class C17Parameters:
    """Parameters in the notation of the official C17R definition."""

    n: float = 10000.0
    c: float = 4.0
    alpha: float = 0.1
    beta: float = 0.1

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(value)
            for value in (self.n, self.c, self.alpha, self.beta)
        ):
            raise ValueError("C17R parameters must be finite")
        if self.n <= 0.0:
            raise ValueError("Population size n must be strictly positive")
        if self.c < 0.0 or self.alpha < 0.0 or self.beta < 0.0:
            raise ValueError("c, alpha, and beta must be non-negative")
        if self.alpha >= 1.0 or self.beta >= 1.0:
            raise ValueError("alpha and beta must be strictly less than 1.0")


_C17_DEFAULT_PARAMETERS = C17Parameters()


def c17_rhs(parameters: C17Parameters = _C17_DEFAULT_PARAMETERS) -> Rhs:
    """Return the official three-state ODE model."""
    gamma = -(parameters.c / parameters.n) * math.log(1.0 - parameters.alpha)
    delta = -math.log(1.0 - parameters.beta)

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        susceptible, infected, _recovered = state
        infection_rate = gamma * susceptible * infected
        recovery_rate = delta * infected
        return (
            -infection_rate,
            infection_rate - recovery_rate,
            recovery_rate,
        )

    return rhs


def c17_problem(
    *,
    parameters: C17Parameters = _C17_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C17_INITIAL_STATE,
    t_bound: float = 100.0,
) -> InitialValueProblem:
    """Build the C17R initial-value problem."""

    state = tuple(float(value) for value in initial_state)
    if len(state) != 3 or any(not math.isfinite(value) for value in state):
        raise ValueError("C17R initial_state must contain three finite values")
    if any(value < 0.0 for value in state):
        raise ValueError("C17R populations must be non-negative")
    if not math.isclose(sum(state), parameters.n, rel_tol=1.0e-12, abs_tol=1.0e-9):
        raise ValueError("C17R initial populations must sum to n")
    return InitialValueProblem(
        c17_rhs(parameters),
        0.0,
        state,
        t_bound,
        name="ARGESIM-C17R-sir-epidemic",
        autonomous=True,
    )


def solve_c17(
    method: str = "rk45",
    *,
    parameters: C17Parameters = _C17_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C17_INITIAL_STATE,
    t_bound: float = 100.0,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Solve C17R with an explicitly selected, auditable backend."""
    problem = c17_problem(
        parameters=parameters,
        initial_state=initial_state,
        t_bound=t_bound,
    )
    defaults = {
        "euler": {"step": 0.1},
        "rk4": {"step": 0.1},
        "rk45": {"rtol": 1.0e-8, "atol": 1.0e-11, "max_step": 1.0},
        "qss1": {"quantum": (1.0, 1.0, 1.0)},
        "qss2": {"quantum": (1.0, 1.0, 1.0)},
    }
    return solve_ivp(problem, method, options=options, defaults=defaults)


# --- Cellular automaton and intervention experiments ---


class C17Movement(str, Enum):
    FHP_I = "fhp-i"
    RANDOM = "random"


class C17HardMeasure(str, Enum):
    VACCINATION = "vaccination"
    QUARANTINE = "quarantine"


class C17SoftParameter(str, Enum):
    CONTACTS = "contacts"
    INFECTION = "alpha"
    RECOVERY = "beta"


@dataclass(frozen=True)
class C17Intervention:
    """One threshold-triggered C17R intervention specification."""

    threshold_fraction: float
    soft_factor: float | None = None
    soft_parameter: C17SoftParameter = C17SoftParameter.INFECTION
    duration: int = 0
    hard_measure: C17HardMeasure | None = None
    hard_fraction: float = 0.0
    repeated: bool = False
    profile: str = "linear"
    selection: str = "random"

    def __post_init__(self) -> None:
        if not 0.0 <= self.threshold_fraction <= 1.0:
            raise ValueError("threshold_fraction must lie in [0, 1]")
        if self.soft_factor is not None and not 0.0 <= self.soft_factor <= 1.0:
            raise ValueError("soft_factor must lie in [0, 1]")
        try:
            object.__setattr__(
                self,
                "soft_parameter",
                C17SoftParameter(self.soft_parameter),
            )
        except ValueError as exc:
            raise ValueError("unknown C17 soft parameter") from exc
        if self.hard_measure is not None:
            try:
                object.__setattr__(
                    self,
                    "hard_measure",
                    C17HardMeasure(self.hard_measure),
                )
            except ValueError as exc:
                raise ValueError("unknown C17 hard measure") from exc
        if (
            not isinstance(self.duration, int)
            or isinstance(self.duration, bool)
            or self.duration < 0
        ):
            raise ValueError("duration must be a non-negative integer")
        if not 0.0 <= self.hard_fraction <= 1.0:
            raise ValueError("hard_fraction must lie in [0, 1]")
        if self.profile not in {"linear", "smoothstep", "constant"}:
            raise ValueError("profile must be linear, smoothstep, or constant")
        if self.selection not in {"random", "center", "interface"}:
            raise ValueError("selection must be random, center, or interface")
        if self.soft_factor is None and self.hard_measure is None:
            raise ValueError("an intervention needs a soft or hard measure")


@dataclass(frozen=True)
class C17InterventionEvent:
    step: int
    kind: str
    affected: int


@dataclass(frozen=True)
class C17CAResult:
    movement: C17Movement
    lattice_size: int
    contact_rate: float
    susceptible: tuple[int, ...]
    infected: tuple[int, ...]
    recovered: tuple[int, ...]
    interventions: tuple[C17InterventionEvent, ...]

    @property
    def population(self) -> int:
        return self.susceptible[0] + self.infected[0] + self.recovered[0]


@dataclass(frozen=True)
class C17Comparison:
    times: tuple[float, ...]
    ode: tuple[Vector, ...]
    ca_mean: tuple[Vector, ...]
    root_mean_square_error: float


@dataclass(frozen=True)
class C17ParameterCase:
    """One Task-1 ODE/CA parameter-comparison case."""

    label: str
    parameters: C17Parameters
    initial_state: tuple[int, int, int]
    comparison: C17Comparison


def c17_lattice_size(population: int, contacts: float) -> int:
    """Identify the hexagonal n-by-n lattice from N and desired C."""

    if not isinstance(population, int) or isinstance(population, bool) or population < 2:
        raise ValueError("population must be an integer >= 2")
    if not math.isfinite(contacts) or contacts <= 0.0:
        raise ValueError("contacts must be positive and finite")
    estimate = math.sqrt((5.0 * (population - 1) + contacts) / (6.0 * contacts))
    size = max(1, int(math.floor(estimate + 0.5)))
    while 6 * size * size < population:
        size += 1
    return size


def c17_contact_rate(population: int, lattice_size: int) -> float:
    """Return C = 5(N-1)/(6n^2-1) from the official CA identification."""

    if population < 2 or lattice_size < 1 or population > 6 * lattice_size * lattice_size:
        raise ValueError("population/lattice combination is not a valid FHP lattice")
    return 5.0 * (population - 1) / (6.0 * lattice_size * lattice_size - 1.0)


_HEX_DIRECTIONS = ((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))


def _c17_select(
    candidates: Sequence[int],
    count: int,
    cells: Sequence[int],
    lattice_size: int,
    selection: str,
    infected_cells: set[int],
    rng: random.Random,
) -> list[int]:
    choices = list(candidates)
    if count <= 0:
        return []
    if selection == "random":
        rng.shuffle(choices)
    elif selection == "center":
        center = (lattice_size - 1) / 2.0
        choices.sort(
            key=lambda index: (
                (cells[index] % lattice_size - center) ** 2
                + (cells[index] // lattice_size - center) ** 2,
                index,
            )
        )
    else:
        # Interface selection prioritizes cells adjacent to an infected cell.
        def distance(index: int) -> tuple[int, int]:
            cell = cells[index]
            q, r = cell % lattice_size, cell // lattice_size
            adjacent = any(
                ((q + dq) % lattice_size) + lattice_size * ((r + dr) % lattice_size)
                in infected_cells
                for dq, dr in _HEX_DIRECTIONS
            )
            return (0 if adjacent else 1, index)

        choices.sort(key=distance)
    return choices[:count]


def _c17_soft_scale(elapsed: int, duration: int, factor: float, profile: str) -> float:
    if duration == 0 or profile == "constant":
        return factor
    phase = min(1.0, max(0.0, elapsed / duration))
    # Ramp from baseline to the persistent reduced value.
    if profile == "smoothstep":
        phase = phase * phase * (3.0 - 2.0 * phase)
    return 1.0 - (1.0 - factor) * phase


def _c17_continuous_soft_scale(
    time_value: float,
    trigger_time: float | None,
    intervention: C17Intervention,
) -> float:
    if trigger_time is None or intervention.soft_factor is None:
        return 1.0
    elapsed = max(0.0, time_value - trigger_time)
    if intervention.duration == 0 or intervention.profile == "constant":
        return intervention.soft_factor
    phase = min(1.0, elapsed / intervention.duration)
    if intervention.profile == "smoothstep":
        phase = phase * phase * (3.0 - 2.0 * phase)
    return 1.0 - (1.0 - intervention.soft_factor) * phase


def simulate_c17_ode_intervention(
    intervention: C17Intervention,
    *,
    parameters: C17Parameters = _C17_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C17_INITIAL_STATE,
    t_bound: float = 100.0,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
) -> HybridResult:
    """Run Task 2 on the cumulative ODE model with shared event semantics."""

    state0 = tuple(float(value) for value in initial_state)
    # Reuse the benchmark's complete state and time validation.
    c17_problem(
        parameters=parameters,
        initial_state=state0,
        t_bound=t_bound,
    )
    trigger_time: float | None = None
    hard_applications = 0

    def controlled_rhs(time_value: float, state: Sequence[float]) -> Vector:
        scale = _c17_continuous_soft_scale(
            time_value,
            trigger_time,
            intervention,
        )
        contacts = parameters.c
        alpha = parameters.alpha
        beta = parameters.beta
        if intervention.soft_factor is not None:
            if intervention.soft_parameter is C17SoftParameter.CONTACTS:
                contacts *= scale
            elif intervention.soft_parameter is C17SoftParameter.INFECTION:
                alpha *= scale
            else:
                beta *= scale
        gamma = -(contacts / parameters.n) * math.log(1.0 - alpha)
        delta = -math.log(1.0 - beta)
        susceptible, infected, _recovered = state
        infections = gamma * susceptible * infected
        recoveries = delta * infected
        return -infections, infections - recoveries, recoveries

    threshold = intervention.threshold_fraction * parameters.n

    def guard(_time: float, state: Sequence[float]) -> float:
        return state[1] - threshold

    def below_guard(_time: float, state: Sequence[float]) -> float:
        return state[1] - threshold

    def apply_threshold(time_value: float, state: Sequence[float]) -> HybridReset:
        nonlocal trigger_time, hard_applications
        if trigger_time is None and intervention.soft_factor is not None:
            trigger_time = time_value
        susceptible, infected, recovered = (float(value) for value in state)
        apply_hard_measure = intervention.repeated or hard_applications == 0
        if intervention.hard_measure is not None and apply_hard_measure:
            if intervention.hard_measure is C17HardMeasure.VACCINATION:
                affected = intervention.hard_fraction * susceptible
                susceptible -= affected
                recovered += affected
                hard_applications += 1
            else:
                affected = intervention.hard_fraction * infected
                infected -= affected
                recovered += affected
                hard_applications += 1
        after = (susceptible, infected, recovered)
        if not intervention.repeated or intervention.hard_measure is None:
            next_mode = "controlled"
        elif infected < threshold:
            next_mode = "armed"
        else:
            next_mode = "wait-below"
        return HybridReset(after, mode=next_mode)

    def rearm(_time: float, state: Sequence[float]) -> HybridReset:
        return HybridReset(tuple(state), mode="armed")

    threshold_event = StateEvent(
        "threshold-intervention",
        guard,
        apply_threshold,
        "controlled",
        direction=1,
    )
    rearm_event = StateEvent(
        "threshold-rearm",
        below_guard,
        rearm,
        "armed",
        direction=-1,
    )
    modes = {
        "armed": HybridMode("armed", controlled_rhs, (threshold_event,)),
        "controlled": HybridMode("controlled", controlled_rhs),
        "wait-below": HybridMode("wait-below", controlled_rhs, (rearm_event,)),
    }
    defaults = {
        "euler": {"step": 0.1},
        "rk4": {"step": 0.1},
        "rk45": {"rtol": 1.0e-8, "atol": 1.0e-11, "max_step": 1.0},
        "qss1": {"quantum": (1.0, 1.0, 1.0)},
        "qss2": {"quantum": (1.0, 1.0, 1.0)},
    }

    initial_mode = "armed"
    initial_event: HybridEventRecord | None = None
    simulation_state = state0
    if state0[1] >= threshold:
        reset = apply_threshold(0.0, state0)
        simulation_state = tuple(float(value) for value in reset.state)
        initial_mode = reset.mode or "controlled"
        initial_event = HybridEventRecord(
            "threshold-intervention",
            HyperTime.at(0.0, 1),
            "armed",
            initial_mode,
            state0,
            simulation_state,
        )

    result = simulate_hybrid(
        modes,
        initial_mode=initial_mode,
        initial_state=simulation_state,
        t_bound=t_bound,
        method=method,
        solver_options=options,
        solver_defaults=defaults,
    )
    if initial_event is None:
        return result
    return HybridResult(
        result.method,
        (0.0,) + result.times,
        (state0,) + result.states,
        ("armed",) + result.modes,
        (initial_event,) + result.events,
        result.stats,
    )


def simulate_c17_ca(
    *,
    parameters: C17Parameters = _C17_DEFAULT_PARAMETERS,
    initial_state: Sequence[int] = (9500, 500, 0),
    steps: int = 100,
    seed: int = 17,
    movement: C17Movement | str = C17Movement.FHP_I,
    intervention: C17Intervention | None = None,
) -> C17CAResult:
    """Run the official synchronous SIR cellular automaton."""

    if not isinstance(steps, int) or isinstance(steps, bool) or steps < 0:
        raise ValueError("steps must be a non-negative integer")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    try:
        selected_movement = C17Movement(movement)
    except ValueError as exc:
        raise ValueError(f"unknown C17 movement: {movement!r}") from exc
    counts = tuple(int(value) for value in initial_state)
    population = int(round(parameters.n))
    if len(counts) != 3 or any(value < 0 for value in counts) or sum(counts) != population:
        raise ValueError("integer CA initial_state must contain S, I, R and sum to n")
    if not math.isclose(parameters.n, population, abs_tol=1.0e-12):
        raise ValueError("CA population n must be integral")
    lattice_size = c17_lattice_size(population, parameters.c)
    rng = random.Random(seed)
    slots = rng.sample(range(6 * lattice_size * lattice_size), population)
    cells = [slot // 6 for slot in slots]
    directions = [slot % 6 for slot in slots]
    health = [0] * counts[0] + [1] * counts[1] + [2] * counts[2]
    rng.shuffle(health)
    susceptible = [counts[0]]
    infected = [counts[1]]
    recovered = [counts[2]]
    events: list[C17InterventionEvent] = []
    active_start: int | None = None
    soft_triggered = False
    intervention_triggered = False
    threshold_was_met = False

    for step_index in range(steps):
        current_infected = sum(value == 1 for value in health)
        threshold_met = (
            intervention is not None
            and current_infected >= intervention.threshold_fraction * population
        )
        crossed_threshold = threshold_met and not threshold_was_met
        may_trigger = (
            intervention is not None
            and threshold_met
            and (
                not intervention_triggered
                or (intervention.repeated and crossed_threshold)
            )
        )
        if may_trigger and intervention is not None:
            if intervention.soft_factor is not None and not soft_triggered:
                active_start = step_index
                soft_triggered = True
                events.append(C17InterventionEvent(step_index, "soft", 0))
            if intervention.hard_measure is not None:
                target_health = (
                    0
                    if intervention.hard_measure is C17HardMeasure.VACCINATION
                    else 1
                )
                candidates = [
                    index
                    for index, value in enumerate(health)
                    if value == target_health
                ]
                number = int(round(intervention.hard_fraction * len(candidates)))
                infected_cells = {
                    cells[index]
                    for index, value in enumerate(health)
                    if value == 1
                }
                selected = _c17_select(
                    candidates,
                    number,
                    cells,
                    lattice_size,
                    intervention.selection,
                    infected_cells,
                    rng,
                )
                for index in selected:
                    health[index] = 2
                events.append(
                    C17InterventionEvent(
                        step_index, intervention.hard_measure.value, len(selected)
                    )
                )
            intervention_triggered = True
        threshold_was_met = threshold_met

        soft_scale = 1.0
        if intervention is not None and active_start is not None:
            elapsed = step_index - active_start
            if elapsed >= intervention.duration:
                soft_scale = float(intervention.soft_factor)
            else:
                soft_scale = _c17_soft_scale(
                    elapsed,
                    intervention.duration,
                    float(intervention.soft_factor),
                    intervention.profile,
                )

        if selected_movement is C17Movement.FHP_I:
            for index, (cell, direction) in enumerate(zip(cells, directions)):
                q, r = cell % lattice_size, cell // lattice_size
                dq, dr = _HEX_DIRECTIONS[direction]
                cells[index] = ((q + dq) % lattice_size) + lattice_size * (
                    (r + dr) % lattice_size
                )
        else:
            # Homogeneous random movement still obeys the LGCA exclusion
            # rule: at most one individual occupies each directional slot.
            random_slots = rng.sample(
                range(6 * lattice_size * lattice_size),
                population,
            )
            for index, slot in enumerate(random_slots):
                cells[index] = slot // 6
                directions[index] = slot % 6

        occupants: list[list[int]] = [[] for _ in range(lattice_size * lattice_size)]
        for index, cell in enumerate(cells):
            occupants[cell].append(index)

        if selected_movement is C17Movement.FHP_I:
            for group in occupants:
                if len(group) == 2:
                    first, second = group
                    if (directions[first] - directions[second]) % 6 == 3:
                        turn = rng.choice((-1, 1))
                        directions[first] = (directions[first] + turn) % 6
                        directions[second] = (directions[second] + turn) % 6
                elif len(group) == 3:
                    values = {directions[index] for index in group}
                    if values in ({0, 2, 4}, {1, 3, 5}):
                        for index in group:
                            directions[index] = (directions[index] + 1) % 6

        infected_before = {index for index, value in enumerate(health) if value == 1}
        new_infections: set[int] = set()
        for group in occupants:
            infected_group = tuple(
                index for index in group if index in infected_before
            )
            if not infected_group:
                continue
            for index in group:
                if health[index] != 0:
                    continue
                infected_contacts = len(infected_group)
                alpha = parameters.alpha
                if (
                    intervention is not None
                    and active_start is not None
                    and intervention.soft_parameter is C17SoftParameter.CONTACTS
                ):
                    infected_contacts = sum(
                        rng.random() < soft_scale for _contact in infected_group
                    )
                elif (
                    intervention is not None
                    and active_start is not None
                    and intervention.soft_parameter is C17SoftParameter.INFECTION
                ):
                    alpha *= soft_scale
                probability = 1.0 - (1.0 - alpha) ** infected_contacts
                if rng.random() < probability:
                    new_infections.add(index)
        for index in new_infections:
            health[index] = 1
        recovery_probability = parameters.beta
        if (
            intervention is not None
            and active_start is not None
            and intervention.soft_parameter is C17SoftParameter.RECOVERY
        ):
            recovery_probability *= soft_scale
        for index in infected_before:
            if rng.random() < recovery_probability:
                health[index] = 2

        susceptible.append(sum(value == 0 for value in health))
        infected.append(sum(value == 1 for value in health))
        recovered.append(sum(value == 2 for value in health))

    return C17CAResult(
        selected_movement,
        lattice_size,
        c17_contact_rate(population, lattice_size),
        tuple(susceptible),
        tuple(infected),
        tuple(recovered),
        tuple(events),
    )


def _c17_interpolate_ode(result: IntegrationResult, time_value: float) -> Vector:
    for index, later in enumerate(result.times[1:], start=1):
        if later >= time_value:
            earlier = result.times[index - 1]
            if later == earlier:
                return result.states[index]
            fraction = (time_value - earlier) / (later - earlier)
            return tuple(
                before + fraction * (after - before)
                for before, after in zip(result.states[index - 1], result.states[index])
            )
    return result.final_state


def c17_compare_ca_ode(
    *,
    parameters: C17Parameters = _C17_DEFAULT_PARAMETERS,
    steps: int = 100,
    replications: int = 10,
    seed: int = 17,
    movement: C17Movement | str = C17Movement.FHP_I,
    initial_state: Sequence[int] = (9500, 500, 0),
) -> C17Comparison:
    """Compare the mean seeded CA trajectory with the identified ODE model."""

    if not isinstance(replications, int) or isinstance(replications, bool) or replications <= 0:
        raise ValueError("replications must be a positive integer")
    counts = tuple(int(value) for value in initial_state)
    if len(counts) != 3 or any(value < 0 for value in counts):
        raise ValueError("initial_state must contain non-negative integer S, I, R")
    if sum(counts) != int(round(parameters.n)):
        raise ValueError("initial_state must sum to the parameter population")
    runs = tuple(
        simulate_c17_ca(
            parameters=parameters,
            initial_state=counts,
            steps=steps,
            seed=seed + index,
            movement=movement,
        )
        for index in range(replications)
    )
    components = (
        tuple(run.susceptible for run in runs),
        tuple(run.infected for run in runs),
        tuple(run.recovered for run in runs),
    )
    ca_mean = tuple(
        tuple(
            sum(series[index] for series in components[component]) / replications
            for component in range(3)
        )
        for index in range(steps + 1)
    )
    ode_result = solve_c17(
        "rk45",
        parameters=parameters,
        initial_state=counts,
        t_bound=float(max(1, steps)),
    )
    times = tuple(float(index) for index in range(steps + 1))
    ode = tuple(_c17_interpolate_ode(ode_result, value) for value in times)
    rmse = math.sqrt(
        sum(
            (candidate - reference) ** 2
            for row, expected in zip(ca_mean, ode)
            for candidate, reference in zip(row, expected)
        )
        / (3 * len(times))
    )
    return C17Comparison(times, ode, ca_mean, rmse)


def c17_task1_parameter_study(
    *,
    cases: Sequence[tuple[str, C17Parameters, Sequence[int]]] | None = None,
    steps: int = 100,
    replications: int = 10,
    seed: int = 17,
    movement: C17Movement | str = C17Movement.FHP_I,
) -> tuple[C17ParameterCase, ...]:
    """Execute Task 1 sweeps for I0, alpha, beta, and the alpha-C trade-off."""

    selected_cases = cases
    if selected_cases is None:
        selected_cases = (
            ("baseline", C17Parameters(), (9500, 500, 0)),
            ("I0-low", C17Parameters(), (9900, 100, 0)),
            ("I0-high", C17Parameters(), (9000, 1000, 0)),
            ("alpha-low", C17Parameters(alpha=0.05), (9500, 500, 0)),
            ("alpha-high", C17Parameters(alpha=0.2), (9500, 500, 0)),
            ("beta-low", C17Parameters(beta=0.05), (9500, 500, 0)),
            ("beta-high", C17Parameters(beta=0.2), (9500, 500, 0)),
            ("alpha-C-low", C17Parameters(c=2.0, alpha=0.2), (9500, 500, 0)),
            ("alpha-C-high", C17Parameters(c=8.0, alpha=0.05), (9500, 500, 0)),
        )
    output = []
    for index, (label, parameters, initial) in enumerate(selected_cases):
        counts = tuple(int(value) for value in initial)
        output.append(
            C17ParameterCase(
                str(label),
                parameters,
                counts,
                c17_compare_ca_ode(
                    parameters=parameters,
                    initial_state=counts,
                    steps=steps,
                    replications=replications,
                    seed=seed + index * replications,
                    movement=movement,
                ),
            )
        )
    return tuple(output)
