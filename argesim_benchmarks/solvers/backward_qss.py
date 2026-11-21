"""First-order backward QSS for autonomous ODEs (Migoni, Kofman & Cellier).

The black-box RHS implies a dense dependency graph for Algorithm 1. Each
batch of direct hits is followed by one pass over its remaining neighbours.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..ivp import InitialValueProblem, IntegrationError, IntegrationResult, SolverStats
from ._clock import _on_elapsed_clock
from .qss import _finite_state, _positive_integer, _quantum_vector


def _bracket(
    state: float,
    lower: float,
    upper: float,
    quantum: float,
) -> tuple[float, float]:
    """Update the two hysteretic grid values after a monotone flight."""
    width = 1.01 * quantum
    if state <= lower:
        lower -= quantum
    elif state - lower >= width:
        lower += quantum
    if state >= upper:
        upper += quantum
    elif upper - state >= width:
        upper -= quantum
    if (
        not math.isfinite(lower)
        or not math.isfinite(upper)
        or not lower < state < upper
    ):
        raise IntegrationError("bqss1 quantum cannot resolve a state bracket")
    return lower, upper


def _toward(rate: float, state: float, target: float) -> bool:
    return (rate > 0 and target > state) or (rate < 0 and target < state)


@_on_elapsed_clock
def bqss1(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
) -> IntegrationResult:
    """Advance each state toward a predicted grid value, suppressing inconsistent drift.

    The grid origin is the component's initial value. Hysteresis is one
    percent of its quantum. In a stationary IVP the exact equilibrium is
    retained. At startup ties in direction select the upper bracket.
    """
    if not problem.autonomous:
        raise ValueError("bqss1 requires problem.autonomous=True")
    limit = _positive_integer(max_events, name="max_events")
    if isinstance(simultaneous_tolerance, bool):
        raise TypeError("simultaneous_tolerance must be a real number")
    tolerance = float(simultaneous_tolerance)
    if not math.isfinite(tolerance) or tolerance < 0:
        raise ValueError("simultaneous_tolerance must be finite and non-negative")

    x = list(problem.y0)
    t = problem.t0
    quanta = _quantum_vector(quantum, problem.dimension)
    times, states = [t], [tuple(x)]
    rates = problem.evaluate(t, x)
    if not any(rates):
        problem._record_step(times, states, problem.t_bound, tuple(x))
        return IntegrationResult(
            "bqss1", tuple(times), tuple(states), SolverStats(0, 0, 1)
        )

    brackets = [_bracket(value, value, value, delta) for value, delta in zip(x, quanta)]
    q = [hi if rate >= 0 else lo for (lo, hi), rate in zip(brackets, rates)]
    rates = problem.evaluate(t, q)
    calls, events = 2, 0
    while t < problem.t_bound:
        # Eq. (13): a component can wait at a local equilibrium while its
        # neighbours keep moving. New forcing can release it at the next event.
        slopes = [
            rate if _toward(rate, value, target) else 0.0
            for rate, value, target in zip(rates, x, q)
        ]
        hits = [
            (target - value) / slope if slope else math.inf
            for target, value, slope in zip(q, x, slopes)
        ]
        first = min(hits)
        remaining = problem.t_bound - t
        dt = min(first, remaining)
        end = problem.t_bound if dt == remaining else t + dt
        if end <= t:
            raise IntegrationError("bqss1 cannot advance the event clock")
        x = _finite_state([v + dt * d for v, d in zip(x, slopes)], method="bqss1")
        if end == problem.t_bound:
            problem._record_step(times, states, end, tuple(x))
            break

        # A tolerance on time alone could move a fast neighbour by an
        # entire quantum. Only coalesce neighbours already at their target
        # to floating-point accuracy.
        margin = tolerance * max(1.0, abs(end))
        due = set()
        for i, hit in enumerate(hits):
            # Both the projected state and the absolute sum t + dt round.
            # The quantum cap prevents early projection of a whole fast cell.
            space_roundoff = max(8 * math.ulp(q[i]), 2 * math.ulp(end) * abs(slopes[i]))
            allowance = min(space_roundoff, 1e-8 * quanta[i])
            if hit == first or (
                hit - first <= margin and abs(x[i] - q[i]) <= allowance
            ):
                due.add(i)
        if events + len(due) > limit:
            raise IntegrationError("bqss1 exceeded max_events")
        for i in due:
            x[i] = q[i]
        t = end
        events += len(due)
        if problem._record_step(times, states, t, tuple(x)):
            break

        brackets = [
            _bracket(value, lo, hi, delta)
            for value, (lo, hi), delta in zip(x, brackets, quanta)
        ]
        for i in due:
            lower, upper = brackets[i]
            q[i] = upper if rates[i] > 0 else lower
        rates = problem.evaluate(t, q)
        calls += 1
        # All remaining components are neighbours in the dense graph.
        # Choose their targets from the same provisional RHS, then commit
        # them simultaneously before evaluating the next segment.
        flips = [
            i
            for i, rate in enumerate(rates)
            if i not in due and _toward(-rate, x[i], q[i])
        ]
        if flips:
            if events + len(flips) > limit:
                raise IntegrationError("bqss1 exceeded max_events")
            for i in flips:
                lower, upper = brackets[i]
                q[i] = upper if rates[i] > 0 else lower
            events += len(flips)
            rates = problem.evaluate(t, q)
            calls += 1

    return IntegrationResult(
        "bqss1", tuple(times), tuple(states), SolverStats(events, 0, calls)
    )
