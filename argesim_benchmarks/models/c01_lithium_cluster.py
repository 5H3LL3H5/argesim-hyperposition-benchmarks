"""ARGESIM C01: lithium-cluster dynamics under electron bombardment.

The equations, parameters, initial values and tasks follow the one-page
official C01 definition.  State order is ``(r, m, f)``.  The supplied initial
state is the state immediately after irradiation; task A switches production
off and integrates over ``[0, 10]``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..runtime import solve_ivp

C01_INITIAL_STATE: Vector = (84.99, 1.674, 9.975)
C01_LOG_LOSS_VALUES: tuple[float, ...] = (
    1.0e2,
    10.0**2.5,
    1.0e3,
    10.0**3.5,
    1.0e4,
)


@dataclass(frozen=True)
class C01Parameters:
    """Parameters in the notation of the official C01 definition."""

    k_r: float = 1.0
    k_f: float = 0.1
    loss_f: float = 1000.0
    decay_r: float = 0.1
    decay_m: float = 1.0
    production: float = 0.0

    def __post_init__(self) -> None:
        positive = (
            self.k_r,
            self.k_f,
            self.loss_f,
            self.decay_r,
            self.decay_m,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in positive):
            raise ValueError("C01 rate parameters must be positive and finite")
        if not math.isfinite(self.production) or self.production < 0.0:
            raise ValueError("production must be finite and non-negative")


_C01_DEFAULT_PARAMETERS = C01Parameters()


def c01_rhs(parameters: C01Parameters = _C01_DEFAULT_PARAMETERS) -> Rhs:
    """Return the official three-state nonlinear rate equations."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        r_center, m_center, f_center = state
        aggregation_rm = parameters.k_r * m_center * f_center
        aggregation_ff = parameters.k_f * f_center * f_center
        return (
            -parameters.decay_r * r_center + aggregation_rm,
            parameters.decay_r * r_center
            - parameters.decay_m * m_center
            + aggregation_ff
            - aggregation_rm,
            parameters.decay_r * r_center
            + 2.0 * parameters.decay_m * m_center
            - aggregation_rm
            - 2.0 * aggregation_ff
            - parameters.loss_f * f_center
            + parameters.production,
        )

    return rhs


def c01_problem(
    *,
    parameters: C01Parameters = _C01_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C01_INITIAL_STATE,
    t_bound: float = 10.0,
) -> InitialValueProblem:
    """Build the C01 initial-value problem for tasks A and B."""

    return InitialValueProblem(
        c01_rhs(parameters),
        0.0,
        initial_state,
        t_bound,
        name="ARGESIM-C01-lithium-cluster",
        autonomous=True,
    )


def c01_steady_state(parameters: C01Parameters) -> Vector:
    """Return the unique non-negative equilibrium for constant production."""

    f_center = parameters.production / parameters.loss_f
    m_center = parameters.k_f * f_center * f_center / parameters.decay_m
    r_center = parameters.k_r * m_center * f_center / parameters.decay_r
    return (r_center, m_center, f_center)


def solve_c01(
    method: str = "rk45",
    *,
    parameters: C01Parameters = _C01_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C01_INITIAL_STATE,
    t_bound: float = 10.0,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Solve C01 with an explicitly selected, auditable backend."""

    problem = c01_problem(
        parameters=parameters,
        initial_state=initial_state,
        t_bound=t_bound,
    )
    defaults = {
        "euler": {"step": 5.0e-4},
        "rk4": {"step": 1.0e-3},
        "rk45": {"rtol": 1.0e-8, "atol": 1.0e-11, "max_step": 1.0e-2},
        "qss1": {"quantum": (1.0e-2, 1.0e-3, 1.0e-4)},
        "qss2": {"quantum": (1.0e-2, 1.0e-3, 1.0e-4)},
    }
    return solve_ivp(problem, method, options=options, defaults=defaults)


def c01_task_b(
    loss_values: Sequence[float] = C01_LOG_LOSS_VALUES,
    *,
    method: str = "rk45",
) -> dict[float, IntegrationResult]:
    """Compute the complete task-B trajectories for the loss-rate sweep."""

    values = tuple(float(value) for value in loss_values)
    if not values:
        raise ValueError("task B requires at least one loss value")
    baseline = _C01_DEFAULT_PARAMETERS
    return {
        loss: solve_c01(
            method,
            parameters=replace(baseline, loss_f=loss),
        )
        for loss in values
    }


def c01_task_c() -> dict[str, Vector]:
    """Return analytical steady states with and without bombardment."""

    return {
        "bombardment": c01_steady_state(C01Parameters(production=1.0e4)),
        "no-bombardment": c01_steady_state(C01Parameters(production=0.0)),
    }
