"""Event-driven first-order and second-order Quantized State System integration."""

from __future__ import annotations

import math
import sys
from collections.abc import Sequence

from ..ivp import (
    InitialValueProblem,
    IntegrationError,
    IntegrationResult,
    SolverStats,
)


def _quantum_vector(
    quantum: float | Sequence[float],
    dimension: int,
) -> tuple[float, ...]:
    if isinstance(quantum, bool):
        raise TypeError("quantum must be a real number or numeric sequence")
    if isinstance(quantum, (int, float)):
        values = (float(quantum),) * dimension
    else:
        raw_values = tuple(quantum)
        if any(isinstance(value, bool) for value in raw_values):
            raise TypeError("quantum values must be real numbers, not bool")
        values = tuple(float(value) for value in raw_values)
        if len(values) != dimension:
            raise ValueError("quantum dimension does not match the problem")
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError("all quantum values must be positive and finite")
    return values


def _positive_integer(value: int, *, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _finite_state(values: Sequence[float], *, method: str) -> list[float]:
    result = [float(value) for value in values]
    if not all(math.isfinite(value) for value in result):
        raise IntegrationError(f"{method} produced a non-finite state")
    return result


def _smallest_nonnegative_root(
    a: float,
    b: float,
    c: float,
    tolerance: float,
) -> float:
    """Return the earliest non-negative root of ``a*t**2 + b*t + c``."""

    if not all(math.isfinite(value) for value in (a, b, c)):
        raise IntegrationError("qss2 produced non-finite event coefficients")
    if a == 0.0:
        if b == 0.0:
            return 0.0 if c == 0.0 else math.inf
        root = -c / b
        return max(0.0, root) if root >= -tolerance else math.inf

    scale = max(abs(a), abs(b), abs(c))
    scaled_a = a / scale
    scaled_b = b / scale
    scaled_c = c / scale
    discriminant = scaled_b * scaled_b - 4.0 * scaled_a * scaled_c
    roundoff = 16.0 * sys.float_info.epsilon * (
        scaled_b * scaled_b + abs(4.0 * scaled_a * scaled_c)
    )
    if discriminant < -roundoff:
        return math.inf
    square_root = math.sqrt(max(0.0, discriminant))
    root_product = -0.5 * (
        scaled_b + math.copysign(square_root, scaled_b)
    )
    candidates: list[float] = []
    if root_product != 0.0:
        candidates.extend(
            (root_product / scaled_a, scaled_c / root_product)
        )
    else:
        candidates.append(-scaled_b / (2.0 * scaled_a))
    eligible = [max(0.0, root) for root in candidates if root >= -tolerance]
    return min(eligible, default=math.inf)


def qss1(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
) -> IntegrationResult:
    """Integrate an autonomous ODE with classical first-order QSS.

    The continuous state evolves linearly under ``f(q)`` between quantization
    events. Every component of ``q`` changes only when ``|x_i-q_i|`` reaches
    its configured quantum. Non-autonomous systems need explicit input-event
    scheduling and are rejected by this reference implementation.
    """

    if not problem.autonomous:
        raise ValueError("qss1 requires problem.autonomous=True")
    event_limit = _positive_integer(max_events, name="max_events")
    if isinstance(simultaneous_tolerance, bool):
        raise TypeError("simultaneous_tolerance must be a real number")
    tolerance = float(simultaneous_tolerance)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("simultaneous_tolerance must be finite and non-negative")

    quanta = _quantum_vector(quantum, problem.dimension)
    t = problem.t0
    x = list(problem.y0)
    q = list(problem.y0)
    times = [t]
    states = [tuple(x)]
    events = 0
    evaluations = 0

    while t < problem.t_bound:
        if events >= event_limit:
            raise IntegrationError("qss1 exceeded max_events")
        derivative = problem.evaluate(t, q)
        evaluations += 1
        crossings: list[float] = []
        for state, quantized, slope, delta in zip(x, q, derivative, quanta):
            if slope > 0.0:
                crossing = (quantized + delta - state) / slope
            elif slope < 0.0:
                crossing = (quantized - delta - state) / slope
            else:
                crossing = math.inf
            if crossing < 0.0 and crossing > -tolerance:
                crossing = 0.0
            if crossing < 0.0:
                raise IntegrationError("qss1 quantizer invariant was violated")
            crossings.append(crossing)

        elapsed = min(crossings)
        remaining = problem.t_bound - t
        if math.isinf(elapsed) or elapsed >= remaining:
            x = _finite_state(
                [value + slope * remaining for value, slope in zip(x, derivative)],
                method="qss1",
            )
            t = problem.t_bound
            times.append(t)
            states.append(tuple(x))
            break

        x = _finite_state(
            [value + slope * elapsed for value, slope in zip(x, derivative)],
            method="qss1",
        )
        t += elapsed
        threshold = tolerance * max(1.0, abs(t), abs(elapsed))
        due = [
            index
            for index, crossing in enumerate(crossings)
            if abs(crossing - elapsed) <= threshold
        ]
        if not due:
            raise IntegrationError("qss1 failed to identify the imminent quantizer")
        if events + len(due) > event_limit:
            raise IntegrationError("qss1 exceeded max_events")
        for index in due:
            direction = 1.0 if derivative[index] > 0.0 else -1.0
            q[index] += direction * quanta[index]
            x[index] = q[index]
        events += len(due)
        times.append(t)
        states.append(tuple(x))

    return IntegrationResult(
        method="qss1",
        times=tuple(times),
        states=tuple(states),
        stats=SolverStats(events, 0, evaluations),
    )


def qss2(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
) -> IntegrationResult:
    """Integrate an autonomous ODE with classical second-order QSS.

    The quantized trajectory ``q`` tracks the state ``x`` with piecewise linear
    segments. The state ``x`` evolves quadratically. An event occurs when
    ``|x_i(t) - q_i(t)| = quantum``.
    At an event for component ``i``, ``q_i`` is updated to ``x_i`` and its slope is
    updated to the current derivative ``x_i'``.

    Since the problem defines a black-box RHS, the second derivative ``x_i''`` is
    estimated using forward finite differences with a scaled step size.
    """

    if not problem.autonomous:
        raise ValueError("qss2 requires problem.autonomous=True")
    event_limit = _positive_integer(max_events, name="max_events")
    if isinstance(simultaneous_tolerance, bool):
        raise TypeError("simultaneous_tolerance must be a real number")
    tolerance = float(simultaneous_tolerance)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("simultaneous_tolerance must be finite and non-negative")

    quanta = _quantum_vector(quantum, problem.dimension)
    t = problem.t0
    x = list(problem.y0)
    q = list(problem.y0)
    # q_slope represents the slope of the piecewise linear q(t)
    q_slope = list(problem.evaluate(t, q))
    evaluations = 1

    times = [t]
    states = [tuple(x)]
    events = 0

    eps_sqrt = math.sqrt(sys.float_info.epsilon)

    while t < problem.t_bound:
        if events >= event_limit:
            raise IntegrationError("qss2 exceeded max_events")

        derivative = problem.evaluate(t, q)
        evaluations += 1

        # Approximate J_f(q) @ q_slope while keeping the perturbation of q at
        # sqrt(machine epsilon) times the state scale. Scaling the step in the
        # same direction as q_slope would catastrophically over-perturb fast
        # nonlinear systems.
        state_scale = max(1.0, max(abs(value) for value in q))
        slope_scale = max(1.0, max(abs(value) for value in q_slope))
        dt_fd = eps_sqrt * state_scale / slope_scale

        q_fd = _finite_state(
            [qv + qs * dt_fd for qv, qs in zip(q, q_slope)],
            method="qss2 finite difference",
        )
        derivative_fd = problem.evaluate(t, q_fd)
        evaluations += 1

        x_second_deriv = _finite_state(
            [(dfd - d) / dt_fd for d, dfd in zip(derivative, derivative_fd)],
            method="qss2 second derivative",
        )

        crossings: list[float] = []
        coefficients = zip(
            x,
            q,
            q_slope,
            derivative,
            x_second_deriv,
            quanta,
        )
        for state, q_val, qs_val, dx, ddx, delta in coefficients:
            c = state - q_val
            b = dx - qs_val
            a = 0.5 * ddx

            crossings.append(
                min(
                    _smallest_nonnegative_root(a, b, c - delta, tolerance),
                    _smallest_nonnegative_root(a, b, c + delta, tolerance),
                )
            )

        elapsed = min(crossings)
        remaining = problem.t_bound - t
        if math.isinf(elapsed) or elapsed >= remaining:
            x = _finite_state(
                [
                    state + dx * remaining + 0.5 * ddx * remaining**2
                    for state, dx, ddx in zip(x, derivative, x_second_deriv)
                ],
                method="qss2",
            )
            t = problem.t_bound
            times.append(t)
            states.append(tuple(x))
            break

        x = _finite_state(
            [
                state + dx * elapsed + 0.5 * ddx * elapsed**2
                for state, dx, ddx in zip(x, derivative, x_second_deriv)
            ],
            method="qss2",
        )
        q = _finite_state(
            [qv + qs * elapsed for qv, qs in zip(q, q_slope)],
            method="qss2 quantizer",
        )
        t += elapsed

        threshold = tolerance * max(1.0, abs(t), abs(elapsed))
        due = [
            index
            for index, crossing in enumerate(crossings)
            if abs(crossing - elapsed) <= threshold
        ]

        if not due:
            raise IntegrationError("qss2 failed to identify the imminent quantizer")
        if events + len(due) > event_limit:
            raise IntegrationError("qss2 exceeded max_events")

        for index in due:
            q[index] = x[index]

        new_derivative = problem.evaluate(t, q)
        evaluations += 1

        for index in due:
            q_slope[index] = new_derivative[index]

        events += len(due)
        times.append(t)
        states.append(tuple(x))

    return IntegrationResult(
        method="qss2",
        times=tuple(times),
        states=tuple(states),
        stats=SolverStats(events, 0, evaluations),
    )
