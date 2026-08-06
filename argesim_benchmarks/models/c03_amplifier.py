"""ARGESIM C03: Generalized Class-E Amplifier."""

from __future__ import annotations

import cmath
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..solvers import euler, rk4, rk45

C03_INITIAL_STATE: Vector = (0.0, 0.0, 0.0, 0.0)

@dataclass(frozen=True)
class C03Parameters:
    """Parameters for the C03 class-E amplifier."""
    vdc: float = 5.0
    l1: float = 79.9e-6
    c2: float = 17.9e-9
    l3: float = 232.0e-6
    c4: float = 9.66e-9
    rl: float = 38.6
    r_on: float = 0.05
    r_off: float = 5.0e6
    trf: float = 1.0e-15
    period: float = 10.0e-6
    duty_cycle: float = 0.5

    def __post_init__(self) -> None:
        if self.trf < 0.0:
            raise ValueError("C03 rise/fall time must be non-negative")

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
def c03_rhs(parameters: C03Parameters = _C03_DEFAULT_PARAMETERS) -> Rhs:
    """Return the official four-state continuous right-hand side."""

    def rhs(time: float, state: Sequence[float]) -> Vector:
        x1, x2, x3, x4 = state
        r = _r_t(time, parameters)

        dx1 = -x2 / parameters.l1 + parameters.vdc / parameters.l1
        dx2 = x1 / parameters.c2 - x2 / (parameters.c2 * r) - x3 / parameters.c2
        dx3 = x2 / parameters.l3 - parameters.rl * x3 / parameters.l3 - x4 / parameters.l3
        dx4 = x3 / parameters.c4

        return (dx1, dx2, dx3, dx4)

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
    t_bound: float = 100.0e-6,
) -> InitialValueProblem:
    """Build the C03 initial-value problem."""
    return InitialValueProblem(
        c03_rhs(parameters),
        0.0,
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
    """Solve C03 with an explicitly selected, auditable backend."""
    configured = dict(options or {})
    problem = c03_problem(
        parameters=parameters,
        initial_state=initial_state,
        t_bound=t_bound,
    )
    normalised = method.strip().lower()

    # In C03, some steps need to be very small, so we customize the defaults for RK methods
    if normalised == "euler":
        return euler(problem, float(configured.get("step", 1.0e-10)))
    if normalised == "rk4":
        return rk4(problem, float(configured.get("step", 1.0e-10)))
    if normalised == "rk45":
        return rk45(
            problem,
            rtol=float(configured.get("rtol", 1.0e-6)),
            atol=float(configured.get("atol", 1.0e-8)),
            max_step=float(configured.get("max_step", 1.0e-7)),
        )
    raise ValueError(f"unsupported C03 solver: {method}")

def c03_task_b(
    method: str = "rk45",
    *,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Compute the task-B trajectory over [0, 100E-6]."""

    # Note on QSS1/2: This model contains an explicitly non-autonomous component
    # `r_t(time)` representing the switched resistance. The framework's QSS solvers
    # (`qss1`, `qss2`) strictly enforce that the RHS must be autonomous (`autonomous=True`).
    # Because `r_t` directly depends on `time`, QSS solvers will aggressively reject
    # this InitialValueProblem upon initialization.

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
