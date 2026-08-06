"""Finite approximations for a standard NSA convergence example."""

from __future__ import annotations

import math
from collections.abc import Iterable
from dataclasses import dataclass


def decay_exact() -> float:
    """Exact standard solution of x' = -x, x(0) = 1 at t = 1."""

    return math.exp(-1.0)


def decay_euler_endpoint(steps: int) -> float:
    """Finite explicit-Euler endpoint ``(1 - 1/n)**n``."""

    if not isinstance(steps, int) or isinstance(steps, bool):
        raise TypeError("steps must be an integer")
    if steps <= 1:
        raise ValueError("steps must be greater than one")
    return (1.0 - 1.0 / steps) ** steps


@dataclass(frozen=True)
class ConvergenceRow:
    steps: int
    approximation: float
    exact: float
    absolute_error: float


def convergence_table(step_counts: Iterable[int]) -> tuple[ConvergenceRow, ...]:
    rows = []
    exact = decay_exact()
    for steps in step_counts:
        approximation = decay_euler_endpoint(steps)
        rows.append(
            ConvergenceRow(
                steps=steps,
                approximation=approximation,
                exact=exact,
                absolute_error=abs(approximation - exact),
            )
        )
    if not rows:
        raise ValueError("at least one step count is required")
    return tuple(rows)
