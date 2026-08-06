"""Shared initial-value problem and integration result types."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

Vector = tuple[float, ...]
Rhs = Callable[[float, Sequence[float]], Sequence[float]]


class IntegrationError(RuntimeError):
    """Raised when an integration method cannot advance reliably."""


def _finite_vector(values: Sequence[float], *, name: str) -> Vector:
    result = tuple(float(value) for value in values)
    if not result:
        raise ValueError(f"{name} must contain at least one value")
    if not all(math.isfinite(value) for value in result):
        raise ValueError(f"{name} must contain only finite values")
    return result


@dataclass(frozen=True)
class InitialValueProblem:
    """An ODE initial-value problem on a forward finite time interval."""

    rhs: Rhs
    t0: float
    y0: Sequence[float]
    t_bound: float
    name: str = "unnamed"
    autonomous: bool = False

    def __post_init__(self) -> None:
        if not callable(self.rhs):
            raise TypeError("rhs must be callable")
        t0 = float(self.t0)
        t_bound = float(self.t_bound)
        if not math.isfinite(t0) or not math.isfinite(t_bound):
            raise ValueError("time bounds must be finite")
        if t_bound <= t0:
            raise ValueError("t_bound must be greater than t0")
        object.__setattr__(self, "t0", t0)
        object.__setattr__(self, "t_bound", t_bound)
        object.__setattr__(self, "y0", _finite_vector(self.y0, name="y0"))

    @property
    def dimension(self) -> int:
        return len(self.y0)

    def evaluate(self, t: float, y: Sequence[float]) -> Vector:
        state = tuple(float(value) for value in y)
        if len(state) != self.dimension:
            raise ValueError("state dimension does not match y0")
        derivative = tuple(float(value) for value in self.rhs(float(t), state))
        if len(derivative) != self.dimension:
            raise ValueError("rhs result dimension does not match y0")
        if not all(math.isfinite(value) for value in derivative):
            raise IntegrationError("rhs returned a non-finite derivative")
        return derivative


@dataclass(frozen=True)
class SolverStats:
    accepted_steps: int
    rejected_steps: int
    rhs_evaluations: int

    def __post_init__(self) -> None:
        if min(self.accepted_steps, self.rejected_steps, self.rhs_evaluations) < 0:
            raise ValueError("solver statistics must be non-negative")


@dataclass(frozen=True)
class IntegrationResult:
    method: str
    times: tuple[float, ...]
    states: tuple[Vector, ...]
    stats: SolverStats

    def __post_init__(self) -> None:
        if not self.times or len(self.times) != len(self.states):
            raise ValueError("times and states must be non-empty and equally sized")
        if any(later < earlier for earlier, later in zip(self.times, self.times[1:])):
            raise ValueError("result times must be non-decreasing")
        dimension = len(self.states[0])
        if dimension == 0 or any(len(state) != dimension for state in self.states):
            raise ValueError("all result states must have one common dimension")

    @property
    def final_time(self) -> float:
        return self.times[-1]

    @property
    def final_state(self) -> Vector:
        return self.states[-1]

