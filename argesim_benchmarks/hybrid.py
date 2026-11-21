"""Reusable state-event runtime for classical and quantized ODE segments."""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from nsa_devs.hypertime import HyperTime

from .ivp import InitialValueProblem, IntegrationError, SolverStats, Vector
from .runtime import SolverOptions, normalise_solver_name, solve_ivp
from .solvers import brentq


@dataclass(frozen=True)
class HybridReset:
    """State and optional mode selected by a discrete transition."""

    state: Sequence[float]
    mode: str | None = None
    terminate: bool = False


Guard = Callable[[float, Sequence[float]], float]
Reset = Callable[[float, Sequence[float]], Sequence[float] | HybridReset]


@dataclass(frozen=True)
class StateEvent:
    """A directed zero crossing and its discrete state transition."""

    name: str
    guard: Guard
    reset: Reset
    target_mode: str
    direction: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("event name must be a non-empty string")
        if not callable(self.guard) or not callable(self.reset):
            raise TypeError("event guard and reset must be callable")
        if not isinstance(self.target_mode, str) or not self.target_mode:
            raise ValueError("target_mode must be a non-empty string")
        if self.direction not in {-1, 0, 1}:
            raise ValueError("event direction must be -1, 0, or 1")


@dataclass(frozen=True)
class HybridMode:
    """One continuous mode and the events enabled in that mode."""

    name: str
    rhs: Callable[[float, Sequence[float]], Sequence[float]]
    events: tuple[StateEvent, ...] = ()
    autonomous: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("mode name must be a non-empty string")
        if not callable(self.rhs):
            raise TypeError("mode rhs must be callable")
        object.__setattr__(self, "events", tuple(self.events))


@dataclass(frozen=True)
class HybridEventRecord:
    """One localized transition in standard and superdense time."""

    name: str
    time: HyperTime
    source_mode: str
    target_mode: str
    state_before: Vector
    state_after: Vector


@dataclass(frozen=True)
class HybridResult:
    """Hybrid trajectory; states may change dimension between modes."""

    method: str
    times: tuple[float, ...]
    states: tuple[Vector, ...]
    modes: tuple[str, ...]
    events: tuple[HybridEventRecord, ...]
    stats: SolverStats

    @property
    def final_time(self) -> float:
        return self.times[-1]

    @property
    def final_state(self) -> Vector:
        return self.states[-1]


def _crosses(before: float, after: float, direction: int, tolerance: float) -> bool:
    if direction < 0:
        return before > tolerance and after <= tolerance
    if direction > 0:
        return before < -tolerance and after >= -tolerance
    return (
        (before > tolerance and after <= tolerance)
        or (before < -tolerance and after >= -tolerance)
    )


def _hermite_interpolate(
    left_derivative: Vector,
    state_left: Vector,
    right_derivative: Vector,
    state_right: Vector,
    span: float,
    fraction: float,
) -> Vector:
    """Cubic-Hermite state interpolation for event localization."""

    s = fraction
    h00 = 2.0 * s**3 - 3.0 * s**2 + 1.0
    h10 = s**3 - 2.0 * s**2 + s
    h01 = -2.0 * s**3 + 3.0 * s**2
    h11 = s**3 - s**2
    return tuple(
        h00 * left
        + h10 * span * left_rate
        + h01 * right
        + h11 * span * right_rate
        for left, left_rate, right, right_rate in zip(
            state_left,
            left_derivative,
            state_right,
            right_derivative,
        )
    )


def _locate_event(
    mode: HybridMode,
    event: StateEvent,
    t_left: float,
    state_left: Vector,
    t_right: float,
    state_right: Vector,
    tolerance: float,
) -> tuple[float, Vector]:
    span = t_right - t_left
    left_derivative = tuple(float(value) for value in mode.rhs(t_left, state_left))
    right_derivative = tuple(float(value) for value in mode.rhs(t_right, state_right))
    if (
        len(left_derivative) != len(state_left)
        or len(right_derivative) != len(state_right)
        or any(
            not math.isfinite(value)
            for values in (left_derivative, right_derivative)
            for value in values
        )
    ):
        raise IntegrationError("hybrid RHS returned an invalid event derivative")

    def interpolated_guard(fraction: float) -> float:
        state = _hermite_interpolate(
            left_derivative,
            state_left,
            right_derivative,
            state_right,
            span,
            fraction,
        )
        value = float(event.guard(t_left + fraction * span, state))
        if not math.isfinite(value):
            raise IntegrationError(f"event {event.name!r} returned a non-finite guard")
        return value

    left_value = interpolated_guard(0.0)
    right_value = interpolated_guard(1.0)
    if abs(left_value) <= tolerance:
        fraction = 0.0
    elif abs(right_value) <= tolerance:
        fraction = 1.0
    else:
        fraction = brentq(
            interpolated_guard,
            0.0,
            1.0,
            tol=max(1.0e-14, tolerance),
        )
    return t_left + fraction * span, _hermite_interpolate(
        left_derivative,
        state_left,
        right_derivative,
        state_right,
        span,
        fraction,
    )


def _step_event(
    mode: HybridMode,
    t_left: float,
    state_left: Vector,
    t_right: float,
    state_right: Vector,
    tolerance: float,
    localize_events: bool,
) -> tuple[StateEvent, float, Vector, int] | None:
    candidates: list[tuple[float, StateEvent, Vector]] = []
    locator_evaluations = 0
    for event in mode.events:
        before = float(event.guard(t_left, state_left))
        after = float(event.guard(t_right, state_right))
        if not math.isfinite(before) or not math.isfinite(after):
            raise IntegrationError(
                f"event {event.name!r} returned a non-finite guard"
            )
        if not _crosses(before, after, event.direction, tolerance):
            continue
        if localize_events:
            event_time, event_state = _locate_event(
                mode, event, t_left, state_left, t_right, state_right, tolerance,
            )
            locator_evaluations += 2
        else:
            event_time, event_state = t_right, state_right
        candidates.append((event_time, event, event_state))
    if not candidates:
        return None
    event_time, event, event_state = min(candidates, key=lambda candidate: candidate[0])
    return event, event_time, event_state, locator_evaluations


def simulate_hybrid(
    modes: Mapping[str, HybridMode],
    *,
    initial_mode: str,
    initial_state: Sequence[float],
    t0: float = 0.0,
    t_bound: float,
    method: str = "rk45",
    solver_options: SolverOptions | None = None,
    solver_defaults: Mapping[str, SolverOptions] | None = None,
    event_tolerance: float = 1.0e-10,
    max_events: int = 10_000,
    segment_span: float | None = None,
    localize_events: bool = True,
) -> HybridResult:
    """Integrate continuous modes and execute state transitions.

    Guards are checked as each step is accepted. The backend stops at the
    first step that brackets a crossing. ``localize_events=False`` deliberately
    switches at that step's endpoint for fixed-step real-time experiments
    where iterative backtracking is unavailable.
    """

    if not isinstance(modes, Mapping) or not modes:
        raise ValueError("modes must be a non-empty mapping")
    mode_map = dict(modes)
    if initial_mode not in mode_map:
        raise ValueError("initial_mode is not present in modes")
    for name, mode in mode_map.items():
        if name != mode.name:
            raise ValueError("mode mapping keys must match HybridMode.name")
        for event in mode.events:
            if event.target_mode not in mode_map:
                raise ValueError(
                    f"event {event.name!r} targets unknown mode {event.target_mode!r}"
                )
    if isinstance(event_tolerance, bool):
        raise TypeError("event_tolerance must be a real number")
    tolerance = float(event_tolerance)
    if not math.isfinite(tolerance) or tolerance <= 0.0:
        raise ValueError("event_tolerance must be positive and finite")
    if not isinstance(max_events, int) or isinstance(max_events, bool):
        raise TypeError("max_events must be an integer")
    if max_events <= 0:
        raise ValueError("max_events must be positive")
    if not isinstance(localize_events, bool):
        raise TypeError("localize_events must be a boolean")
    if segment_span is not None:
        if isinstance(segment_span, bool):
            raise TypeError("segment_span must be a real number")
        segment_span = float(segment_span)
        if not math.isfinite(segment_span) or segment_span <= 0.0:
            raise ValueError("segment_span must be positive and finite")

    solver_name = normalise_solver_name(method)
    time = float(t0)
    final_time = float(t_bound)
    if not math.isfinite(time) or not math.isfinite(final_time):
        raise ValueError("hybrid time bounds must be finite")
    if final_time <= time:
        raise ValueError("t_bound must be greater than t0")
    state = tuple(float(value) for value in initial_state)
    if not state or not all(math.isfinite(value) for value in state):
        raise ValueError("initial_state must be a non-empty finite sequence")

    current_mode = initial_mode
    times = [time]
    states = [state]
    trajectory_modes = [current_mode]
    records: list[HybridEventRecord] = []
    accepted = rejected = evaluations = 0
    terminated = False

    while time < final_time and not terminated:
        mode = mode_map[current_mode]
        segment_bound = (
            final_time
            if segment_span is None
            else min(final_time, time + segment_span)
        )
        located = None

        def stop_on_event(
            t_left: float, state_left: Vector, t_right: float, state_right: Vector,
            *, active_mode: HybridMode = mode,
        ) -> bool:
            nonlocal located
            located = _step_event(
                active_mode, t_left, state_left, t_right, state_right,
                tolerance, localize_events,
            )
            return located is not None

        problem = InitialValueProblem(
            mode.rhs,
            time,
            state,
            segment_bound,
            name=f"hybrid:{current_mode}",
            autonomous=mode.autonomous,
            _stop_after_step=stop_on_event if mode.events else None,
        )
        segment = solve_ivp(
            problem,
            solver_name,
            options=solver_options,
            defaults=solver_defaults,
        )
        accepted += segment.stats.accepted_steps
        rejected += segment.stats.rejected_steps
        evaluations += segment.stats.rhs_evaluations

        if located is None:
            times.extend(segment.times[1:])
            states.extend(segment.states[1:])
            trajectory_modes.extend([current_mode] * (len(segment.times) - 1))
            time = segment.final_time
            state = segment.final_state
            if time >= final_time:
                break
            continue

        if len(records) >= max_events:
            raise IntegrationError("hybrid simulation exceeded max_events")
        event, event_time, state_before, locator_evaluations = located
        evaluations += locator_evaluations
        times.extend(segment.times[1:-1])
        states.extend(segment.states[1:-1])
        trajectory_modes.extend([current_mode] * (len(segment.times) - 2))
        if event_time > times[-1]:
            times.append(event_time)
            states.append(state_before)
            trajectory_modes.append(current_mode)

        reset_value = event.reset(event_time, state_before)
        if isinstance(reset_value, HybridReset):
            state_after = tuple(float(value) for value in reset_value.state)
            next_mode = reset_value.mode or event.target_mode
            terminated = reset_value.terminate
        else:
            state_after = tuple(float(value) for value in reset_value)
            next_mode = event.target_mode
        if next_mode not in mode_map:
            raise IntegrationError(
                f"event {event.name!r} selected unknown mode {next_mode!r}"
            )
        if not state_after or not all(math.isfinite(value) for value in state_after):
            raise IntegrationError(f"event {event.name!r} produced an invalid state")

        micro = 1
        while records and records[-1].time.macro == HyperTime.at(event_time).macro:
            micro = records[-1].time.micro + 1
            break
        records.append(
            HybridEventRecord(
                event.name,
                HyperTime.at(event_time, micro),
                current_mode,
                next_mode,
                state_before,
                state_after,
            )
        )
        times.append(event_time)
        states.append(state_after)
        trajectory_modes.append(next_mode)
        if event_time <= time and state_after == state and next_mode == current_mode:
            raise IntegrationError("hybrid transition made no progress")
        time = event_time
        state = state_after
        current_mode = next_mode

    return HybridResult(
        f"{solver_name}-hybrid",
        tuple(times),
        tuple(states),
        tuple(trajectory_modes),
        tuple(records),
        SolverStats(accepted, rejected, evaluations),
    )


__all__ = [
    "HybridEventRecord",
    "HybridMode",
    "HybridReset",
    "HybridResult",
    "StateEvent",
    "simulate_hybrid",
]
