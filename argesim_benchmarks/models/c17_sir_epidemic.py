"""ARGESIM C17R: SIR-type Epidemic with Cellular Automata and Ordinary Differential Equations.

The equations, parameters, initial values and tasks follow the
official C17R definition. State order is ``(S, I, R)``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..solvers import euler, qss1, rk4, rk45

C17_INITIAL_STATE: Vector = (9500.0, 500.0, 0.0)


@dataclass(frozen=True)
class C17Parameters:
    """Parameters in the notation of the official C17R definition."""

    n: float = 10000.0
    c: float = 4.0
    alpha: float = 0.1
    beta: float = 0.1

    def __post_init__(self) -> None:
        if self.n <= 0.0:
            raise ValueError("Population size n must be strictly positive")
        if self.c < 0.0 or self.alpha < 0.0 or self.beta < 0.0:
            raise ValueError("c, alpha, and beta must be non-negative")
        if self.alpha >= 1.0 or self.beta >= 1.0:
            raise ValueError("alpha and beta must be strictly less than 1.0")


_C17_DEFAULT_PARAMETERS = C17Parameters()


def c17_rhs(parameters: C17Parameters = _C17_DEFAULT_PARAMETERS) -> Rhs:
    """Return the official three-state ODE model."""
    gamma = -(parameters.c / parameters.n) * math.log(1.0 - parameters.alpha)
    delta = -math.log(1.0 - parameters.beta)

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        susceptible, infected, _recovered = state
        infection_rate = gamma * susceptible * infected
        recovery_rate = delta * infected
        return (
            -infection_rate,
            infection_rate - recovery_rate,
            recovery_rate,
        )

    return rhs


def c17_problem(
    *,
    parameters: C17Parameters = _C17_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C17_INITIAL_STATE,
    t_bound: float = 100.0,
) -> InitialValueProblem:
    """Build the C17R initial-value problem."""
    return InitialValueProblem(
        c17_rhs(parameters),
        0.0,
        initial_state,
        t_bound,
        name="ARGESIM-C17R-sir-epidemic",
        autonomous=True,
    )


def solve_c17(
    method: str = "rk45",
    *,
    parameters: C17Parameters = _C17_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C17_INITIAL_STATE,
    t_bound: float = 100.0,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Solve C17R with an explicitly selected, auditable backend."""
    configured = dict(options or {})
    problem = c17_problem(
        parameters=parameters,
        initial_state=initial_state,
        t_bound=t_bound,
    )
    normalised = method.strip().lower()
    if normalised == "euler":
        return euler(problem, float(configured.get("step", 0.1)))
    if normalised == "rk4":
        return rk4(problem, float(configured.get("step", 0.1)))
    if normalised == "rk45":
        return rk45(
            problem,
            rtol=float(configured.get("rtol", 1.0e-8)),
            atol=float(configured.get("atol", 1.0e-11)),
            max_step=float(configured.get("max_step", 1.0)),
        )
    if normalised == "qss1":
        quantum = configured.get("quantum", (1.0, 1.0, 1.0))
        if not isinstance(quantum, (int, float, tuple, list)):
            raise TypeError("qss1 quantum must be scalar or a finite sequence")
        return qss1(problem, quantum)
    raise ValueError(f"unsupported C17 solver: {method}")
