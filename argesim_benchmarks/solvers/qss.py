"""Event-driven first-order Quantized State System integration."""

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
