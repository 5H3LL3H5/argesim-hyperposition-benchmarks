"""Event-driven first-order and second-order Quantized State System integration."""

from __future__ import annotations

import math
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
    if isinstance(quantum, (int, float)):
        values = (float(quantum),) * dimension
    else:
        values = tuple(float(value) for value in quantum)
        if len(values) != dimension:
            raise ValueError("quantum dimension does not match the problem")
    if not all(math.isfinite(value) and value > 0.0 for value in values):
        raise ValueError("all quantum values must be positive and finite")
    return values


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
    if max_events <= 0:
        raise ValueError("max_events must be positive")
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
        if events >= max_events:
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
            x = [value + slope * remaining for value, slope in zip(x, derivative)]
            t = problem.t_bound
            times.append(t)
            states.append(tuple(x))
            break

        x = [value + slope * elapsed for value, slope in zip(x, derivative)]
        t += elapsed
        threshold = tolerance * max(1.0, abs(t), abs(elapsed))
        due = [
            index
            for index, crossing in enumerate(crossings)
            if abs(crossing - elapsed) <= threshold
        ]
        if not due:
            raise IntegrationError("qss1 failed to identify the imminent quantizer")
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
    dq_min: float = 1e-8,
) -> IntegrationResult:
    """Integrate an autonomous ODE with classical second-order QSS.

    The quantized trajectory ``q`` tracks the state ``x`` with piecewise linear segments.
    The state ``x`` evolves quadratically. An event occurs when ``|x_i(t) - q_i(t)| = quantum``.
    At an event for component ``i``, ``q_i`` is updated to ``x_i`` and its slope is
    updated to the current derivative ``x_i'``.

    Since the problem defines a black-box RHS, the second derivative ``x_i''`` is
    estimated using forward finite differences.
    """

    if not problem.autonomous:
        raise ValueError("qss2 requires problem.autonomous=True")
    if max_events <= 0:
        raise ValueError("max_events must be positive")
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

    while t < problem.t_bound:
        if events >= max_events:
            raise IntegrationError("qss2 exceeded max_events")

        # In QSS2, x' = f(q). Since q is linear, x is quadratic.
        # We estimate x'' = d/dt f(q) by evaluating f at q and a small step q + dq.
        derivative = problem.evaluate(t, q)
        evaluations += 1

        # Use finite difference to estimate the second derivative (x'')
        # q_next = q + q_slope * dt_fd
        # We choose a small effective time step for the finite difference
        dt_fd = dq_min
        q_fd = [qv + qs * dt_fd for qv, qs in zip(q, q_slope)]
        derivative_fd = problem.evaluate(t, q_fd)
        evaluations += 1

        x_second_deriv = [(dfd - d) / dt_fd for d, dfd in zip(derivative, derivative_fd)]

        crossings: list[float] = []
        for state, q_val, qs_val, dx, ddx, delta in zip(x, q, q_slope, derivative, x_second_deriv, quanta):
            # We want to solve for dt > 0:
            # |x(t+dt) - q(t+dt)| = delta
            # Let e(dt) = x(t+dt) - q(t+dt)
            # e(dt) = (x(t) + x'(t)*dt + 1/2*x''(t)*dt^2) - (q(t) + q'(t)*dt)
            # x'(t) is exactly f(q(t)) which is `dx`
            # q'(t) is `qs_val`
            c = state - q_val
            b = dx - qs_val
            a = 0.5 * ddx

            # We need to find the smallest positive root of:
            # a*dt^2 + b*dt + c - delta = 0
            # a*dt^2 + b*dt + c + delta = 0
            roots = []
            for target in (delta, -delta):
                c_eff = c - target
                if abs(a) < 1e-14:
                    # Effectively linear
                    if abs(b) > 1e-14:
                        r = -c_eff / b
                        if r > -tolerance:
                            roots.append(r if r > 0 else 0.0)
                else:
                    discriminant = b*b - 4*a*c_eff
                    if discriminant >= 0:
                        sqrt_d = math.sqrt(discriminant)
                        r1 = (-b + sqrt_d) / (2*a)
                        r2 = (-b - sqrt_d) / (2*a)
                        if r1 > -tolerance:
                            roots.append(r1 if r1 > 0 else 0.0)
                        if r2 > -tolerance:
                            roots.append(r2 if r2 > 0 else 0.0)

            if roots:
                crossings.append(min(roots))
            else:
                crossings.append(math.inf)

        elapsed = min(crossings)
        remaining = problem.t_bound - t
        if math.isinf(elapsed) or elapsed >= remaining:
            x = [state + dx * remaining + 0.5 * ddx * remaining**2
                 for state, dx, ddx in zip(x, derivative, x_second_deriv)]
            t = problem.t_bound
            times.append(t)
            states.append(tuple(x))
            break

        # Advance state to the event time
        x = [state + dx * elapsed + 0.5 * ddx * elapsed**2
             for state, dx, ddx in zip(x, derivative, x_second_deriv)]
        # Advance q to the event time
        q = [qv + qs * elapsed for qv, qs in zip(q, q_slope)]
        t += elapsed

        threshold = tolerance * max(1.0, abs(t), abs(elapsed))
        due = [
            index
            for index, crossing in enumerate(crossings)
            if abs(crossing - elapsed) <= threshold
        ]

        if not due:
            raise IntegrationError("qss2 failed to identify the imminent quantizer")

        # We need the true derivative at the new state to update q_slope accurately.
        # But wait, QSS2 evaluates the RHS using the *new* q.
        # Actually, q_i is set to x_i, and q_slope_i is set to f_i(q).
        # We must temporarily update q to evaluate f(q).
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
