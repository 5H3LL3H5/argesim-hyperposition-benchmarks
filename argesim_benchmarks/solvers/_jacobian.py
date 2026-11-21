"""Shared dense Jacobian for the quantized and implicit RK solvers."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence

from ..ivp import InitialValueProblem, IntegrationError

Jacobian = Callable[[float, Sequence[float]], Sequence[Sequence[float]]]


def validated_jacobian(
    problem: InitialValueProblem,
    time: float,
    state: Sequence[float],
    jacobian: Jacobian | None,
    jacobian_step: float,
) -> tuple[list[list[float]], int]:
    dimension = problem.dimension
    if jacobian is not None:
        if not callable(jacobian):
            raise TypeError("jacobian must be callable")
        try:
            rows = tuple(tuple(row) for row in jacobian(time, state))
        except TypeError as exc:
            raise TypeError("jacobian must return a square numeric matrix") from exc
        if len(rows) != dimension or any(len(row) != dimension for row in rows):
            raise ValueError("jacobian dimensions do not match the problem")
        matrix = [[float(value) for value in row] for row in rows]
        if not all(math.isfinite(value) for row in matrix for value in row):
            raise IntegrationError("jacobian returned a non-finite value")
        return matrix, 0

    matrix = [[0.0] * dimension for _ in range(dimension)]
    evaluations = 0
    for column in range(dimension):
        step = jacobian_step * max(1.0, abs(state[column]))
        plus = list(state)
        minus = list(state)
        plus[column] += step
        minus[column] -= step
        f_plus = problem.evaluate(time, plus)
        f_minus = problem.evaluate(time, minus)
        evaluations += 2
        for row in range(dimension):
            matrix[row][column] = (f_plus[row] - f_minus[row]) / (2.0 * step)
    return matrix, evaluations
