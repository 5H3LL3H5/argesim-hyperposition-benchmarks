"""Fixed-step Euler/RK4 and adaptive Dormand-Prince RK45 methods."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from ..ivp import InitialValueProblem, IntegrationError, IntegrationResult, SolverStats


def _positive_finite(value: float, *, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return result


def _positive_integer(value: int, *, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _combine(
    y: Sequence[float],
    h: float,
    terms: Sequence[tuple[float, Sequence[float]]],
) -> tuple[float, ...]:
    result = tuple(
        value
        + h * sum(coefficient * derivative[index] for coefficient, derivative in terms)
        for index, value in enumerate(y)
    )
    if not all(math.isfinite(value) for value in result):
        raise IntegrationError("state update produced a non-finite value")
    return result


def _fixed_step(
    problem: InitialValueProblem,
    step: float,
    method: str,
    advance: Callable[
        [InitialValueProblem, float, tuple[float, ...], float],
        tuple[tuple[float, ...], int],
    ],
    *,
    max_steps: int,
) -> IntegrationResult:
    h_nominal = _positive_finite(step, name="step")
    step_limit = _positive_integer(max_steps, name="max_steps")

    t = problem.t0
    y = tuple(problem.y0)
    times = [t]
    states = [y]
    evaluations = 0

    while t < problem.t_bound:
        if len(times) - 1 >= step_limit:
            raise IntegrationError(f"{method} exceeded max_steps")
        h = min(h_nominal, problem.t_bound - t)
        if t + h == t:
            raise IntegrationError(f"{method} step no longer advances time")
        y, used = advance(problem, t, y, h)
        evaluations += used
        t = min(problem.t_bound, t + h)
        if problem._record_step(times, states, t, y):
            break

    return IntegrationResult(
        method=method,
        times=tuple(times),
        states=tuple(states),
        stats=SolverStats(len(times) - 1, 0, evaluations),
    )


def _euler_step(
    problem: InitialValueProblem, t: float, y: tuple[float, ...], h: float
) -> tuple[tuple[float, ...], int]:
    derivative = problem.evaluate(t, y)
    return _combine(y, h, ((1.0, derivative),)), 1


def euler(
    problem: InitialValueProblem, step: float, *, max_steps: int = 1_000_000
) -> IntegrationResult:
    """Integrate with the explicit first-order Euler method."""

    return _fixed_step(problem, step, "euler", _euler_step, max_steps=max_steps)


def _rk4_step(
    problem: InitialValueProblem, t: float, y: tuple[float, ...], h: float
) -> tuple[tuple[float, ...], int]:
    k1 = problem.evaluate(t, y)
    k2 = problem.evaluate(t + h / 2.0, _combine(y, h, ((0.5, k1),)))
    k3 = problem.evaluate(t + h / 2.0, _combine(y, h, ((0.5, k2),)))
    k4 = problem.evaluate(t + h, _combine(y, h, ((1.0, k3),)))
    return _combine(
        y,
        h,
        ((1.0 / 6.0, k1), (1.0 / 3.0, k2), (1.0 / 3.0, k3), (1.0 / 6.0, k4)),
    ), 4


def rk4(
    problem: InitialValueProblem, step: float, *, max_steps: int = 1_000_000
) -> IntegrationResult:
    """Integrate with the classical explicit fourth-order Runge-Kutta method."""

    return _fixed_step(problem, step, "rk4", _rk4_step, max_steps=max_steps)


def _adaptive_controls(
    problem: InitialValueProblem,
    initial_step: float | None,
    rtol: float,
    atol: float | Sequence[float],
    min_step: float,
    max_step: float,
    max_steps: int,
):
    relative_tolerance = _positive_finite(rtol, name="rtol")
    if isinstance(atol, Sequence) and not isinstance(atol, (str, bytes)):
        absolute_tolerance = tuple(
            _positive_finite(value, name="atol") for value in atol
        )
        if len(absolute_tolerance) != problem.dimension:
            raise ValueError("atol dimension must match y0")
    else:
        absolute_tolerance = (_positive_finite(atol, name="atol"),) * problem.dimension
    minimum_step = _positive_finite(min_step, name="min_step")
    if isinstance(max_step, bool):
        raise TypeError("max_step must be a real number")
    maximum_step = float(max_step)
    if math.isnan(maximum_step) or maximum_step <= 0.0:
        raise ValueError("max_step must be positive")
    if minimum_step > maximum_step:
        raise ValueError("min_step must not exceed max_step")
    step_limit = _positive_integer(max_steps, name="max_steps")

    span = problem.t_bound - problem.t0
    h = (
        span / 100.0
        if initial_step is None
        else _positive_finite(initial_step, name="initial_step")
    )
    h = min(max(h, minimum_step), maximum_step, span)
    return (
        absolute_tolerance,
        relative_tolerance,
        minimum_step,
        maximum_step,
        step_limit,
        h,
    )


def _rms_error(
    error: Sequence[float],
    old: Sequence[float],
    new: Sequence[float],
    atol: Sequence[float],
    rtol: float,
    method: str = "rk45",
) -> float:
    scaled = [
        component / (absolute + rtol * max(abs(before), abs(after)))
        for component, before, after, absolute in zip(error, old, new, atol)
    ]
    root_dimension = math.sqrt(len(scaled))
    norm = math.hypot(*(value / root_dimension for value in scaled))
    if not math.isfinite(norm):
        raise IntegrationError(f"{method} produced a non-finite error estimate")
    return norm


def rk45(
    problem: InitialValueProblem,
    *,
    initial_step: float | None = None,
    rtol: float = 1e-6,
    atol: float | Sequence[float] = 1e-9,
    min_step: float = 1e-14,
    max_step: float = math.inf,
    max_steps: int = 1_000_000,
) -> IntegrationResult:
    """Adaptive Dormand-Prince 5(4) integration with local error control.

    ``atol`` is positive and finite, scalar or one value per state component.
    The initial step is clipped to the configured step bounds. Only the final
    interval may be shorter than ``min_step``; it still must pass error control.
    The RHS must be deterministic for the same (time, state): FSAL reuses the
    accepted endpoint derivative, and retries reuse the unchanged start value.
    """

    (
        absolute_tolerance,
        relative_tolerance,
        minimum_step,
        maximum_step,
        step_limit,
        h,
    ) = _adaptive_controls(
        problem, initial_step, rtol, atol, min_step, max_step, max_steps
    )
    t = problem.t0
    y = tuple(problem.y0)
    times = [t]
    states = [y]
    accepted = 0
    rejected = 0
    evaluations = 0
    # Dormand-Prince is FSAL: the accepted endpoint derivative is the next k1.
    # Rejected trials retain k1 at the unchanged (t, y).
    k1 = None

    while t < problem.t_bound:
        if accepted + rejected >= step_limit:
            raise IntegrationError("rk45 exceeded max_steps")
        h = min(h, maximum_step, problem.t_bound - t)
        if (h < minimum_step and h < problem.t_bound - t) or t + h == t:
            raise IntegrationError("rk45 required a step below min_step")

        if k1 is None:
            k1 = problem.evaluate(t, y)
            evaluations += 1
        k2 = problem.evaluate(t + h / 5.0, _combine(y, h, ((1.0 / 5.0, k1),)))
        k3 = problem.evaluate(
            t + 3.0 * h / 10.0,
            _combine(y, h, ((3.0 / 40.0, k1), (9.0 / 40.0, k2))),
        )
        k4 = problem.evaluate(
            t + 4.0 * h / 5.0,
            _combine(y, h, ((44.0 / 45.0, k1), (-56.0 / 15.0, k2), (32.0 / 9.0, k3))),
        )
        k5 = problem.evaluate(
            t + 8.0 * h / 9.0,
            _combine(
                y,
                h,
                (
                    (19372.0 / 6561.0, k1),
                    (-25360.0 / 2187.0, k2),
                    (64448.0 / 6561.0, k3),
                    (-212.0 / 729.0, k4),
                ),
            ),
        )
        k6 = problem.evaluate(
            t + h,
            _combine(
                y,
                h,
                (
                    (9017.0 / 3168.0, k1),
                    (-355.0 / 33.0, k2),
                    (46732.0 / 5247.0, k3),
                    (49.0 / 176.0, k4),
                    (-5103.0 / 18656.0, k5),
                ),
            ),
        )
        y5 = _combine(
            y,
            h,
            (
                (35.0 / 384.0, k1),
                (500.0 / 1113.0, k3),
                (125.0 / 192.0, k4),
                (-2187.0 / 6784.0, k5),
                (11.0 / 84.0, k6),
            ),
        )
        k7 = problem.evaluate(t + h, y5)
        y4 = _combine(
            y,
            h,
            (
                (5179.0 / 57600.0, k1),
                (7571.0 / 16695.0, k3),
                (393.0 / 640.0, k4),
                (-92097.0 / 339200.0, k5),
                (187.0 / 2100.0, k6),
                (1.0 / 40.0, k7),
            ),
        )
        evaluations += 6
        local_error = tuple(fifth - fourth for fifth, fourth in zip(y5, y4))
        error_norm = _rms_error(
            local_error, y, y5, absolute_tolerance, relative_tolerance
        )

        if error_norm <= 1.0:
            t = min(problem.t_bound, t + h)
            y = y5
            accepted += 1
            if problem._record_step(times, states, t, y):
                break
            k1 = k7
            factor = 10.0 if error_norm == 0.0 else min(10.0, 0.9 * error_norm**-0.2)
            h *= max(0.2, factor)
        else:
            rejected += 1
            h *= max(0.2, 0.9 * error_norm**-0.2)

    return IntegrationResult(
        method="rk45-dormand-prince-5(4)",
        times=tuple(times),
        states=tuple(states),
        stats=SolverStats(accepted, rejected, evaluations),
    )
