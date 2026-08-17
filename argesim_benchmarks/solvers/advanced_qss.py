"""Higher-order explicit and linearly implicit QSS reference solvers.

The implementation is deliberately dense and dependency-free.  It evaluates
all right-hand-side components after an event, which makes it suitable as a
portable correctness/reference backend.  Production QSS engines normally use
sparse dependency graphs to update only affected components.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Callable, Sequence

from ..ivp import InitialValueProblem, IntegrationError, IntegrationResult, SolverStats
from ._polynomial import (
    evaluate_polynomial,
    first_positive_root,
    interpolation_inverse,
    shift_polynomial,
    solve_linear_system,
)
from .qss import _finite_state, _positive_integer, _quantum_vector

Jacobian = Callable[[float, Sequence[float]], Sequence[Sequence[float]]]


def _validate_common_controls(
    problem: InitialValueProblem,
    max_events: int,
    simultaneous_tolerance: float,
    derivative_step: float | None,
    *,
    method: str,
) -> tuple[int, float, float | None]:
    if not problem.autonomous:
        raise ValueError(f"{method} requires problem.autonomous=True")
    event_limit = _positive_integer(max_events, name="max_events")
    if isinstance(simultaneous_tolerance, bool):
        raise TypeError("simultaneous_tolerance must be a real number")
    tolerance = float(simultaneous_tolerance)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("simultaneous_tolerance must be finite and non-negative")
    if derivative_step is None:
        finite_difference_step = None
    else:
        if isinstance(derivative_step, bool):
            raise TypeError("derivative_step must be a real number")
        finite_difference_step = float(derivative_step)
        if not math.isfinite(finite_difference_step) or finite_difference_step <= 0.0:
            raise ValueError("derivative_step must be positive and finite")
    return event_limit, tolerance, finite_difference_step


def _automatic_derivative_step(q: Sequence[Sequence[float]], order: int) -> float:
    state_scale = max(1.0, max(abs(polynomial[0]) for polynomial in q))
    characteristic_times = [1.0]
    for polynomial in q:
        for power, coefficient in enumerate(polynomial[1:], start=1):
            if coefficient != 0.0:
                characteristic_times.append(
                    (state_scale / abs(coefficient)) ** (1.0 / power)
                )
    time_scale = min(characteristic_times)
    stencil_degree = 2 * order - 2
    roundoff_balance = sys.float_info.epsilon ** (1.0 / (stencil_degree + 1))
    step = roundoff_balance * time_scale
    if not math.isfinite(step) or step <= 0.0:
        raise IntegrationError("could not select a finite QSS derivative step")
    return step


def _rhs_taylor(
    problem: InitialValueProblem,
    time: float,
    q: Sequence[Sequence[float]],
    order: int,
    derivative_step: float | None,
) -> tuple[list[list[float]], int]:
    """Estimate coefficients of ``f(q(time+s))`` through degree ``order-1``."""

    radius = order - 1
    nodes = tuple(range(-radius, radius + 1))
    inverse = interpolation_inverse(radius)
    step = derivative_step or _automatic_derivative_step(q, order)
    samples: list[tuple[float, ...]] = []
    for node in nodes:
        elapsed = node * step
        state = _finite_state(
            [evaluate_polynomial(polynomial, elapsed) for polynomial in q],
            method="QSS derivative stencil",
        )
        samples.append(problem.evaluate(time + elapsed, state))

    coefficients = [[0.0] * order for _ in range(problem.dimension)]
    for state_index in range(problem.dimension):
        for power in range(order):
            numerator = sum(
                inverse[power][sample_index] * sample[state_index]
                for sample_index, sample in enumerate(samples)
            )
            coefficients[state_index][power] = numerator / step**power
    for state_coefficients in coefficients:
        _finite_state(state_coefficients, method="QSS Taylor expansion")
    return coefficients, len(samples)


def _state_polynomials(
    values: Sequence[float], rhs_taylor: Sequence[Sequence[float]], order: int
) -> list[list[float]]:
    return [
        [float(value)]
        + [rhs_coefficients[power - 1] / power for power in range(1, order + 1)]
        for value, rhs_coefficients in zip(values, rhs_taylor)
    ]


def _bootstrap_explicit_polynomials(
    problem: InitialValueProblem,
    time: float,
    values: Sequence[float],
    order: int,
    derivative_step: float | None,
) -> tuple[list[list[float]], list[list[float]], int]:
    q = [[float(value)] + [0.0] * (order - 1) for value in values]
    evaluations = 0
    x: list[list[float]] = []
    for _ in range(order):
        rhs_coefficients, used = _rhs_taylor(
            problem, time, q, order, derivative_step
        )
        evaluations += used
        x = _state_polynomials(values, rhs_coefficients, order)
        for state_index in range(problem.dimension):
            q[state_index][1:] = x[state_index][1:order]
    rhs_coefficients, used = _rhs_taylor(problem, time, q, order, derivative_step)
    evaluations += used
    return q, _state_polynomials(values, rhs_coefficients, order), evaluations


def _boundary_time(
    state: Sequence[float],
    reference: Sequence[float],
    quantum: float,
    remaining: float,
    tolerance: float,
) -> float:
    error = [
        state[power] - (reference[power] if power < len(reference) else 0.0)
        for power in range(len(state))
    ]
    return min(
        first_positive_root(
            [error[0] - quantum] + error[1:],
            remaining,
            time_tolerance=tolerance,
        ),
        first_positive_root(
            [error[0] + quantum] + error[1:],
            remaining,
            time_tolerance=tolerance,
        ),
    )


def _qss_high_order(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    order: int,
    method: str,
    max_events: int,
    simultaneous_tolerance: float,
    derivative_step: float | None,
) -> IntegrationResult:
    event_limit, tolerance, finite_difference_step = _validate_common_controls(
        problem,
        max_events,
        simultaneous_tolerance,
        derivative_step,
        method=method,
    )
    quanta = _quantum_vector(quantum, problem.dimension)
    time = problem.t0
    q, x, evaluations = _bootstrap_explicit_polynomials(
        problem, time, problem.y0, order, finite_difference_step
    )
    times = [time]
    states = [tuple(problem.y0)]
    events = 0

    while time < problem.t_bound:
        if events >= event_limit:
            raise IntegrationError(f"{method} exceeded max_events")
        remaining = problem.t_bound - time
        root_tolerance = tolerance * max(1.0, abs(time))
        crossings = [
            _boundary_time(
                x[index], q[index], quanta[index], remaining, root_tolerance
            )
            for index in range(problem.dimension)
        ]
        elapsed = min(crossings)
        if math.isinf(elapsed) or elapsed >= remaining:
            final_state = _finite_state(
                [evaluate_polynomial(polynomial, remaining) for polynomial in x],
                method=method,
            )
            time = problem.t_bound
            times.append(time)
            states.append(tuple(final_state))
            break

        x = [shift_polynomial(polynomial, elapsed) for polynomial in x]
        q = [shift_polynomial(polynomial, elapsed) for polynomial in q]
        time += elapsed
        threshold = tolerance * max(1.0, abs(time), abs(elapsed))
        due = [
            index
            for index, crossing in enumerate(crossings)
            if abs(crossing - elapsed) <= threshold
        ]
        if not due:
            raise IntegrationError(
                f"{method} failed to identify the imminent quantizer"
            )
        if events + len(due) > event_limit:
            raise IntegrationError(f"{method} exceeded max_events")
        for index in due:
            q[index][:] = x[index][:order]

        rhs_coefficients, used = _rhs_taylor(
            problem, time, q, order, finite_difference_step
        )
        evaluations += used
        x = _state_polynomials(
            [polynomial[0] for polynomial in x], rhs_coefficients, order
        )
        events += len(due)
        times.append(time)
        states.append(tuple(polynomial[0] for polynomial in x))

    return IntegrationResult(
        method,
        tuple(times),
        tuple(states),
        SolverStats(events, 0, evaluations),
    )


def qss3(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Integrate a smooth autonomous IVP with third-order QSS."""

    return _qss_high_order(
        problem,
        quantum,
        order=3,
        method="qss3",
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def qss4(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Integrate a smooth autonomous IVP with fourth-order QSS."""

    return _qss_high_order(
        problem,
        quantum,
        order=4,
        method="qss4",
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def _validated_jacobian(
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


def _linearised_dynamics(
    problem: InitialValueProblem,
    time: float,
    values: Sequence[float],
    q: Sequence[Sequence[float]],
    order: int,
    derivative_step: float | None,
    jacobian: Jacobian | None,
    jacobian_step: float,
) -> tuple[list[list[float]], list[list[float]], list[list[float]], int]:
    rhs_coefficients, evaluations = _rhs_taylor(
        problem, time, q, order, derivative_step
    )
    matrix, jacobian_evaluations = _validated_jacobian(
        problem,
        time,
        [polynomial[0] for polynomial in q],
        jacobian,
        jacobian_step,
    )
    evaluations += jacobian_evaluations
    x = _state_polynomials(values, rhs_coefficients, order)
    return x, rhs_coefficients, matrix, evaluations


def _input_coefficients(
    state_index: int,
    q: Sequence[Sequence[float]],
    rhs_coefficients: Sequence[Sequence[float]],
    jacobian: Sequence[Sequence[float]],
    order: int,
) -> list[float]:
    diagonal = jacobian[state_index][state_index]
    return [
        rhs_coefficients[state_index][power]
        - diagonal * q[state_index][power]
        for power in range(order)
    ]


def _estimated_derivative_polynomial(
    diagonal: float,
    q: Sequence[float],
    inputs: Sequence[float],
    order: int,
) -> list[float]:
    result = [(diagonal**order) * coefficient for coefficient in q]
    for index in range(1, order + 1):
        derivative_order = order - index
        multiplier = diagonal ** (index - 1)
        for power in range(order - derivative_order):
            source_power = power + derivative_order
            result[power] += (
                multiplier
                * inputs[source_power]
                * math.factorial(source_power)
                / math.factorial(power)
            )
    return result


def _first_positive_unbounded_root(coefficients: Sequence[float]) -> float:
    """Return the first positive root of a low-degree polynomial.

    The generalized LIQSS construction produces degree-three-or-lower
    equations for a local segment horizon.  Coefficient-balance estimates and
    geometric interval growth turn that unbounded problem into the finite
    interval required by the shared, tangency-aware root isolator.  Starting
    from the smallest balance scale avoids losing a small first root when a
    later root is many orders of magnitude larger.
    """

    values = [float(value) for value in coefficients]
    if not values or not all(math.isfinite(value) for value in values):
        raise IntegrationError("LIQSS horizon polynomial is not finite")
    if max(abs(value) for value in values) == 0.0:
        raise IntegrationError("LIQSS horizon polynomial is identically zero")
    while len(values) > 1 and values[-1] == 0.0:
        values.pop()
    while len(values) > 1 and values[0] == 0.0:
        values.pop(0)
    if len(values) <= 1:
        raise IntegrationError("LIQSS horizon polynomial has no positive root")
    if len(values) == 2:
        root = -values[0] / values[1]
        if not math.isfinite(root) or root <= 0.0:
            raise IntegrationError("LIQSS horizon polynomial has no positive root")
        return root

    constant = abs(values[0])
    balance_scales: list[float] = []
    for power, coefficient in enumerate(values[1:], start=1):
        if coefficient == 0.0:
            continue
        try:
            balance = math.exp(
                (math.log(constant) - math.log(abs(coefficient))) / power
            )
        except OverflowError:
            balance = math.inf
        if math.isfinite(balance) and balance > 0.0:
            balance_scales.append(balance)
    upper_bound = min(balance_scales, default=1.0)
    for _ in range(1024):
        root = first_positive_root(
            values,
            upper_bound,
            time_tolerance=256.0 * sys.float_info.epsilon * upper_bound,
        )
        if math.isfinite(root) and root > 0.0:
            return root
        if upper_bound > sys.float_info.max / 2.0:
            break
        upper_bound *= 2.0
    raise IntegrationError("LIQSS horizon polynomial has no positive root")


def _generalised_segment_times(
    family: str,
    order: int,
    diagonal: float,
    derivative_ratio: float,
) -> tuple[float, float]:
    """Return ``(shape_time, event_horizon)`` for eLIQSS or CheQSS."""

    if order == 1:
        denominator = derivative_ratio + diagonal
        if denominator <= 0.0:
            raise IntegrationError("first-order LIQSS horizon is not positive")
        shape_time = 1.0 / denominator
        return shape_time, 2.0 * shape_time

    if family == "extended":
        if order == 2:
            shape_time = _first_positive_unbounded_root(
                (-2.0, 2.0 * diagonal, derivative_ratio - diagonal**2)
            )
        else:
            shape_time = _first_positive_unbounded_root(
                (
                    -6.0,
                    6.0 * diagonal,
                    -3.0 * diagonal**2,
                    derivative_ratio + diagonal**3,
                )
            )
        return shape_time, 2.0 * shape_time

    if order == 2:
        horizon = _first_positive_unbounded_root(
            (-16.0, 8.0 * diagonal, derivative_ratio - diagonal**2)
        )
    else:
        horizon = _first_positive_unbounded_root(
            (
                -192.0,
                96.0 * diagonal,
                -18.0 * diagonal**2,
                derivative_ratio + diagonal**3,
            )
        )
    return horizon, horizon


def _difference_coefficients(
    family: str,
    order: int,
    signed_quantum: float,
    shape_time: float,
) -> list[float]:
    """Build the local polynomial ``p = x - q`` in Taylor form."""

    if family == "extended":
        initial = ((-1.0) ** order) * signed_quantum
        return [
            initial
            * math.comb(order, power)
            * (-1.0 / shape_time) ** power
            for power in range(order + 1)
        ]
    if order == 1:
        return [
            -signed_quantum,
            2.0 * signed_quantum / shape_time,
        ]
    if order == 2:
        return [
            signed_quantum,
            -8.0 * signed_quantum / shape_time,
            8.0 * signed_quantum / shape_time**2,
        ]
    return [
        -signed_quantum,
        18.0 * signed_quantum / shape_time,
        -48.0 * signed_quantum / shape_time**2,
        32.0 * signed_quantum / shape_time**3,
    ]


def _generalised_liqss_candidate(
    state_index: int,
    x: Sequence[Sequence[float]],
    q: Sequence[Sequence[float]],
    rhs_coefficients: Sequence[Sequence[float]],
    jacobian: Sequence[Sequence[float]],
    quantum: float,
    order: int,
    family: str,
) -> tuple[list[float], float]:
    """Construct one published eLIQSS or CheQSS quantized segment."""

    diagonal = jacobian[state_index][state_index]
    inputs = _input_coefficients(
        state_index, q, rhs_coefficients, jacobian, order
    )

    nth_derivative = x[state_index][0]
    for derivative_order in range(1, order + 1):
        nth_derivative = (
            diagonal * nth_derivative
            + math.factorial(derivative_order - 1)
            * inputs[derivative_order - 1]
        )
    derivative_scale = max(
        1.0,
        abs(nth_derivative),
        abs(diagonal) ** order * max(1.0, abs(x[state_index][0])),
        *(abs(value) for value in inputs),
    )
    zero_floor = 512.0 * sys.float_info.epsilon * derivative_scale
    diagonal_floor = 512.0 * sys.float_info.epsilon * max(1.0, abs(diagonal))

    if abs(diagonal) > diagonal_floor:
        equilibrium_bound = abs(diagonal) ** order * quantum
        if abs(nth_derivative) <= equilibrium_bound * (1.0 + 1.0e-12):
            difference = nth_derivative / diagonal**order
            candidate = [x[state_index][0] - difference]
            for power in range(1, order):
                candidate.append(
                    (
                        diagonal * candidate[power - 1]
                        + inputs[power - 1]
                    )
                    / power
                )
            if all(math.isfinite(value) for value in candidate):
                return candidate, math.inf

    if abs(nth_derivative) <= zero_floor:
        candidate = [x[state_index][0]]
        for power in range(1, order):
            candidate.append(
                (diagonal * candidate[power - 1] + inputs[power - 1])
                / power
            )
        return candidate, math.inf

    direction = 1.0 if nth_derivative > 0.0 else -1.0
    derivative_ratio = abs(nth_derivative) / quantum
    shape_time, horizon = _generalised_segment_times(
        family, order, diagonal, derivative_ratio
    )
    difference = _difference_coefficients(
        family, order, direction * quantum, shape_time
    )
    candidate = [x[state_index][0] - difference[0]]
    for power in range(1, order):
        state_coefficient = (
            diagonal * candidate[power - 1] + inputs[power - 1]
        ) / power
        candidate.append(state_coefficient - difference[power])
    if not all(math.isfinite(value) for value in (*candidate, horizon)):
        raise IntegrationError("generalized LIQSS update produced non-finite values")
    minimum_horizon = 1024.0 * sys.float_info.epsilon
    if horizon <= minimum_horizon:
        raise IntegrationError("generalized LIQSS update cannot advance time")
    return candidate, horizon


def _liqss_candidate(
    state_index: int,
    x: Sequence[Sequence[float]],
    q: Sequence[Sequence[float]],
    rhs_coefficients: Sequence[Sequence[float]],
    jacobian: Sequence[Sequence[float]],
    quantum: float,
    order: int,
) -> list[float]:
    diagonal = jacobian[state_index][state_index]
    inputs = _input_coefficients(
        state_index, q, rhs_coefficients, jacobian, order
    )
    actual_derivative = math.factorial(order) * x[state_index][order]
    derivative_scale = max(
        1.0,
        abs(actual_derivative),
        *(abs(value) for value in rhs_coefficients[state_index]),
    )
    if abs(actual_derivative) <= 512.0 * sys.float_info.epsilon * derivative_scale:
        return list(x[state_index][:order])

    direction = 1.0 if actual_derivative > 0.0 else -1.0
    future_value = x[state_index][0] + direction * quantum
    estimate = (diagonal**order) * future_value
    for index in range(1, order + 1):
        derivative_order = order - index
        estimate += (
            diagonal ** (index - 1)
            * inputs[derivative_order]
            * math.factorial(derivative_order)
        )
    diagonal_floor = 512.0 * sys.float_info.epsilon * max(1.0, abs(diagonal))
    if actual_derivative * estimate > 0.0 or abs(diagonal) <= diagonal_floor:
        return [future_value] + list(x[state_index][1:order])

    candidate = [0.0] * order
    candidate[-1] = -inputs[-1] / diagonal
    for power in range(order - 2, -1, -1):
        candidate[power] = (
            (power + 1) * candidate[power + 1] - inputs[power]
        ) / diagonal
    if (
        not all(math.isfinite(value) for value in candidate)
        or abs(candidate[0] - x[state_index][0]) > quantum * (1.0 + 1.0e-9)
    ):
        return [future_value] + list(x[state_index][1:order])
    return candidate


def _significant_change(previous: float, future: float) -> bool:
    scale = max(1.0, abs(previous), abs(future))
    return abs(previous - future) > (
        0.5 * abs(previous + future)
        + 1024.0 * sys.float_info.epsilon * scale
    )


def _coupled_backward_coefficients(
    x_values: tuple[float, float],
    matrix: tuple[tuple[float, float], tuple[float, float]],
    inputs: tuple[Sequence[float], Sequence[float]],
    order: int,
    horizon: float,
) -> tuple[list[float], list[float]]:
    size = 2 * order
    equations = [[0.0] * size for _ in range(size)]
    right_hand_side = [0.0] * size

    def variable(component: int, power: int) -> int:
        return component * order + power

    for component in range(2):
        for derivative_order in range(order):
            row = component * order + derivative_order
            for power in range(derivative_order, order):
                equations[row][variable(component, power)] += (
                    math.factorial(power)
                    / math.factorial(power - derivative_order)
                    * horizon ** (power - derivative_order)
                )
            if derivative_order == 0:
                for other in range(2):
                    for power in range(order):
                        equations[row][variable(other, power)] -= (
                            matrix[component][other]
                            * horizon ** (power + 1)
                            / (power + 1)
                        )
                right_hand_side[row] = x_values[component] + sum(
                    inputs[component][power]
                    * horizon ** (power + 1)
                    / (power + 1)
                    for power in range(order)
                )
            else:
                input_derivative = derivative_order - 1
                for other in range(2):
                    for power in range(input_derivative, order):
                        equations[row][variable(other, power)] -= (
                            matrix[component][other]
                            * math.factorial(power)
                            / math.factorial(power - input_derivative)
                            * horizon ** (power - input_derivative)
                        )
                right_hand_side[row] = sum(
                    inputs[component][power]
                    * math.factorial(power)
                    / math.factorial(power - input_derivative)
                    * horizon ** (power - input_derivative)
                    for power in range(input_derivative, order)
                )
    solution = solve_linear_system(equations, right_hand_side)
    return solution[:order], solution[order:]


def _bounded_coupled_update(
    x_values: tuple[float, float],
    matrix: tuple[tuple[float, float], tuple[float, float]],
    inputs: tuple[Sequence[float], Sequence[float]],
    quanta: tuple[float, float],
    order: int,
    remaining: float,
) -> tuple[list[float], list[float]] | None:
    def attempt(horizon: float) -> tuple[list[float], list[float]] | None:
        try:
            return _coupled_backward_coefficients(
                x_values, matrix, inputs, order, horizon
            )
        except IntegrationError:
            return None

    def violation(candidate: tuple[list[float], list[float]] | None) -> float:
        if candidate is None:
            return math.inf
        return max(
            abs(candidate[0][0] - x_values[0]) / quanta[0],
            abs(candidate[1][0] - x_values[1]) / quanta[1],
        )

    candidate = attempt(remaining)
    if violation(candidate) <= 1.0 + 1.0e-10:
        return candidate

    low = 0.0
    high = remaining
    best = attempt(0.0)
    if violation(best) > 1.0 + 1.0e-10:
        return None
    for _ in range(72):
        middle = 0.5 * (low + high)
        middle_candidate = attempt(middle)
        if violation(middle_candidate) <= 1.0:
            low = middle
            best = middle_candidate
        else:
            high = middle
    minimum_horizon = 1024.0 * sys.float_info.epsilon * max(1.0, remaining)
    if low <= minimum_horizon or best is None:
        return None
    return best


def _apply_modified_pairs(
    due: Sequence[int],
    candidates: dict[int, list[float]],
    x: Sequence[Sequence[float]],
    q: Sequence[Sequence[float]],
    rhs_coefficients: Sequence[Sequence[float]],
    jacobian: Sequence[Sequence[float]],
    quanta: Sequence[float],
    order: int,
    remaining: float,
    coupling_tolerance: float,
) -> tuple[dict[int, list[float]], set[int]]:
    updated = set(due)
    paired: set[int] = set()
    for state_index in due:
        if state_index in paired:
            continue
        best_partner = -1
        best_score = 0.0
        best_proposal: list[float] | None = None
        for partner in range(len(q)):
            if partner == state_index or partner in paired:
                continue
            row_scale_i = max(1.0, *(abs(value) for value in jacobian[state_index]))
            row_scale_j = max(1.0, *(abs(value) for value in jacobian[partner]))
            if (
                abs(jacobian[state_index][partner])
                <= coupling_tolerance * row_scale_i
                or abs(jacobian[partner][state_index])
                <= coupling_tolerance * row_scale_j
            ):
                continue

            changed_partner = []
            for power in range(order):
                previous = rhs_coefficients[partner][power]
                future = previous + jacobian[partner][state_index] * (
                    candidates[state_index][power] - q[state_index][power]
                )
                changed_partner.append((previous, future))
            if not any(_significant_change(*change) for change in changed_partner):
                continue

            highest = changed_partner[-1][1] * math.factorial(order - 1)
            if highest == 0.0:
                highest = changed_partner[0][1]
            direction = 1.0 if highest >= 0.0 else -1.0
            proposal = [
                x[partner][0] + direction * quanta[partner],
                *x[partner][1:order],
            ]
            changed_back = []
            for power in range(order):
                after_first = rhs_coefficients[state_index][power] + jacobian[
                    state_index
                ][state_index] * (
                    candidates[state_index][power] - q[state_index][power]
                )
                after_second = after_first + jacobian[state_index][partner] * (
                    proposal[power] - q[partner][power]
                )
                changed_back.append((after_first, after_second))
            if not any(_significant_change(*change) for change in changed_back):
                continue
            score = max(
                abs(previous - future) / max(1.0, abs(previous), abs(future))
                for previous, future in (*changed_partner, *changed_back)
            )
            if score > best_score:
                best_score = score
                best_partner = partner
                best_proposal = proposal

        if best_partner < 0 or best_proposal is None:
            continue
        partner = best_partner
        local_matrix = (
            (
                jacobian[state_index][state_index],
                jacobian[state_index][partner],
            ),
            (jacobian[partner][state_index], jacobian[partner][partner]),
        )
        local_inputs = (
            [
                rhs_coefficients[state_index][power]
                - jacobian[state_index][state_index] * q[state_index][power]
                - jacobian[state_index][partner] * q[partner][power]
                for power in range(order)
            ],
            [
                rhs_coefficients[partner][power]
                - jacobian[partner][state_index] * q[state_index][power]
                - jacobian[partner][partner] * q[partner][power]
                for power in range(order)
            ],
        )
        coupled = _bounded_coupled_update(
            (x[state_index][0], x[partner][0]),
            local_matrix,
            local_inputs,
            (quanta[state_index], quanta[partner]),
            order,
            remaining,
        )
        if coupled is None:
            continue
        candidates[state_index], candidates[partner] = coupled
        updated.add(partner)
        paired.update((state_index, partner))
    return candidates, updated


def _liqss_family(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    order: int,
    modified: bool,
    method: str,
    jacobian: Jacobian | None,
    jacobian_step: float,
    coupling_tolerance: float,
    max_events: int,
    simultaneous_tolerance: float,
    derivative_step: float | None,
) -> IntegrationResult:
    event_limit, tolerance, finite_difference_step = _validate_common_controls(
        problem,
        max_events,
        simultaneous_tolerance,
        derivative_step,
        method=method,
    )
    if isinstance(jacobian_step, bool):
        raise TypeError("jacobian_step must be a real number")
    jacobian_delta = float(jacobian_step)
    if not math.isfinite(jacobian_delta) or jacobian_delta <= 0.0:
        raise ValueError("jacobian_step must be positive and finite")
    if isinstance(coupling_tolerance, bool):
        raise TypeError("coupling_tolerance must be a real number")
    coupling_delta = float(coupling_tolerance)
    if not math.isfinite(coupling_delta) or coupling_delta < 0.0:
        raise ValueError("coupling_tolerance must be finite and non-negative")

    quanta = _quantum_vector(quantum, problem.dimension)
    time = problem.t0
    q, x, evaluations = _bootstrap_explicit_polynomials(
        problem, time, problem.y0, order, finite_difference_step
    )
    x, rhs_coefficients, matrix, used = _linearised_dynamics(
        problem,
        time,
        problem.y0,
        q,
        order,
        finite_difference_step,
        jacobian,
        jacobian_delta,
    )
    evaluations += used
    initial_due = tuple(range(problem.dimension))
    candidates = {
        index: _liqss_candidate(
            index, x, q, rhs_coefficients, matrix, quanta[index], order
        )
        for index in initial_due
    }
    updated = set(initial_due)
    if modified:
        candidates, updated = _apply_modified_pairs(
            initial_due,
            candidates,
            x,
            q,
            rhs_coefficients,
            matrix,
            quanta,
            order,
            problem.t_bound - time,
            coupling_delta,
        )
    for index in updated:
        q[index] = candidates[index]
    q_minus = [
        [x[index][0], *q[index][1:]] for index in range(problem.dimension)
    ]
    x, rhs_coefficients, matrix, used = _linearised_dynamics(
        problem,
        time,
        problem.y0,
        q,
        order,
        finite_difference_step,
        jacobian,
        jacobian_delta,
    )
    evaluations += used

    times = [time]
    states = [tuple(problem.y0)]
    events = 0
    while time < problem.t_bound:
        if events >= event_limit:
            raise IntegrationError(f"{method} exceeded max_events")
        remaining = problem.t_bound - time
        root_tolerance = tolerance * max(1.0, abs(time))
        crossings: list[float] = []
        for index in range(problem.dimension):
            boundary = _boundary_time(
                x[index],
                q_minus[index],
                quanta[index],
                remaining,
                root_tolerance,
            )
            inputs = _input_coefficients(
                index, q, rhs_coefficients, matrix, order
            )
            estimate = _estimated_derivative_polynomial(
                matrix[index][index], q[index], inputs, order
            )
            direction_change = first_positive_root(
                estimate,
                remaining,
                time_tolerance=root_tolerance,
            )
            crossings.append(min(boundary, direction_change))

        elapsed = min(crossings)
        if math.isinf(elapsed) or elapsed >= remaining:
            final_state = _finite_state(
                [evaluate_polynomial(polynomial, remaining) for polynomial in x],
                method=method,
            )
            time = problem.t_bound
            times.append(time)
            states.append(tuple(final_state))
            break

        x = [shift_polynomial(polynomial, elapsed) for polynomial in x]
        q = [shift_polynomial(polynomial, elapsed) for polynomial in q]
        q_minus = [
            shift_polynomial(polynomial, elapsed) for polynomial in q_minus
        ]
        time += elapsed
        threshold = tolerance * max(1.0, abs(time), abs(elapsed))
        due = [
            index
            for index, crossing in enumerate(crossings)
            if abs(crossing - elapsed) <= threshold
        ]
        if not due:
            raise IntegrationError(
                f"{method} failed to identify the imminent quantizer"
            )

        current_values = [polynomial[0] for polynomial in x]
        x, rhs_coefficients, matrix, used = _linearised_dynamics(
            problem,
            time,
            current_values,
            q,
            order,
            finite_difference_step,
            jacobian,
            jacobian_delta,
        )
        evaluations += used
        candidates = {
            index: _liqss_candidate(
                index, x, q, rhs_coefficients, matrix, quanta[index], order
            )
            for index in due
        }
        updated = set(due)
        if modified:
            candidates, updated = _apply_modified_pairs(
                due,
                candidates,
                x,
                q,
                rhs_coefficients,
                matrix,
                quanta,
                order,
                problem.t_bound - time,
                coupling_delta,
            )
        if events + len(updated) > event_limit:
            raise IntegrationError(f"{method} exceeded max_events")
        for index in updated:
            q[index] = candidates[index]
            q_minus[index] = [x[index][0], *q[index][1:]]

        x, rhs_coefficients, matrix, used = _linearised_dynamics(
            problem,
            time,
            current_values,
            q,
            order,
            finite_difference_step,
            jacobian,
            jacobian_delta,
        )
        evaluations += used
        events += len(updated)
        times.append(time)
        states.append(tuple(current_values))

    return IntegrationResult(
        method,
        tuple(times),
        tuple(states),
        SolverStats(events, 0, evaluations),
    )


def _generalised_liqss_family(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    order: int,
    family: str,
    method: str,
    jacobian: Jacobian | None,
    jacobian_step: float,
    max_events: int,
    simultaneous_tolerance: float,
    derivative_step: float | None,
) -> IntegrationResult:
    """Integrate with the extended or Chebyshev LIQSS quantizer policy."""

    if family not in {"extended", "chebyshev"}:
        raise ValueError("unknown generalized LIQSS family")
    event_limit, tolerance, finite_difference_step = _validate_common_controls(
        problem,
        max_events,
        simultaneous_tolerance,
        derivative_step,
        method=method,
    )
    if isinstance(jacobian_step, bool):
        raise TypeError("jacobian_step must be a real number")
    jacobian_delta = float(jacobian_step)
    if not math.isfinite(jacobian_delta) or jacobian_delta <= 0.0:
        raise ValueError("jacobian_step must be positive and finite")

    quanta = _quantum_vector(quantum, problem.dimension)
    time = problem.t0
    q, x, evaluations = _bootstrap_explicit_polynomials(
        problem, time, problem.y0, order, finite_difference_step
    )
    x, rhs_coefficients, matrix, used = _linearised_dynamics(
        problem,
        time,
        problem.y0,
        q,
        order,
        finite_difference_step,
        jacobian,
        jacobian_delta,
    )
    evaluations += used

    next_self = [math.inf] * problem.dimension
    for index in range(problem.dimension):
        candidate, horizon = _generalised_liqss_candidate(
            index,
            x,
            q,
            rhs_coefficients,
            matrix,
            quanta[index],
            order,
            family,
        )
        q[index] = candidate
        if math.isfinite(horizon):
            next_self[index] = time + horizon

    x, rhs_coefficients, matrix, used = _linearised_dynamics(
        problem,
        time,
        problem.y0,
        q,
        order,
        finite_difference_step,
        jacobian,
        jacobian_delta,
    )
    evaluations += used

    times = [time]
    states = [tuple(problem.y0)]
    events = 0
    guard_multiplier = 1.001
    while time < problem.t_bound:
        if events >= event_limit:
            raise IntegrationError(f"{method} exceeded max_events")
        remaining = problem.t_bound - time
        root_tolerance = tolerance * max(1.0, abs(time))
        crossings: list[float] = []
        for index in range(problem.dimension):
            scheduled = next_self[index] - time
            if scheduled < 0.0:
                scheduled = 0.0
            guard = _boundary_time(
                x[index],
                q[index],
                guard_multiplier * quanta[index],
                remaining,
                root_tolerance,
            )
            crossings.append(min(scheduled, guard))

        elapsed = min(crossings)
        if math.isinf(elapsed) or elapsed >= remaining:
            final_state = _finite_state(
                [evaluate_polynomial(polynomial, remaining) for polynomial in x],
                method=method,
            )
            time = problem.t_bound
            times.append(time)
            states.append(tuple(final_state))
            break

        x = [shift_polynomial(polynomial, elapsed) for polynomial in x]
        q = [shift_polynomial(polynomial, elapsed) for polynomial in q]
        time += elapsed
        threshold = tolerance * max(1.0, abs(time), abs(elapsed))
        due = [
            index
            for index, crossing in enumerate(crossings)
            if abs(crossing - elapsed) <= threshold
        ]
        if not due:
            raise IntegrationError(
                f"{method} failed to identify the imminent quantizer"
            )
        if events + len(due) > event_limit:
            raise IntegrationError(f"{method} exceeded max_events")

        current_values = [polynomial[0] for polynomial in x]
        x, rhs_coefficients, matrix, used = _linearised_dynamics(
            problem,
            time,
            current_values,
            q,
            order,
            finite_difference_step,
            jacobian,
            jacobian_delta,
        )
        evaluations += used
        updates: dict[int, tuple[list[float], float]] = {}
        for index in due:
            updates[index] = _generalised_liqss_candidate(
                index,
                x,
                q,
                rhs_coefficients,
                matrix,
                quanta[index],
                order,
                family,
            )
        for index, (candidate, horizon) in updates.items():
            q[index] = candidate
            next_self[index] = (
                time + horizon if math.isfinite(horizon) else math.inf
            )

        x, rhs_coefficients, matrix, used = _linearised_dynamics(
            problem,
            time,
            current_values,
            q,
            order,
            finite_difference_step,
            jacobian,
            jacobian_delta,
        )
        evaluations += used
        events += len(due)
        times.append(time)
        states.append(tuple(current_values))

    return IntegrationResult(
        method,
        tuple(times),
        tuple(states),
        SolverStats(events, 0, evaluations),
    )


def liqss1(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """First-order linearly implicit QSS with a diagonal local Jacobian."""

    return _liqss_family(
        problem,
        quantum,
        order=1,
        modified=False,
        method="liqss1",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        coupling_tolerance=0.0,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def liqss2(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Second-order linearly implicit QSS."""

    return _liqss_family(
        problem,
        quantum,
        order=2,
        modified=False,
        method="liqss2",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        coupling_tolerance=0.0,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def liqss3(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Third-order linearly implicit QSS."""

    return _liqss_family(
        problem,
        quantum,
        order=3,
        modified=False,
        method="liqss3",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        coupling_tolerance=0.0,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def eliqss1(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """First-order extended LIQSS; equivalent to first-order CheQSS."""

    return _generalised_liqss_family(
        problem,
        quantum,
        order=1,
        family="extended",
        method="eliqss1",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def eliqss2(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Second-order extended LIQSS with the full-quantum update policy."""

    return _generalised_liqss_family(
        problem,
        quantum,
        order=2,
        family="extended",
        method="eliqss2",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def eliqss3(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Third-order extended LIQSS with the full-quantum update policy."""

    return _generalised_liqss_family(
        problem,
        quantum,
        order=3,
        family="extended",
        method="eliqss3",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def cheqss1(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """First-order Chebyshev LIQSS; equivalent to first-order eLIQSS."""

    return _generalised_liqss_family(
        problem,
        quantum,
        order=1,
        family="chebyshev",
        method="cheqss1",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def cheqss2(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Second-order CheQSS with a minimax difference polynomial."""

    return _generalised_liqss_family(
        problem,
        quantum,
        order=2,
        family="chebyshev",
        method="cheqss2",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def cheqss3(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Third-order CheQSS with a minimax difference polynomial."""

    return _generalised_liqss_family(
        problem,
        quantum,
        order=3,
        family="chebyshev",
        method="cheqss3",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def mliqss1(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    coupling_tolerance: float = 1e-12,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """First-order modified LIQSS with coupled two-state implicit updates."""

    return _liqss_family(
        problem,
        quantum,
        order=1,
        modified=True,
        method="mliqss1",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        coupling_tolerance=coupling_tolerance,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def mliqss2(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    coupling_tolerance: float = 1e-12,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Second-order modified LIQSS with coupled polynomial updates."""

    return _liqss_family(
        problem,
        quantum,
        order=2,
        modified=True,
        method="mliqss2",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        coupling_tolerance=coupling_tolerance,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


def mliqss3(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    coupling_tolerance: float = 1e-12,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1e-12,
    derivative_step: float | None = None,
) -> IntegrationResult:
    """Third-order modified LIQSS using future value/derivative matching."""

    return _liqss_family(
        problem,
        quantum,
        order=3,
        modified=True,
        method="mliqss3",
        jacobian=jacobian,
        jacobian_step=jacobian_step,
        coupling_tolerance=coupling_tolerance,
        max_events=max_events,
        simultaneous_tolerance=simultaneous_tolerance,
        derivative_step=derivative_step,
    )


# Common engine spellings and the CIFASIS ``EQSS`` compatibility spelling.
liqss = liqss1
mliqss = mliqss1
eliqss = eliqss1
cheqss = cheqss1
eqss = eliqss1
eqss1 = eliqss1
eqss2 = eliqss2
eqss3 = eliqss3


__all__ = [
    "Jacobian",
    "cheqss",
    "cheqss1",
    "cheqss2",
    "cheqss3",
    "eliqss",
    "eliqss1",
    "eliqss2",
    "eliqss3",
    "eqss",
    "eqss1",
    "eqss2",
    "eqss3",
    "liqss",
    "liqss1",
    "liqss2",
    "liqss3",
    "mliqss",
    "mliqss1",
    "mliqss2",
    "mliqss3",
    "qss3",
    "qss4",
]
