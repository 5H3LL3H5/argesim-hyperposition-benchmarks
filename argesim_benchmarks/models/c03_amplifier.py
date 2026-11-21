"""ARGESIM C03: Generalized Class-E Amplifier."""

from __future__ import annotations

import itertools
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..runtime import (
    merge_integration_results,
    normalise_solver_name,
    solve_ivp,
)

C03_INITIAL_STATE: Vector = (0.0, 0.0, 0.0, 0.0)

@dataclass(frozen=True)
class C03Parameters:
    """Parameters for the C03 class-E amplifier."""
    vdc: float = 5.0
    l1: float = 79.9e-6
    c2: float = 17.9e-9
    l3: float = 232.0e-6
    c4: float = 9.66e-9
    rl: float = 52.4
    r_on: float = 0.05
    r_off: float = 5.0e6
    trf: float = 1.0e-15
    period: float = 10.0e-6
    duty_cycle: float = 0.5

    def __post_init__(self) -> None:
        positive = (
            self.vdc,
            self.l1,
            self.c2,
            self.l3,
            self.c4,
            self.rl,
            self.r_on,
            self.r_off,
            self.period,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in positive):
            raise ValueError("C03 electrical parameters must be positive and finite")
        if not math.isfinite(self.trf) or self.trf < 0.0:
            raise ValueError("C03 rise/fall time must be non-negative and finite")
        if not 0.0 < self.duty_cycle < 1.0:
            raise ValueError("C03 duty_cycle must be strictly between zero and one")
        if self.trf > min(
            self.period * self.duty_cycle,
            self.period * (1.0 - self.duty_cycle),
        ):
            raise ValueError("C03 rise/fall time does not fit within a switching half-cycle")

_C03_DEFAULT_PARAMETERS = C03Parameters()

def _r_t(time: float, parameters: C03Parameters) -> float:
    """Calculate the resistance of the switch at a given time."""
    t_mod = time % parameters.period
    half_period = parameters.period * parameters.duty_cycle

    # 0 to TRF: transition from ON to OFF
    if t_mod < parameters.trf:
        return parameters.r_on + (parameters.r_off - parameters.r_on) * (t_mod / parameters.trf)
    # TRF to half period: OFF
    elif t_mod < half_period:
        return parameters.r_off
    # half period to half period + TRF: transition from OFF to ON
    elif t_mod < half_period + parameters.trf:
        return parameters.r_off - (parameters.r_off - parameters.r_on) * ((t_mod - half_period) / parameters.trf)
    # half period + TRF to end of period: ON
    else:
        return parameters.r_on


def _c03_derivative(state: Sequence[float], parameters: C03Parameters, r: float) -> Vector:
    x1, x2, x3, x4 = state
    return (
        -x2 / parameters.l1 + parameters.vdc / parameters.l1,
        x1 / parameters.c2 - x2 / (parameters.c2 * r) - x3 / parameters.c2,
        x2 / parameters.l3 - parameters.rl * x3 / parameters.l3 - x4 / parameters.l3,
        x3 / parameters.c4,
    )


def c03_rhs(parameters: C03Parameters = _C03_DEFAULT_PARAMETERS) -> Rhs:
    """Return the official four-state continuous right-hand side."""

    def rhs(time: float, state: Sequence[float]) -> Vector:
        return _c03_derivative(state, parameters, _r_t(time, parameters))

    return rhs

def _durand_kerner(coeffs: Sequence[float], iterations: int = 2000, tol: float = 1e-12) -> tuple[complex, ...]:
    """Find roots of a polynomial using the Durand-Kerner method."""
    degree = len(coeffs) - 1
    if degree < 1:
        return ()

    # Normalize polynomial
    a_n = coeffs[0]
    normalized_coeffs = [c / a_n for c in coeffs]

    # Initialize roots with some complex values
    roots = [complex(0.4, 0.9) * (complex(0.4, 0.9) ** i) for i in range(degree)]

    for _ in range(iterations):
        max_diff = 0.0
        for i in range(degree):
            # Evaluate P(root)
            p_val = 0j
            for j, c in enumerate(normalized_coeffs):
                p_val = p_val * roots[i] + c

            # Denominator product (root_i - root_j)
            denom = 1.0 + 0.0j
            for j in range(degree):
                if i != j:
                    denom *= (roots[i] - roots[j])

            diff = p_val / denom
            roots[i] -= diff
            max_diff = max(max_diff, abs(diff))

        if max_diff < tol:
            break

    return tuple(roots)

def _c03_characteristic_polynomial(r: float, p: C03Parameters) -> list[float]:
    """
    Analytically construct the characteristic polynomial of the linear system
    for a given resistance `r`.
    The system is:
        dx1/dt = -x2 / L1
        dx2/dt = x1/C2 - x2/(R*C2) - x3/C2
        dx3/dt = x2/L3 - RL*x3/L3 - x4/L3
        dx4/dt = x3/C4

    The characteristic equation det(A - sI) = 0 yields:
    s^4 + c3*s^3 + c2*s^2 + c1*s + c0 = 0
    """
    c3 = 1.0 / (r * p.c2) + p.rl / p.l3
    c2 = (1.0 / (p.l1 * p.c2) +
          p.rl / (r * p.c2 * p.l3) +
          1.0 / (p.c2 * p.l3) +
          1.0 / (p.l3 * p.c4))
    c1 = (p.rl / (p.l1 * p.c2 * p.l3) +
          1.0 / (r * p.c2 * p.l3 * p.c4))
    c0 = 1.0 / (p.l1 * p.c2 * p.l3 * p.c4)

    # Return coefficients [a4, a3, a2, a1, a0]
    return [1.0, c3, c2, c1, c0]

def c03_task_a(parameters: C03Parameters = _C03_DEFAULT_PARAMETERS) -> dict[str, tuple[complex, ...]]:
    """Return the eigenvalues of the system in the ON and OFF periods."""

    coeffs_on = _c03_characteristic_polynomial(parameters.r_on, parameters)
    coeffs_off = _c03_characteristic_polynomial(parameters.r_off, parameters)

    roots_on = _durand_kerner(coeffs_on, iterations=5000)
    roots_off = _durand_kerner(coeffs_off, iterations=5000)

    # Sort roots by real part then imaginary part for deterministic output
    return {
        "ON": tuple(sorted(roots_on, key=lambda r: (r.real, r.imag))),
        "OFF": tuple(sorted(roots_off, key=lambda r: (r.real, r.imag))),
    }


def c03_problem(
    *,
    parameters: C03Parameters = _C03_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C03_INITIAL_STATE,
    t0: float = 0.0,
    t_bound: float = 100.0e-6,
) -> InitialValueProblem:
    """Build the C03 initial-value problem."""
    return InitialValueProblem(
        c03_rhs(parameters),
        t0,
        initial_state,
        t_bound,
        name="ARGESIM-C03-amplifier",
        autonomous=False,
    )

def solve_c03(
    method: str = "rk45",
    *,
    parameters: C03Parameters = _C03_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C03_INITIAL_STATE,
    t_bound: float = 100.0e-6,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Solve C03 with event-aligned segments at every switch boundary."""
    normalised = normalise_solver_name(method)
    if parameters.trf and normalised not in {"euler", "rk4", "rk45"}:
        raise ValueError(f"unsupported C03 solver: {method}")
    if not math.isfinite(t_bound) or t_bound <= 0.0:
        raise ValueError("t_bound must be positive and finite")

    boundaries = {0.0, float(t_bound)}
    half_period = parameters.period * parameters.duty_cycle
    cycle = 0
    while cycle * parameters.period < t_bound:
        base = cycle * parameters.period
        for offset in (
            parameters.trf,
            half_period,
            half_period + parameters.trf,
        ):
            # Ramp endpoints at a cycle edge use the canonical cycle
            # boundary below, including the maximum allowed rise/fall time.
            if not 0.0 < offset < parameters.period:
                continue
            boundary = base + offset
            if 0.0 < boundary < t_bound:
                boundaries.add(boundary)
        # Use the same expression as the next cycle's start. base+period can
        # differ by one ULP and create an unresolvable artificial interval.
        boundary = (cycle + 1) * parameters.period
        if 0.0 < boundary < t_bound:
            boundaries.add(boundary)
        cycle += 1

    ordered = sorted(boundaries)
    segments: list[IntegrationResult] = []
    state = tuple(float(value) for value in initial_state)

    for start, end in itertools.pairwise(ordered):
        if parameters.trf == 0.0:
            # An instantaneous switch belongs to the next segment. All RK
            # stages in this segment, including its endpoint, use its fixed
            # circuit; sampling R(end) would introduce the next discontinuity.
            resistance = _r_t(start + (end - start) / 2.0, parameters)

            def segment_rhs(
                _time: float, values: Sequence[float], r: float = resistance
            ) -> Vector:
                return _c03_derivative(values, parameters, r)

            problem = InitialValueProblem(
                segment_rhs, start, state, end,
                name="ARGESIM-C03-ideal-switch-segment", autonomous=True,
            )
        else:
            problem = c03_problem(
                parameters=parameters,
                initial_state=state,
                t0=start,
                t_bound=end,
            )
        span = end - start
        defaults = {
            "euler": {"step": 1.0e-10},
            "rk4": {"step": 1.0e-10},
            "rk45": {
                "rtol": 1.0e-6,
                "atol": 1.0e-8,
                "min_step": min(1.0e-14, max(span * 1.0e-6, 1.0e-30)),
                "max_step": 1.0e-7,
            },
        }
        segment = solve_ivp(
            problem,
            normalised,
            options=options,
            defaults=defaults,
        )
        segments.append(segment)
        state = segment.final_state
    return merge_integration_results(segments, method=normalised)

def c03_task_b(
    method: str = "rk45",
    *,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Compute the task-B trajectory over [0, 100E-6]."""

    # This model contains the explicitly time-dependent switched resistance
    # `r_t(time)`. QSS/LIQSS methods require autonomous right-hand sides, so
    # they reject this InitialValueProblem instead of hiding the input events.

    return solve_c03(
        method=method,
        parameters=_C03_DEFAULT_PARAMETERS,
        initial_state=C03_INITIAL_STATE,
        t_bound=100.0e-6,
        options=options,
    )

def c03_task_c(
    trf_values: Sequence[float] = (1.0e-15, 1.0e-11, 1.0e-9, 1.0e-7),
    *,
    method: str = "rk45",
    initial_state: Sequence[float] | None = None,
    options: Mapping[str, object] | None = None,
) -> dict[float, IntegrationResult]:
    """Compute task-C parameter variation trajectories over [0, 9E-6]."""

    values = tuple(float(value) for value in trf_values)
    if not values:
        raise ValueError("task C requires at least one TRF value")

    start_state = initial_state
    if start_state is None:
        # Task C definition: "with initial solution equal to the final solution at 100E-6 sec from task (b)"
        res_b = c03_task_b(method=method, options=options)
        start_state = res_b.final_state

    baseline = _C03_DEFAULT_PARAMETERS
    return {
        trf: solve_c03(
            method=method,
            parameters=replace(baseline, trf=trf),
            initial_state=start_state,
            t_bound=9.0e-6,
            options=options,
        )
        for trf in values
    }
