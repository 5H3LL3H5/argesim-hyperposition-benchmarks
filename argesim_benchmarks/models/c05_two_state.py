"""ARGESIM C05: stiff two-state model with state-dependent switching.

The model is linear inside each mode, so this module uses the exact local
solution and bisection only for event localization.  That makes the published
event sequence an independent, high-accuracy reference for general ODE/event
solvers rather than another tolerance-dependent integration result.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import TypedDict

from ..ivp import Vector

C05_C1 = 2.7e6
C05_C3 = 3.5651205
C05_INITIAL_STATE: Vector = (4.2, 0.3)
C05_UPPER_THRESHOLD = 5.8
C05_LOWER_THRESHOLD = 2.5

C05_REFERENCE_EVENT_TIMES = (
    1.10830616777114,
    2.12968535515471,
    3.05415290699571,
    4.07553209437930,
    4.99999964622030,
)
C05_REFERENCE_FINAL_Y1 = 5.3693121470

C05_TASK_D_REFERENCE_EVENT_TIMES = (
    1.10830616777114,
    1.12172996789144,
    1.23546396574812,
    1.24888776586842,
)
C05_TASK_D_REFERENCE_LAST_EVENT_TIMES = (
    4.79588230910372,
    4.80930610922402,
    4.92304010708071,
    4.93646390720101,
)
C05_TASK_D_REFERENCE_FINAL_Y1 = 5.7804025205614


@dataclass(frozen=True)
class C05Mode:
    name: str
    c2: float
    c4: float
    threshold: float
    direction: int

    def __post_init__(self) -> None:
        if self.direction not in {-1, 1}:
            raise ValueError("event direction must be -1 or +1")
        if any(
            not math.isfinite(value) for value in (self.c2, self.c4, self.threshold)
        ):
            raise ValueError("C05 mode parameters must be finite")


C05_MODE_1 = C05Mode("state-1", 0.4, 5.5, C05_UPPER_THRESHOLD, 1)
C05_MODE_2 = C05Mode("state-2", -0.3, 2.73, C05_LOWER_THRESHOLD, -1)
C05_TASK_D_MODE_2 = C05Mode("state-2-task-d", -1.25, 4.33, 4.1, -1)


@dataclass(frozen=True)
class C05Event:
    time: float
    old_mode: str
    new_mode: str
    state: Vector


@dataclass(frozen=True)
class C05Result:
    final_time: float
    final_state: Vector
    final_mode: str
    events: tuple[C05Event, ...]
    times: tuple[float, ...] = ()
    states: tuple[Vector, ...] = ()
    modes: tuple[str, ...] = ()


@dataclass(frozen=True)
class C05Validation:
    default_maximum_event_error: float
    default_final_y1_error: float
    task_d_event_count: int
    task_d_boundary_event_error: float
    task_d_final_y1_error: float


def c05_exact_step(
    state: Vector,
    duration: float,
    mode: C05Mode,
    *,
    c1: float = C05_C1,
    c3: float = C05_C3,
) -> Vector:
    """Advance one mode by its closed-form solution."""

    if len(state) != 2:
        raise ValueError("C05 state must contain y1 and y2")
    if any(not math.isfinite(float(value)) for value in state):
        raise ValueError("C05 state must contain finite values")
    if not math.isfinite(duration) or duration < 0.0:
        raise ValueError("duration must be non-negative and finite")
    if (
        not math.isfinite(c1)
        or not math.isfinite(c3)
        or c1 <= 0.0
        or c3 <= 0.0
        or math.isclose(c1, c3)
    ):
        raise ValueError("c1 and c3 must be distinct positive values")
    y1, y2 = (float(value) for value in state)
    if duration == 0.0:
        return (y1, y2)
    difference = y2 - mode.c4
    ratio = c1 / (c1 - c3)
    equilibrium = mode.c4 + mode.c2
    slow = difference * ratio
    fast = y1 - equilibrium - slow
    return (
        equilibrium + slow * math.exp(-c3 * duration) + fast * math.exp(-c1 * duration),
        mode.c4 + difference * math.exp(-c3 * duration),
    )


def _event_delay(state: Vector, mode: C05Mode, limit: float) -> float | None:
    initial = state[0] - mode.threshold
    if mode.direction * initial >= 0.0:
        # The active guard is only considered after the mode has moved away
        # from the switching surface; callers alternate distinct thresholds.
        initial = math.copysign(abs(initial), -mode.direction)
    low = 0.0
    f_low = initial
    high = min(limit, 1.0e-8)
    while high <= limit:
        f_high = c05_exact_step(state, high, mode)[0] - mode.threshold
        if mode.direction * f_high >= 0.0 and mode.direction * f_low < 0.0:
            for _ in range(80):
                middle = 0.5 * (low + high)
                f_middle = c05_exact_step(state, middle, mode)[0] - mode.threshold
                if mode.direction * f_middle >= 0.0:
                    high = middle
                else:
                    low = middle
            return 0.5 * (low + high)
        low, f_low = high, f_high
        if high == limit:
            break
        high = min(limit, max(2.0 * high, high + 1.0e-8))
    return None


def simulate_c05(
    *,
    t_bound: float = 5.0,
    initial_state: Vector = C05_INITIAL_STATE,
    task_d: bool = False,
    max_events: int = 10_000,
    output_step: float = 0.01,
) -> C05Result:
    """Simulate the default task or the published high-frequency Task D."""

    if not math.isfinite(t_bound) or t_bound <= 0.0:
        raise ValueError("t_bound must be positive and finite")
    if (
        not isinstance(max_events, int)
        or isinstance(max_events, bool)
        or max_events <= 0
    ):
        raise ValueError("max_events must be a positive integer")
    if not math.isfinite(output_step) or output_step <= 0.0:
        raise ValueError("output_step must be positive and finite")
    if t_bound / output_step > 1_000_000:
        raise ValueError(
            "requested C05 trajectory exceeds one million output intervals"
        )
    state = tuple(float(value) for value in initial_state)
    if len(state) != 2 or any(not math.isfinite(value) for value in state):
        raise ValueError("initial_state must contain two finite values")
    second_mode = C05_TASK_D_MODE_2 if task_d else C05_MODE_2
    mode = C05_MODE_1
    time_value = 0.0
    events: list[C05Event] = []
    while time_value < t_bound:
        delay = _event_delay(state, mode, t_bound - time_value)
        if delay is None:
            state = c05_exact_step(state, t_bound - time_value, mode)
            time_value = t_bound
            break
        state = c05_exact_step(state, delay, mode)
        time_value += delay
        next_mode = second_mode if mode is C05_MODE_1 else C05_MODE_1
        events.append(C05Event(time_value, mode.name, next_mode.name, state))
        if len(events) > max_events:
            raise RuntimeError("C05 exceeded max_events")
        mode = next_mode
    # A regular grid alone would hide the very fast post-switch transients.
    # Include the event itself and samples on the fast time scale as well.
    sample_times = {0.0, t_bound}
    sample_times.update(
        i * output_step for i in range(1, math.ceil(t_bound / output_step))
    )
    for origin in (0.0, *(event.time for event in events)):
        sample_times.add(origin)
        for multiplier in (0.1, 1.0, 10.0, 100.0):
            sample = origin + multiplier / C05_C1
            if sample < t_bound:
                sample_times.add(sample)
    ordered = tuple(sorted(sample_times))
    sample_states: list[Vector] = []
    sample_modes: list[str] = []
    current_mode, origin, origin_state = C05_MODE_1, 0.0, tuple(initial_state)
    event_index = 0
    for sample in ordered:
        while event_index < len(events) and events[event_index].time <= sample:
            event = events[event_index]
            origin, origin_state = event.time, event.state
            current_mode = (
                second_mode if event.new_mode == second_mode.name else C05_MODE_1
            )
            event_index += 1
        sample_states.append(
            state
            if sample == t_bound
            else c05_exact_step(origin_state, sample - origin, current_mode)
        )
        sample_modes.append(current_mode.name)
    return C05Result(
        time_value,
        state,
        mode.name,
        tuple(events),
        ordered,
        tuple(sample_states),
        tuple(sample_modes),
    )


class _DecimalRun(TypedDict):
    precision: int
    events: tuple[tuple[Decimal, tuple[Decimal, Decimal]], ...]
    final_state: tuple[Decimal, Decimal]


def _decimal_run(precision: int, *, task_d: bool = False) -> _DecimalRun:
    """Closed-form mode flows with numerical event bisection in decimal arithmetic.

    Physical constants are transcribed as decimal strings. All state and time
    calculations stay in the chosen context, including the short interval
    between the last event and 5 s. Binary64 conversion is only for display.
    """
    with localcontext(Context(prec=precision, rounding=ROUND_HALF_EVEN)):
        c1, c3 = Decimal("2.7e6"), Decimal("3.5651205")
        modes = (
            (Decimal("0.4"), Decimal("5.5"), Decimal("5.8"), 1),
            (Decimal("-1.25"), Decimal("4.33"), Decimal("4.1"), -1)
            if task_d
            else (Decimal("-0.3"), Decimal("2.73"), Decimal("2.5"), -1),
        )
        time, bound = Decimal(0), Decimal(5)
        state = (Decimal("4.2"), Decimal("0.3"))
        mode_index = 0
        events: list[tuple[Decimal, tuple[Decimal, Decimal]]] = []

        def flow(
            values: tuple[Decimal, Decimal], duration: Decimal, index: int
        ) -> tuple[Decimal, Decimal]:
            c2, c4, _, _ = modes[index]
            difference = values[1] - c4
            slow = difference * c1 / (c1 - c3)
            equilibrium = c4 + c2
            fast = values[0] - equilibrium - slow
            return (
                equilibrium
                + slow * (-c3 * duration).exp()
                + fast * (-c1 * duration).exp(),
                c4 + difference * (-c3 * duration).exp(),
            )

        while time < bound:
            _, _, threshold, direction = modes[mode_index]
            low = Decimal(0)
            high = min(Decimal("1e-8"), bound - time)
            while direction * (flow(state, high, mode_index)[0] - threshold) < 0:
                if high == bound - time:
                    state = flow(state, high, mode_index)
                    time = bound
                    break
                low, high = high, min(2 * high, bound - time)
            if time == bound:
                break
            for _ in range(4 * precision + 32):
                middle = (low + high) / 2
                if middle in (low, high):
                    break
                if direction * (flow(state, middle, mode_index)[0] - threshold) >= 0:
                    high = middle
                else:
                    low = middle
            else:
                raise RuntimeError("C05 decimal event bisection did not converge")
            delay = (low + high) / 2
            if time + delay <= time:
                raise RuntimeError("C05 decimal precision cannot advance event time")
            state = flow(state, delay, mode_index)
            time += delay
            events.append((time, state))
            if len(events) > 1000:
                raise RuntimeError("C05 decimal event limit exceeded")
            mode_index = 1 - mode_index
        return {"precision": precision, "events": tuple(events), "final_state": state}


def c05_task_c(
    relative_accuracies: Sequence[float] = (1.0e-6, 1.0e-10, 1.0e-14),
    *,
    task_d: bool = False,
) -> dict[str, object]:
    """Measure event-time and final-state accuracy of the semi-analytical backend.

    Each requested accuracy selects arithmetic precision with guard digits for
    the stiff final transient. Results are compared with an 80-digit run and
    explicitly report whether the requested accuracy was attained. This is a
    precision experiment, not a qualification of a general-purpose ODE solver
    or a proof of an error bound over the entire trajectory.
    """
    requested = tuple(relative_accuracies)
    if not requested or any(
        isinstance(value, bool) or not math.isfinite(value) or not 1e-14 <= value < 1
        for value in requested
    ):
        raise ValueError("relative accuracies must be nonempty and in [1e-14, 1)")
    if not isinstance(task_d, bool):
        raise TypeError("task_d must be bool")
    reference = _decimal_run(80, task_d=task_d)
    rows = []
    for accuracy in requested:
        digits = max(18, math.ceil(-math.log10(accuracy)) + 12)
        candidate = _decimal_run(digits, task_d=task_d)
        actual_events, reference_events = candidate["events"], reference["events"]
        same_count = len(actual_events) == len(reference_events)
        with localcontext(Context(prec=80, rounding=ROUND_HALF_EVEN)):
            event_error = (
                max(
                    abs(event[0] - expected[0]) / abs(expected[0])
                    for event, expected in zip(actual_events, reference_events)
                )
                if same_count
                else Decimal("Infinity")
            )
            final_errors = tuple(
                abs(value - expected) / abs(expected)
                for value, expected in zip(
                    candidate["final_state"], reference["final_state"]
                )
            )
            achieved = max(event_error, *final_errors)
        rows.append(
            {
                "requested_relative_accuracy": accuracy,
                "decimal_precision": digits,
                "event_times": tuple(str(event[0]) for event in actual_events),
                "final_state": tuple(str(value) for value in candidate["final_state"]),
                "maximum_event_time_relative_error": str(event_error),
                "final_state_relative_errors": tuple(
                    str(error) for error in final_errors
                ),
                "passed": same_count and achieved <= Decimal(str(accuracy)),
            }
        )
    return {
        "backend": "decimal closed-form flows with event bisection",
        "scope": "event times and final state; arithmetic precision convergence",
        "reference_precision": 80,
        "reference_event_times": tuple(str(event[0]) for event in reference["events"]),
        "reference_final_state": tuple(
            str(value) for value in reference["final_state"]
        ),
        "task_d": task_d,
        "runs": tuple(rows),
    }


def c05_task_d(*, output_step: float = 0.01) -> dict[str, object]:
    """Task-D trajectory, event printout and its prescribed 1e-11 accuracy check."""
    return {
        "trajectory": simulate_c05(task_d=True, output_step=output_step),
        "accuracy": c05_task_c((1.0e-11,), task_d=True),
    }


def c05_validate() -> C05Validation:
    """Validate both official parameter sets against published reference data."""

    default = simulate_c05()
    task_d = simulate_c05(task_d=True)
    if len(default.events) != len(C05_REFERENCE_EVENT_TIMES):
        raise RuntimeError("C05 default event count differs from the reference")
    if len(task_d.events) != 62:
        raise RuntimeError("C05 Task D event count differs from the reference")
    default_event_error = max(
        abs(event.time - reference)
        for event, reference in zip(default.events, C05_REFERENCE_EVENT_TIMES)
    )
    task_d_boundary = (
        C05_TASK_D_REFERENCE_EVENT_TIMES + C05_TASK_D_REFERENCE_LAST_EVENT_TIMES
    )
    selected = task_d.events[:4] + task_d.events[-4:]
    task_d_event_error = max(
        abs(event.time - reference)
        for event, reference in zip(selected, task_d_boundary)
    )
    return C05Validation(
        default_event_error,
        abs(default.final_state[0] - C05_REFERENCE_FINAL_Y1),
        len(task_d.events),
        task_d_event_error,
        abs(task_d.final_state[0] - C05_TASK_D_REFERENCE_FINAL_Y1),
    )
