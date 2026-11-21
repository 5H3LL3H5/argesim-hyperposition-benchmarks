"""Bogacki–Shampine RK23 and Kværnø's stiffly accurate ESDIRK 3/2a.

Both advance the third-order solution and control the embedded difference.
The implicit tableau is from Kværnø (2004), section 3, ESDIRK 3/2a.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import replace
from functools import partial

from ..ivp import InitialValueProblem, IntegrationError, IntegrationResult, SolverStats
from ._jacobian import Jacobian, validated_jacobian
from .explicit import (
    _adaptive_controls,
    _combine,
    _positive_finite,
    _positive_integer,
    _rms_error,
)

_GAMMA = 0.435866521508459
# The third and fourth rows are also the two embedded endpoint formulas.
_ROWS = (
    (2 * _GAMMA, (_GAMMA,)),
    (1.0, (0.490563388421781, 0.073570090069760)),
    (1.0, (0.308809969976747, 1.490563388421781, -1.235239879906987)),
)


class _RetryStep(IntegrationError):
    """A smaller trial can recover the implicit stage solve."""


class _StageMatrix:
    """Factor I - h*gamma*J once for the three implicit stages of this trial."""

    def __init__(self, jac: list[list[float]], step_gamma: float):
        self.lu = [
            [float(i == j) - step_gamma * v for j, v in enumerate(row)]
            for i, row in enumerate(jac)
        ]
        n = len(jac)
        self.order = list(range(n))
        for k in range(n):
            pivot = max(range(k, n), key=lambda i: abs(self.lu[i][k]))
            diagonal = self.lu[pivot][k]
            if diagonal == 0 or not math.isfinite(diagonal):
                raise _RetryStep("singular or nonfinite stage matrix")
            self.lu[k], self.lu[pivot] = self.lu[pivot], self.lu[k]
            self.order[k], self.order[pivot] = self.order[pivot], self.order[k]
            for i in range(k + 1, n):
                row = self.lu[i]
                row[k] /= diagonal
                for j in range(k + 1, n):
                    row[j] -= row[k] * self.lu[k][j]

    def solve(self, residual: Sequence[float]) -> list[float]:
        n = len(self.order)
        x = [residual[i] for i in self.order]
        for i, row in enumerate(self.lu):
            x[i] -= sum(row[j] * x[j] for j in range(i))
        for i in reversed(range(n)):
            row = self.lu[i]
            x[i] = (x[i] - sum(row[j] * x[j] for j in range(i + 1, n))) / row[i]
        if not all(map(math.isfinite, x)):
            raise _RetryStep("nonfinite Newton correction")
        return x


def _implicit_stage(problem, time, base, guess, weight, matrix, atol, rtol, limit):
    rate = problem.evaluate(time, guess)
    for _ in range(limit):
        residual = [b - x + weight * f for b, x, f in zip(base, guess, rate)]
        if not any(residual):
            return guess, rate
        correction = matrix.solve(residual)
        updated = tuple(x + d for x, d in zip(guess, correction))
        if not all(map(math.isfinite, updated)):
            raise _RetryStep("nonfinite stage iterate")
        rate = problem.evaluate(time, updated)
        norm = _rms_error(correction, guess, updated, atol, rtol, "esdirk32")
        if norm <= 0.01:
            # Check the nonlinear equation again at the corrected point.
            defect = [b - x + weight * f for b, x, f in zip(base, updated, rate)]
            if (
                _rms_error(matrix.solve(defect), guess, updated, atol, rtol, "esdirk32")
                <= 0.01
            ):
                return updated, rate
        guess = updated
    raise _RetryStep("Newton iteration did not converge")


def _esdirk_trial(
    problem, t, y, h, k1, atol, rtol, *, jacobian, jacobian_step, iterations
):
    jac, _ = validated_jacobian(problem, t, y, jacobian, jacobian_step)
    weight = h * _GAMMA
    matrix = _StageMatrix(jac, weight)
    stages = [k1]
    state = y
    for c, coefficients in _ROWS:
        base = _combine(y, h, tuple(zip(coefficients, stages)))
        previous = state
        state, rate = _implicit_stage(
            problem, t + c * h, base, previous, weight, matrix, atol, rtol, iterations
        )
        stages.append(rate)
    return state, previous, stages[-1]


def _rk23_trial(problem, t, y, h, k1, _atol, _rtol):
    k2 = problem.evaluate(t + h / 2, _combine(y, h, ((1 / 2, k1),)))
    k3 = problem.evaluate(t + 3 * h / 4, _combine(y, h, ((3 / 4, k2),)))
    high = _combine(y, h, ((2 / 9, k1), (1 / 3, k2), (4 / 9, k3)))
    k4 = problem.evaluate(t + h, high)
    low = _combine(y, h, ((7 / 24, k1), (1 / 4, k2), (1 / 3, k3), (1 / 8, k4)))
    return high, low, k4


def _integrate(
    problem, method, trial, initial_step, rtol, atol, min_step, max_step, max_steps
):
    absolute, relative, minimum, maximum, budget, h = _adaptive_controls(
        problem, initial_step, rtol, atol, min_step, max_step, max_steps
    )
    calls = 0

    def counted_rhs(t, y):
        nonlocal calls
        calls += 1
        return problem.rhs(t, y)

    # Count every RHS call, including finite differences and discarded Newton trials.
    counted = replace(problem, rhs=counted_rhs)
    t, y = problem.t0, tuple(problem.y0)
    times, states = [t], [y]
    k1 = counted.evaluate(t, y)
    accepted = rejected = 0
    while t < problem.t_bound:
        if accepted + rejected >= budget:
            raise IntegrationError(f"{method} exceeded max_steps")
        remaining = problem.t_bound - t
        h = min(h, maximum, remaining)
        end = problem.t_bound if h == remaining else t + h
        if end <= t:
            raise IntegrationError(f"{method} step no longer advances time")
        try:
            high, low, last = trial(counted, t, y, h, k1, absolute, relative)
            error = tuple(a - b for a, b in zip(high, low))
            norm = _rms_error(error, y, high, absolute, relative, method)
        except (IntegrationError, OverflowError) as exc:
            reason = str(exc)
            factor = 0.5
        else:
            factor = 5.0 if norm == 0 else min(5.0, max(0.2, 0.9 * norm ** (-1 / 3)))
            if norm <= 1.0:
                t, y, k1 = end, high, last
                accepted += 1
                if problem._record_step(times, states, t, y):
                    break
                h = max(minimum, h * factor)
                continue
            reason = "error tolerance"
        # The last interval may be shorter than min_step but must still pass.
        rejected += 1
        if h <= minimum:
            raise IntegrationError(f"{method} cannot meet {reason} at min_step")
        h = max(minimum, h * factor)
    return IntegrationResult(
        method, tuple(times), tuple(states), SolverStats(accepted, rejected, calls)
    )


def rk23(
    problem: InitialValueProblem,
    *,
    initial_step: float | None = None,
    rtol: float = 1e-6,
    atol: float | Sequence[float] = 1e-9,
    min_step: float = 1e-14,
    max_step: float = math.inf,
    max_steps: int = 1_000_000,
) -> IntegrationResult:
    """Explicit Bogacki–Shampine 3(2) with endpoint derivative reuse."""
    return _integrate(
        problem,
        "rk23",
        _rk23_trial,
        initial_step,
        rtol,
        atol,
        min_step,
        max_step,
        max_steps,
    )


def esdirk32(
    problem: InitialValueProblem,
    *,
    initial_step: float | None = None,
    rtol: float = 1e-6,
    atol: float | Sequence[float] = 1e-9,
    min_step: float = 1e-14,
    max_step: float = math.inf,
    max_steps: int = 1_000_000,
    jacobian: Jacobian | None = None,
    jacobian_step: float = 1e-6,
    max_newton_iterations: int = 8,
) -> IntegrationResult:
    """L-stable ESDIRK 3/2a for stiff ODEs with a dense simplified Newton solve.

    Supply df/dy or use centered differences. A failed stage rolls back the
    trial and retries with a smaller step. Only accepted states reach observers.
    """
    if jacobian is not None and not callable(jacobian):
        raise TypeError("jacobian must be callable")
    increment = _positive_finite(jacobian_step, name="jacobian_step")
    limit = _positive_integer(max_newton_iterations, name="max_newton_iterations")
    trial = partial(
        _esdirk_trial, jacobian=jacobian, jacobian_step=increment, iterations=limit
    )
    return _integrate(
        problem,
        "esdirk32",
        trial,
        initial_step,
        rtol,
        atol,
        min_step,
        max_step,
        max_steps,
    )
