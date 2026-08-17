"""Small, dependency-free polynomial utilities for event-driven solvers.

Coefficients are stored in ascending power order.  The root isolator is
intended for the degree-four-or-lower event polynomials used by QSS methods;
it recursively splits the interval at derivative roots and therefore does not
depend on a sampling grid.
"""

from __future__ import annotations

import math
import sys
from functools import lru_cache
from typing import Sequence

from ..ivp import IntegrationError


def evaluate_polynomial(coefficients: Sequence[float], value: float) -> float:
    """Evaluate an ascending-order polynomial with Horner's rule."""

    result = 0.0
    for coefficient in reversed(coefficients):
        result = result * value + coefficient
    return result


def shift_polynomial(
    coefficients: Sequence[float], elapsed: float
) -> list[float]:
    """Re-anchor ``p(s)`` as ``p(elapsed + s)``."""

    degree = len(coefficients) - 1
    shifted = [0.0] * (degree + 1)
    for target_power in range(degree + 1):
        shifted[target_power] = sum(
            coefficients[source_power]
            * math.comb(source_power, target_power)
            * elapsed ** (source_power - target_power)
            for source_power in range(target_power, degree + 1)
        )
    if not all(math.isfinite(value) for value in shifted):
        raise IntegrationError("polynomial projection produced non-finite values")
    return shifted


def polynomial_derivative(coefficients: Sequence[float]) -> list[float]:
    """Return the derivative of an ascending-order polynomial."""

    if len(coefficients) <= 1:
        return [0.0]
    return [power * coefficients[power] for power in range(1, len(coefficients))]


def _normalise(coefficients: Sequence[float]) -> list[float]:
    values = [float(value) for value in coefficients]
    if not values or not all(math.isfinite(value) for value in values):
        raise IntegrationError("event polynomial contains non-finite coefficients")
    scale = max(abs(value) for value in values)
    if scale == 0.0:
        return [0.0]
    values = [value / scale for value in values]
    cutoff = 64.0 * sys.float_info.epsilon
    while len(values) > 1 and abs(values[-1]) <= cutoff:
        values.pop()
    return values


def _unit_interval_roots(
    coefficients: Sequence[float], interval_tolerance: float
) -> list[float]:
    """Isolate every real root on ``[0, 1]`` for a low-degree polynomial."""

    values = _normalise(coefficients)
    degree = len(values) - 1
    if degree <= 0:
        return []
    if degree == 1:
        root = -values[0] / values[1]
        if -interval_tolerance <= root <= 1.0 + interval_tolerance:
            return [min(1.0, max(0.0, root))]
        return []

    critical = _unit_interval_roots(
        polynomial_derivative(values), interval_tolerance
    )
    points = [0.0]
    for point in critical:
        if point > points[-1] + interval_tolerance:
            points.append(point)
    if 1.0 > points[-1] + interval_tolerance:
        points.append(1.0)
    elif points[-1] != 1.0:
        points[-1] = 1.0

    value_tolerance = 16.0 * sys.float_info.epsilon * sum(
        abs(value) for value in values
    )
    roots: list[float] = []

    def append_root(root: float) -> None:
        bounded = min(1.0, max(0.0, root))
        if not roots or abs(bounded - roots[-1]) > interval_tolerance:
            roots.append(bounded)

    point_values = [evaluate_polynomial(values, point) for point in points]
    for point, point_value in zip(points, point_values):
        if abs(point_value) <= value_tolerance:
            append_root(point)

    for left, right, left_value, right_value in zip(
        points, points[1:], point_values, point_values[1:]
    ):
        if abs(left_value) <= value_tolerance or abs(right_value) <= value_tolerance:
            continue
        if (left_value > 0.0) == (right_value > 0.0):
            continue
        low = left
        high = right
        low_value = left_value
        for _ in range(96):
            middle = 0.5 * (low + high)
            middle_value = evaluate_polynomial(values, middle)
            if high - low <= interval_tolerance:
                low = high = middle
                break
            if (middle_value > 0.0) == (low_value > 0.0):
                low = middle
                low_value = middle_value
            else:
                high = middle
        append_root(0.5 * (low + high))
    ordered: list[float] = []
    for root in sorted(roots):
        if not ordered or abs(root - ordered[-1]) > interval_tolerance:
            ordered.append(root)
    return ordered


def first_positive_root(
    coefficients: Sequence[float],
    upper_bound: float,
    *,
    time_tolerance: float,
) -> float:
    """Return the first strictly positive root no later than ``upper_bound``."""

    if not math.isfinite(upper_bound) or upper_bound <= 0.0:
        return math.inf
    scaled: list[float] = []
    power = 1.0
    for coefficient in coefficients:
        scaled_value = float(coefficient) * power
        if not math.isfinite(scaled_value):
            raise IntegrationError("event polynomial overflowed its time interval")
        scaled.append(scaled_value)
        power *= upper_bound
    normalised_tolerance = max(
        128.0 * sys.float_info.epsilon,
        min(1.0e-6, time_tolerance / upper_bound),
    )
    roots = _unit_interval_roots(scaled, normalised_tolerance)
    zero_guard = 128.0 * sys.float_info.epsilon
    eligible = [root for root in roots if root > zero_guard]
    if not eligible:
        return math.inf
    return min(eligible) * upper_bound


def solve_linear_system(
    matrix: Sequence[Sequence[float]], right_hand_side: Sequence[float]
) -> list[float]:
    """Solve a small dense system using partial-pivot Gaussian elimination."""

    size = len(matrix)
    if size == 0 or len(right_hand_side) != size:
        raise ValueError("linear system dimensions do not agree")
    augmented = []
    for row, value in zip(matrix, right_hand_side):
        if len(row) != size:
            raise ValueError("linear system matrix must be square")
        augmented.append([float(entry) for entry in row] + [float(value)])
    if not all(math.isfinite(value) for row in augmented for value in row):
        raise IntegrationError("linear system contains non-finite values")

    scale = max(abs(value) for row in augmented for value in row[:-1])
    pivot_floor = max(1.0, scale) * 256.0 * sys.float_info.epsilon
    for column in range(size):
        pivot_row = max(
            range(column, size), key=lambda row: abs(augmented[row][column])
        )
        if abs(augmented[pivot_row][column]) <= pivot_floor:
            raise IntegrationError("linearly implicit update is singular")
        augmented[column], augmented[pivot_row] = (
            augmented[pivot_row],
            augmented[column],
        )
        pivot = augmented[column][column]
        for entry in range(column, size + 1):
            augmented[column][entry] /= pivot
        for row in range(size):
            if row == column:
                continue
            factor = augmented[row][column]
            if factor == 0.0:
                continue
            for entry in range(column, size + 1):
                augmented[row][entry] -= factor * augmented[column][entry]
    solution = [augmented[row][-1] for row in range(size)]
    if not all(math.isfinite(value) for value in solution):
        raise IntegrationError("linearly implicit update produced non-finite values")
    return solution


@lru_cache(maxsize=None)
def interpolation_inverse(radius: int) -> tuple[tuple[float, ...], ...]:
    """Return the inverse Vandermonde map for integer nodes ``[-r, r]``."""

    if radius < 0:
        raise ValueError("interpolation radius cannot be negative")
    nodes = tuple(range(-radius, radius + 1))
    matrix = [[float(node**power) for power in range(len(nodes))] for node in nodes]
    columns = []
    for column in range(len(nodes)):
        unit = [0.0] * len(nodes)
        unit[column] = 1.0
        columns.append(solve_linear_system(matrix, unit))
    return tuple(
        tuple(columns[column][row] for column in range(len(nodes)))
        for row in range(len(nodes))
    )
