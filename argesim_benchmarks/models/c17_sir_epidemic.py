"""ARGESIM C17R: SIR-type Epidemic with Cellular Automata and Ordinary Differential Equations.

The equations, parameters, initial values and tasks follow the
official C17R definition. State order is ``(S, I, R)``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..runtime import solve_ivp

C17_INITIAL_STATE: Vector = (9500.0, 500.0, 0.0)


@dataclass(frozen=True)
class C17Parameters:
    """Parameters in the notation of the official C17R definition."""

    n: float = 10000.0
    c: float = 4.0
    alpha: float = 0.1
    beta: float = 0.1

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(value)
            for value in (self.n, self.c, self.alpha, self.beta)
        ):
            raise ValueError("C17R parameters must be finite")
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

    state = tuple(float(value) for value in initial_state)
    if len(state) != 3 or any(not math.isfinite(value) for value in state):
        raise ValueError("C17R initial_state must contain three finite values")
    if any(value < 0.0 for value in state):
        raise ValueError("C17R populations must be non-negative")
    if not math.isclose(sum(state), parameters.n, rel_tol=1.0e-12, abs_tol=1.0e-9):
        raise ValueError("C17R initial populations must sum to n")
    return InitialValueProblem(
        c17_rhs(parameters),
        0.0,
        state,
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
    problem = c17_problem(
        parameters=parameters,
        initial_state=initial_state,
        t_bound=t_bound,
    )
    defaults = {
        "euler": {"step": 0.1},
        "rk4": {"step": 0.1},
        "rk45": {"rtol": 1.0e-8, "atol": 1.0e-11, "max_step": 1.0},
        "qss1": {"quantum": (1.0, 1.0, 1.0)},
        "qss2": {"quantum": (1.0, 1.0, 1.0)},
    }
    return solve_ivp(problem, method, options=options, defaults=defaults)
