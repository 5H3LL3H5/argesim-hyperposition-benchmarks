"""Shared initial-value problem and integration result types."""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

Vector = tuple[float, ...]
Rhs = Callable[[float, Sequence[float]], Sequence[float]]


class IntegrationError(RuntimeError):
    """Raised when an integration method cannot advance reliably."""


def _finite_vector(values: Sequence[float], *, name: str) -> Vector:
    try:
        raw_values = tuple(values)
    except TypeError as exc:
        raise TypeError(f"{name} must be a finite numeric sequence") from exc
    if any(isinstance(value, bool) for value in raw_values):
        raise TypeError(f"{name} must contain real numbers, not bool")
    try:
        result = tuple(float(value) for value in raw_values)
    except (TypeError, ValueError) as exc:
        raise TypeError(f"{name} must be a finite numeric sequence") from exc
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
        if isinstance(self.t0, bool) or isinstance(self.t_bound, bool):
            raise TypeError("time bounds must be real numbers")
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("name must be a non-empty string")
        if not isinstance(self.autonomous, bool):
            raise TypeError("autonomous must be bool")
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
        evaluation_time = float(t)
        if not math.isfinite(evaluation_time):
            raise ValueError("evaluation time must be finite")
        state = _finite_vector(y, name="state")
        if len(state) != self.dimension:
            raise ValueError("state dimension does not match y0")
        derivative = tuple(float(value) for value in self.rhs(evaluation_time, state))
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
        for name, value in (
            ("accepted_steps", self.accepted_steps),
            ("rejected_steps", self.rejected_steps),
            ("rhs_evaluations", self.rhs_evaluations),
        ):
            if not isinstance(value, int) or isinstance(value, bool):
                raise TypeError(f"{name} must be an integer")
            if value < 0:
                raise ValueError("solver statistics must be non-negative")


@dataclass(frozen=True)
class IntegrationResult:
    method: str
    times: tuple[float, ...]
    states: tuple[Vector, ...]
    stats: SolverStats

    def __post_init__(self) -> None:
        if not isinstance(self.method, str) or not self.method.strip():
            raise ValueError("method must be a non-empty string")
        if not isinstance(self.stats, SolverStats):
            raise TypeError("stats must be SolverStats")
        raw_times = tuple(self.times)
        if any(isinstance(value, bool) for value in raw_times):
            raise TypeError("result times must be real numbers, not bool")
        times = tuple(float(value) for value in raw_times)
        states = tuple(
            _finite_vector(state, name=f"states[{index}]")
            for index, state in enumerate(self.states)
        )
        if not times or len(times) != len(states):
            raise ValueError("times and states must be non-empty and equally sized")
        if not all(math.isfinite(value) for value in times):
            raise ValueError("result times must be finite")
        if any(later < earlier for earlier, later in itertools.pairwise(times)):
            raise ValueError("result times must be non-decreasing")
        dimension = len(states[0])
        if any(len(state) != dimension for state in states):
            raise ValueError("all result states must have one common dimension")
        object.__setattr__(self, "times", times)
        object.__setattr__(self, "states", states)

    @property
    def final_time(self) -> float:
        return self.times[-1]

    @property
    def final_state(self) -> Vector:
        return self.states[-1]
