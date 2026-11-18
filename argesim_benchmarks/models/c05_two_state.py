"""ARGESIM C05: stiff two-state model with state-dependent switching.

The model is linear inside each mode, so this module uses the exact local
solution and bisection only for event localization.  That makes the published
event sequence an independent, high-accuracy reference for general ODE/event
solvers rather than another tolerance-dependent integration result.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

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
            not math.isfinite(value)
            for value in (self.c2, self.c4, self.threshold)
        ):
            raise ValueError("C05 mode parameters must be finite")


C05_MODE_1 = C05Mode("state-1", 0.4, 5.5, C05_UPPER_THRESHOLD, 1)
C05_MODE_2 = C05Mode("state-2", -0.3, 2.73, C05_LOWER_THRESHOLD, -1)
C05_TASK_D_MODE_2 = C05Mode(
    "state-2-task-d", -1.25, 4.33, 4.1, -1
)


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
    difference = y2 - mode.c4
    ratio = c1 / (c1 - c3)
    equilibrium = mode.c4 + mode.c2
    slow = difference * ratio
    fast = y1 - equilibrium - slow
    return (
        equilibrium
        + slow * math.exp(-c3 * duration)
        + fast * math.exp(-c1 * duration),
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
) -> C05Result:
    """Simulate the default task or the published high-frequency Task D."""

    if not math.isfinite(t_bound) or t_bound <= 0.0:
        raise ValueError("t_bound must be positive and finite")
    if not isinstance(max_events, int) or isinstance(max_events, bool) or max_events <= 0:
        raise ValueError("max_events must be a positive integer")
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
    return C05Result(time_value, state, mode.name, tuple(events))


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
        C05_TASK_D_REFERENCE_EVENT_TIMES
        + C05_TASK_D_REFERENCE_LAST_EVENT_TIMES
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
