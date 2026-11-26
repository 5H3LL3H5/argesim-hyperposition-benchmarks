"""Small, dependency-free polynomial utilities for event-driven solvers.

Coefficients are stored in ascending power order.  The root isolator is
intended for the degree-four-or-lower event polynomials used by QSS methods;
it recursively splits the interval at derivative roots and therefore does not
depend on a sampling grid.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Sequence
from functools import cache
from itertools import pairwise

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
    while len(values) > 1 and values[-1] == 0.0:
        values.pop()
    # Rescaling by a common power of two preserves the roots. Lift small
    # coefficients before reciprocal Horner can round an extremum to zero.
    # Apply ldexp to each coefficient: the multiplier may exceed float range.
    scale = max(abs(value) for value in values)
    if 0.0 < scale < 0.5:
        _, exponent = math.frexp(scale)
        return [math.ldexp(value, -exponent) for value in values]
    if scale > sys.float_info.max / (4 * len(values)):
        values = [math.ldexp(value, -4) for value in values]
    return values


def _event_value(coefficients: Sequence[float], t: float) -> float:
    """Evaluate p(t), or p(t)/t**degree when t > 1. Both have the same sign."""
    if t <= 1.0:
        return evaluate_polynomial(coefficients, t)
    reciprocal = 1.0 / t
    value = 0.0
    for coefficient in coefficients:
        value = value * reciprocal + coefficient
    return value


def _bracketed_root(
    coefficients: Sequence[float], left: float, right: float,
    left_value: float, time_tolerance: float,
) -> float:
    while True:
        width = right - left
        middle = left + 0.5 * width
        # Keep tiny positive roots distinguishable from the initial instant.
        tolerance = min(time_tolerance, 1e-8 * middle)
        if middle == left or middle == right or width <= tolerance:
            return middle
        value = _event_value(coefficients, middle)
        if value == 0.0:
            return middle
        if (value > 0.0) == (left_value > 0.0):
            left, left_value = middle, value
        else:
            right = middle


def _interval_roots(
    coefficients: Sequence[float], upper: float, time_tolerance: float,
) -> list[float]:
    """Isolate low-degree real roots in physical time, including tangencies."""
    values = _normalise(coefficients)
    if len(values) == 1:
        return []
    if values[0] == 0.0:
        first = next(i for i, value in enumerate(values) if value != 0.0)
        return [0.0, *_interval_roots(values[first:], upper, time_tolerance)]
    if len(values) == 2:
        root = -values[0] / values[1]
        return [root] if 0.0 < root <= upper else []

    extrema = _interval_roots(polynomial_derivative(values), upper, time_tolerance)
    points = [0.0, *(t for t in extrema if 0.0 < t < upper), upper]
    samples = [_event_value(values, t) for t in points]
    crossings = [
        (a < 0.0 < b) or (b < 0.0 < a) for a, b in pairwise(samples)
    ]
    magnitudes = [abs(value) for value in values]
    roots = []
    for i, crossing in enumerate(crossings):
        right = points[i + 1]
        if crossing:
            roots.append(_bracketed_root(values, points[i], right, samples[i], time_tolerance))
        # A multiple root may touch the threshold without changing sign.
        # Its residual is relative to the local Horner terms at this extremum.
        if samples[i + 1] == 0.0:
            roots.append(right)
        elif not crossing and (i + 1 == len(crossings) or not crossings[i + 1]):
            roundoff = 16.0 * sys.float_info.epsilon * _event_value(magnitudes, right)
            if abs(samples[i + 1]) <= roundoff:
                roots.append(right)
    return roots


def _unit_interval_roots(
    coefficients: Sequence[float], interval_tolerance: float
) -> list[float]:
    return _interval_roots(coefficients, 1.0, interval_tolerance)


def first_positive_root(
    coefficients: Sequence[float],
    upper_bound: float,
    *,
    time_tolerance: float,
) -> float:
    """Return the first strictly positive root no later than upper_bound."""
    if not math.isfinite(upper_bound) or upper_bound <= 0.0:
        return math.inf
    roots = _interval_roots(coefficients, upper_bound, time_tolerance)
    return next((root for root in roots if root > 0.0), math.inf)


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


@cache
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
