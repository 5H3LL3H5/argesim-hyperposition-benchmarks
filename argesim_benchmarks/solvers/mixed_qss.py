"""Mixed state/time-discretized LIQSS2-BDF integration.

The published LIQSS-BDF method partitions the state vector: one partition is
advanced asynchronously with LIQSS2, while a classic backward-difference
method advances the other partition.  Linear interface polynomials exchange
the two trajectories at every accepted BDF macro step.  This module is an
independent, dependency-free reference implementation of that coordination
scheme; it does not wrap CVODE or source from the CIFASIS engine.
"""

from __future__ import annotations

import math
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..ivp import (
    InitialValueProblem,
    IntegrationError,
    IntegrationResult,
    SolverStats,
)
from ._polynomial import (
    evaluate_polynomial,
    first_positive_root,
    shift_polynomial,
    solve_linear_system,
)
from .advanced_qss import (
    Jacobian,
    _bootstrap_explicit_polynomials,
    _boundary_time,
    _estimated_derivative_polynomial,
    _input_coefficients,
    _linearised_dynamics,
    _liqss_candidate,
)
from .qss import _finite_state, _positive_integer, _quantum_vector


class _StepFailure(RuntimeError):
    """Signal that a smaller BDF macro step may recover the integration."""


@dataclass(frozen=True)
class _Liqss2State:
    """Persistent LIQSS2 quantizer polynomials anchored at a macro boundary."""

    q: tuple[tuple[float, float], ...]
    q_minus: tuple[tuple[float, float], ...]


def _positive_finite(value: float, *, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be positive and finite")
    return result


def _non_negative_finite(value: float, *, name: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number")
    result = float(value)
    if not math.isfinite(result) or result < 0.0:
        raise ValueError(f"{name} must be finite and non-negative")
    return result


def _tolerance_vector(
    value: float | Sequence[float],
    dimension: int,
    *,
    name: str,
) -> tuple[float, ...]:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be a real number or numeric sequence")
    if isinstance(value, (int, float)):
        values = (float(value),) * dimension
    else:
        raw = tuple(value)
        if any(isinstance(component, bool) for component in raw):
            raise TypeError(f"{name} values must be real numbers, not bool")
        if len(raw) != dimension:
            raise ValueError(f"{name} dimension does not match the problem")
        values = tuple(float(component) for component in raw)
    if not all(
        math.isfinite(component) and component > 0.0
        for component in values
    ):
        raise ValueError(f"all {name} values must be positive and finite")
    return values


def _partition_indices(
    partition: Sequence[int] | None,
    dimension: int,
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    if partition is None:
        bdf = tuple(range(dimension))
    else:
        raw = tuple(partition)
        if not raw:
            raise ValueError("bdf_partition must contain at least one state index")
        if any(not isinstance(index, int) or isinstance(index, bool) for index in raw):
            raise TypeError("bdf_partition must contain integer state indices")
        if len(set(raw)) != len(raw):
            raise ValueError("bdf_partition must not contain duplicate indices")
        if any(index < 0 or index >= dimension for index in raw):
            raise ValueError("bdf_partition index is outside the state vector")
        bdf = tuple(sorted(raw))
    bdf_set = set(bdf)
    qss = tuple(index for index in range(dimension) if index not in bdf_set)
    return bdf, qss


def _validated_full_jacobian(
    jacobian: Jacobian,
    time: float,
    state: Sequence[float],
    dimension: int,
) -> list[list[float]]:
    try:
        rows = tuple(tuple(row) for row in jacobian(time, state))
    except TypeError as exc:
        raise TypeError("jacobian must return a square numeric matrix") from exc
    if len(rows) != dimension or any(len(row) != dimension for row in rows):
        raise ValueError("jacobian dimensions do not match the problem")
    try:
        result = [[float(value) for value in row] for row in rows]
    except (TypeError, ValueError) as exc:
        raise TypeError("jacobian must return a square numeric matrix") from exc
    if not all(math.isfinite(value) for row in result for value in row):
        raise IntegrationError("jacobian returned a non-finite value")
    return result


def _bdf_jacobian_block(
    problem: InitialValueProblem,
    time: float,
    state: Sequence[float],
    bdf_indices: Sequence[int],
    jacobian: Jacobian | None,
    jacobian_step: float,
) -> tuple[list[list[float]], int]:
    if jacobian is not None:
        matrix = _validated_full_jacobian(
            jacobian, time, state, problem.dimension
        )
        return (
            [[matrix[row][column] for column in bdf_indices] for row in bdf_indices],
            0,
        )

    block = [[0.0] * len(bdf_indices) for _ in bdf_indices]
    evaluations = 0
    for local_column, state_column in enumerate(bdf_indices):
        step = jacobian_step * max(1.0, abs(state[state_column]))
        plus = list(state)
        minus = list(state)
        plus[state_column] += step
        minus[state_column] -= step
        f_plus = problem.evaluate(time, plus)
        f_minus = problem.evaluate(time, minus)
        evaluations += 2
        for local_row, state_row in enumerate(bdf_indices):
            block[local_row][local_column] = (
                f_plus[state_row] - f_minus[state_row]
            ) / (2.0 * step)
    return block, evaluations


def _residual_norm(
    residual: Sequence[float],
    alpha: float,
    values: Sequence[float],
    constant: Sequence[float],
    step: float,
    derivative: Sequence[float],
) -> float:
    scaled = [
        abs(component)
        / max(
            1.0,
            abs(alpha * value),
            abs(offset),
            abs(step * slope),
        )
        for component, value, offset, slope in zip(
            residual, values, constant, derivative
        )
    ]
    return max(scaled, default=0.0)


def _implicit_bdf_partition(
    problem: InitialValueProblem,
    time: float,
    step: float,
    template: Sequence[float],
    bdf_indices: Sequence[int],
    initial: Sequence[float],
    *,
    alpha: float,
    constant: Sequence[float],
    jacobian: Jacobian | None,
    jacobian_step: float,
    max_newton_iterations: int,
    newton_tolerance: float,
) -> tuple[tuple[float, ...], int]:
    values = [float(value) for value in initial]
    evaluations = 0

    def evaluate(candidate: Sequence[float]) -> tuple[list[float], list[float]]:
        state = list(template)
        for index, value in zip(bdf_indices, candidate):
            state[index] = value
        derivative = problem.evaluate(time, state)
        local_derivative = [derivative[index] for index in bdf_indices]
        residual = [
            alpha * value + offset - step * slope
            for value, offset, slope in zip(candidate, constant, local_derivative)
        ]
        return residual, local_derivative

    residual, derivative = evaluate(values)
    evaluations += 1
    for _ in range(max_newton_iterations):
        norm = _residual_norm(
            residual, alpha, values, constant, step, derivative
        )
        if norm <= newton_tolerance:
            state = list(template)
            for index, value in zip(bdf_indices, values):
                state[index] = value
            result = _finite_state(state, method="liqss-bdf Newton solve")
            return tuple(result), evaluations

        state = list(template)
        for index, value in zip(bdf_indices, values):
            state[index] = value
        block, used = _bdf_jacobian_block(
            problem,
            time,
            state,
            bdf_indices,
            jacobian,
            jacobian_step,
        )
        evaluations += used
        system = [
            [
                (alpha if row == column else 0.0) - step * block[row][column]
                for column in range(len(bdf_indices))
            ]
            for row in range(len(bdf_indices))
        ]
        try:
            correction = solve_linear_system(system, [-value for value in residual])
        except IntegrationError as exc:
            raise _StepFailure("singular BDF Newton matrix") from exc

        accepted = False
        damping = 1.0
        for _ in range(8):
            trial = [
                value + damping * change
                for value, change in zip(values, correction)
            ]
            if not all(math.isfinite(value) for value in trial):
                damping *= 0.5
                continue
            trial_residual, trial_derivative = evaluate(trial)
            evaluations += 1
            trial_norm = _residual_norm(
                trial_residual,
                alpha,
                trial,
                constant,
                step,
                trial_derivative,
            )
            if trial_norm < norm or trial_norm <= newton_tolerance:
                values = trial
                residual = trial_residual
                derivative = trial_derivative
                accepted = True
                break
            damping *= 0.5
        if not accepted:
            raise _StepFailure("BDF Newton line search did not converge")
    raise _StepFailure("BDF Newton iteration did not converge")


def _reduced_qss_problem(
    problem: InitialValueProblem,
    time: float,
    step: float,
    start: Sequence[float],
    bdf_endpoint: Sequence[float],
    qss_indices: Sequence[int],
    bdf_indices: Sequence[int],
) -> InitialValueProblem:
    qss_initial = tuple(start[index] for index in qss_indices)

    def full_state(local_time: float, qss_state: Sequence[float]) -> list[float]:
        theta = (local_time - time) / step
        state = list(start)
        for index, value in zip(qss_indices, qss_state):
            state[index] = value
        for index in bdf_indices:
            state[index] = start[index] + theta * (
                bdf_endpoint[index] - start[index]
            )
        return state

    def rhs(local_time: float, qss_state: Sequence[float]) -> tuple[float, ...]:
        derivative = problem.evaluate(local_time, full_state(local_time, qss_state))
        return tuple(derivative[index] for index in qss_indices)

    # LIQSS2's event loop accepts autonomous problems.  Time enters here only
    # through the published, known interface polynomial, not an unscheduled
    # external input.
    return InitialValueProblem(
        rhs,
        time,
        qss_initial,
        time + step,
        name=f"{problem.name}-liqss-partition",
        autonomous=True,
    )


def _reduced_jacobian(
    jacobian: Jacobian,
    problem: InitialValueProblem,
    time: float,
    step: float,
    start: Sequence[float],
    bdf_endpoint: Sequence[float],
    qss_indices: Sequence[int],
    bdf_indices: Sequence[int],
) -> Callable[[float, Sequence[float]], tuple[tuple[float, ...], ...]]:
    def evaluate(
        local_time: float, qss_state: Sequence[float]
    ) -> tuple[tuple[float, ...], ...]:
        theta = (local_time - time) / step
        state = list(start)
        for index, value in zip(qss_indices, qss_state):
            state[index] = value
        for index in bdf_indices:
            state[index] = start[index] + theta * (
                bdf_endpoint[index] - start[index]
            )
        matrix = _validated_full_jacobian(
            jacobian, local_time, state, problem.dimension
        )
        return tuple(
            tuple(matrix[row][column] for column in qss_indices)
            for row in qss_indices
        )

    return evaluate


def _advance_qss_partition(
    problem: InitialValueProblem,
    time: float,
    step: float,
    start: Sequence[float],
    bdf_endpoint: Sequence[float],
    qss_indices: Sequence[int],
    bdf_indices: Sequence[int],
    quanta: Sequence[float],
    quantizer_state: _Liqss2State | None,
    *,
    jacobian: Jacobian | None,
    jacobian_step: float,
    max_events: int,
    simultaneous_tolerance: float,
    derivative_step: float | None,
) -> tuple[tuple[float, ...], _Liqss2State | None, int, int]:
    if not qss_indices:
        return tuple(start), None, 0, 0
    reduced_problem = _reduced_qss_problem(
        problem,
        time,
        step,
        start,
        bdf_endpoint,
        qss_indices,
        bdf_indices,
    )
    reduced_jacobian = None
    if jacobian is not None:
        reduced_jacobian = _reduced_jacobian(
            jacobian,
            problem,
            time,
            step,
            start,
            bdf_endpoint,
            qss_indices,
            bdf_indices,
        )
    local_quanta = tuple(quanta[index] for index in qss_indices)
    current_values = [start[index] for index in qss_indices]
    evaluations = 0

    if quantizer_state is None:
        q, x, used = _bootstrap_explicit_polynomials(
            reduced_problem,
            time,
            current_values,
            2,
            derivative_step,
        )
        evaluations += used
        x, rhs_coefficients, matrix, used = _linearised_dynamics(
            reduced_problem,
            time,
            current_values,
            q,
            2,
            derivative_step,
            reduced_jacobian,
            jacobian_step,
        )
        evaluations += used
        for index in range(len(qss_indices)):
            q[index] = _liqss_candidate(
                index,
                x,
                q,
                rhs_coefficients,
                matrix,
                local_quanta[index],
                2,
            )
        q_minus = [
            [x[index][0], q[index][1]]
            for index in range(len(qss_indices))
        ]
    else:
        if (
            len(quantizer_state.q) != len(qss_indices)
            or len(quantizer_state.q_minus) != len(qss_indices)
        ):
            raise IntegrationError("LIQSS-BDF quantizer state dimension changed")
        q = [list(polynomial) for polynomial in quantizer_state.q]
        q_minus = [
            list(polynomial) for polynomial in quantizer_state.q_minus
        ]

    x, rhs_coefficients, matrix, used = _linearised_dynamics(
        reduced_problem,
        time,
        current_values,
        q,
        2,
        derivative_step,
        reduced_jacobian,
        jacobian_step,
    )
    evaluations += used

    local_time = time
    end_time = time + step
    events = 0
    while local_time < end_time:
        if events >= max_events:
            raise IntegrationError("liqss-bdf exceeded max_events")
        remaining = end_time - local_time
        root_tolerance = simultaneous_tolerance * max(1.0, abs(local_time))
        crossings: list[float] = []
        for index in range(len(qss_indices)):
            boundary = _boundary_time(
                x[index],
                q_minus[index],
                local_quanta[index],
                remaining,
                root_tolerance,
            )
            inputs = _input_coefficients(
                index, q, rhs_coefficients, matrix, 2
            )
            estimate = _estimated_derivative_polynomial(
                matrix[index][index], q[index], inputs, 2
            )
            direction_change = first_positive_root(
                estimate,
                remaining,
                time_tolerance=root_tolerance,
            )
            crossings.append(min(boundary, direction_change))

        elapsed = min(crossings)
        if math.isinf(elapsed) or elapsed >= remaining:
            current_values = _finite_state(
                [
                    evaluate_polynomial(polynomial, remaining)
                    for polynomial in x
                ],
                method="liqss-bdf LIQSS2 partition",
            )
            q = [shift_polynomial(polynomial, remaining) for polynomial in q]
            q_minus = [
                shift_polynomial(polynomial, remaining)
                for polynomial in q_minus
            ]
            local_time = end_time
            break

        x = [shift_polynomial(polynomial, elapsed) for polynomial in x]
        q = [shift_polynomial(polynomial, elapsed) for polynomial in q]
        q_minus = [
            shift_polynomial(polynomial, elapsed) for polynomial in q_minus
        ]
        local_time += elapsed
        threshold = simultaneous_tolerance * max(
            1.0, abs(local_time), abs(elapsed)
        )
        due = [
            index
            for index, crossing in enumerate(crossings)
            if abs(crossing - elapsed) <= threshold
        ]
        if not due:
            raise IntegrationError(
                "liqss-bdf failed to identify the imminent LIQSS2 quantizer"
            )
        if events + len(due) > max_events:
            raise IntegrationError("liqss-bdf exceeded max_events")

        current_values = [polynomial[0] for polynomial in x]
        x, rhs_coefficients, matrix, used = _linearised_dynamics(
            reduced_problem,
            local_time,
            current_values,
            q,
            2,
            derivative_step,
            reduced_jacobian,
            jacobian_step,
        )
        evaluations += used
        for index in due:
            q[index] = _liqss_candidate(
                index,
                x,
                q,
                rhs_coefficients,
                matrix,
                local_quanta[index],
                2,
            )
            q_minus[index] = [x[index][0], q[index][1]]
        x, rhs_coefficients, matrix, used = _linearised_dynamics(
            reduced_problem,
            local_time,
            current_values,
            q,
            2,
            derivative_step,
            reduced_jacobian,
            jacobian_step,
        )
        evaluations += used
        events += len(due)

    state = list(bdf_endpoint)
    for index, value in zip(qss_indices, current_values):
        state[index] = value
    persisted = _Liqss2State(
        tuple(tuple(polynomial) for polynomial in q),
        tuple(tuple(polynomial) for polynomial in q_minus),
    )
    return tuple(state), persisted, events, evaluations


def _coupling_norm(
    previous: Sequence[float],
    current: Sequence[float],
    qss_indices: Sequence[int],
    quanta: Sequence[float],
    atols: Sequence[float],
    rtol: float,
) -> float:
    qss_set = set(qss_indices)
    scaled = []
    for index, (before, after) in enumerate(zip(previous, current)):
        absolute = quanta[index] if index in qss_set else atols[index]
        scale = absolute + rtol * max(abs(before), abs(after))
        scaled.append(abs(after - before) / scale)
    return max(scaled, default=0.0)


def _mixed_endpoint(
    problem: InitialValueProblem,
    time: float,
    step: float,
    start: Sequence[float],
    previous: Sequence[float] | None,
    previous_step: float | None,
    bdf_indices: Sequence[int],
    qss_indices: Sequence[int],
    quanta: Sequence[float],
    atols: Sequence[float],
    rtol: float,
    predictor: Sequence[float],
    quantizer_state: _Liqss2State | None,
    *,
    force_euler: bool,
    jacobian: Jacobian | None,
    jacobian_step: float,
    max_newton_iterations: int,
    newton_tolerance: float,
    max_coupling_iterations: int,
    coupling_tolerance: float,
    max_events: int,
    simultaneous_tolerance: float,
    derivative_step: float | None,
) -> tuple[tuple[float, ...], _Liqss2State | None, int, int]:
    if force_euler or previous is None or previous_step is None:
        alpha = 1.0
        constant = [-start[index] for index in bdf_indices]
    else:
        ratio = step / previous_step
        alpha = (1.0 + 2.0 * ratio) / (1.0 + ratio)
        constant = [
            -(1.0 + ratio) * start[index]
            + ratio * ratio / (1.0 + ratio) * previous[index]
            for index in bdf_indices
        ]

    estimate = tuple(float(value) for value in predictor)
    evaluations = 0
    last_qss_events = 0
    last_quantizer_state = quantizer_state
    for _ in range(max_coupling_iterations):
        with_qss, trial_quantizer_state, qss_events, used = (
            _advance_qss_partition(
                problem,
                time,
                step,
                start,
                estimate,
                qss_indices,
                bdf_indices,
                quanta,
                quantizer_state,
                jacobian=jacobian,
                jacobian_step=jacobian_step,
                max_events=max_events,
                simultaneous_tolerance=simultaneous_tolerance,
                derivative_step=derivative_step,
            )
        )
        evaluations += used
        initial = [estimate[index] for index in bdf_indices]
        try:
            candidate, used = _implicit_bdf_partition(
                problem,
                time + step,
                step,
                with_qss,
                bdf_indices,
                initial,
                alpha=alpha,
                constant=constant,
                jacobian=jacobian,
                jacobian_step=jacobian_step,
                max_newton_iterations=max_newton_iterations,
                newton_tolerance=newton_tolerance,
            )
        except _StepFailure:
            raise
        evaluations += used
        last_qss_events = qss_events
        last_quantizer_state = trial_quantizer_state
        if not qss_indices:
            return candidate, None, 0, evaluations
        if _coupling_norm(
            estimate,
            candidate,
            qss_indices,
            quanta,
            atols,
            rtol,
        ) <= coupling_tolerance:
            return (
                candidate,
                last_quantizer_state,
                last_qss_events,
                evaluations,
            )
        estimate = candidate
    raise _StepFailure("LIQSS-BDF interface iteration did not converge")


def _error_norm(
    high: Sequence[float],
    low: Sequence[float],
    old: Sequence[float],
    qss_indices: Sequence[int],
    quanta: Sequence[float],
    atols: Sequence[float],
    rtol: float,
) -> float:
    qss_set = set(qss_indices)
    scaled = []
    for index, (accurate, estimate, previous) in enumerate(
        zip(high, low, old)
    ):
        absolute = quanta[index] if index in qss_set else atols[index]
        scale = absolute + rtol * max(abs(previous), abs(accurate))
        scaled.append((accurate - estimate) / scale)
    result = math.sqrt(sum(value * value for value in scaled) / len(scaled))
    if not math.isfinite(result):
        raise IntegrationError("liqss-bdf produced a non-finite error estimate")
    return result


def liqss_bdf(
    problem: InitialValueProblem,
    quantum: float | Sequence[float],
    *,
    bdf_partition: Sequence[int] | None = None,
    jacobian: Jacobian | None = None,
    jacobian_step: float = math.sqrt(sys.float_info.epsilon),
    rtol: float = 1.0e-6,
    atol: float | Sequence[float] = 1.0e-9,
    initial_step: float | None = None,
    min_step: float = 1.0e-14,
    max_step: float = math.inf,
    max_steps: int = 1_000_000,
    max_events: int = 1_000_000,
    simultaneous_tolerance: float = 1.0e-12,
    derivative_step: float | None = None,
    max_newton_iterations: int = 12,
    newton_tolerance: float = 1.0e-10,
    max_coupling_iterations: int = 12,
    coupling_tolerance: float = 0.1,
) -> IntegrationResult:
    """Integrate with a partitioned LIQSS2 and variable-step BDF1/BDF2 method.

    ``bdf_partition`` contains zero-based state indices advanced by BDF.  Its
    complement is advanced by LIQSS2.  ``None`` selects every state for BDF,
    the deterministic automatic choice when this IVP contract contains no
    event metadata from which a hybrid partition could be inferred.

    The first accepted macro step uses backward Euler; subsequent steps use
    variable-step BDF2.  A linear waveform-relaxation interface couples both
    partitions.  The QSS complement may depend on time only through that
    interface, so a genuinely non-autonomous problem is supported only when
    all states belong to the BDF partition.
    """

    if not isinstance(problem, InitialValueProblem):
        raise TypeError("problem must be InitialValueProblem")
    bdf_indices, qss_indices = _partition_indices(
        bdf_partition, problem.dimension
    )
    if qss_indices and not problem.autonomous:
        raise ValueError(
            "partial liqss-bdf requires problem.autonomous=True; "
            "schedule external input changes as separate segments"
        )
    quanta = _quantum_vector(quantum, problem.dimension)
    relative_tolerance = _positive_finite(rtol, name="rtol")
    absolute_tolerances = _tolerance_vector(
        atol, problem.dimension, name="atol"
    )
    jacobian_delta = _positive_finite(jacobian_step, name="jacobian_step")
    minimum_step = _positive_finite(min_step, name="min_step")
    if isinstance(max_step, bool):
        raise TypeError("max_step must be a real number")
    maximum_step = float(max_step)
    if math.isnan(maximum_step) or maximum_step <= 0.0:
        raise ValueError("max_step must be positive")
    if minimum_step > maximum_step:
        raise ValueError("min_step must not exceed max_step")
    step_limit = _positive_integer(max_steps, name="max_steps")
    event_limit = _positive_integer(max_events, name="max_events")
    newton_limit = _positive_integer(
        max_newton_iterations, name="max_newton_iterations"
    )
    coupling_limit = _positive_integer(
        max_coupling_iterations, name="max_coupling_iterations"
    )
    newton_delta = _positive_finite(
        newton_tolerance, name="newton_tolerance"
    )
    coupling_delta = _positive_finite(
        coupling_tolerance, name="coupling_tolerance"
    )
    simultaneous_delta = _non_negative_finite(
        simultaneous_tolerance, name="simultaneous_tolerance"
    )
    if derivative_step is not None:
        _positive_finite(derivative_step, name="derivative_step")
    if jacobian is not None and not callable(jacobian):
        raise TypeError("jacobian must be callable")

    span = problem.t_bound - problem.t0
    time = problem.t0
    state = tuple(problem.y0)
    if jacobian is not None:
        _validated_full_jacobian(
            jacobian, time, state, problem.dimension
        )
    initial_derivative = problem.evaluate(time, state)
    evaluations = 1
    if initial_step is None:
        scales = [
            (
                quanta[index]
                if index in set(qss_indices)
                else absolute_tolerances[index]
            )
            + relative_tolerance * abs(state[index])
            for index in range(problem.dimension)
        ]
        state_norm = math.sqrt(
            sum((value / scale) ** 2 for value, scale in zip(state, scales))
            / problem.dimension
        )
        derivative_norm = math.sqrt(
            sum(
                (value / scale) ** 2
                for value, scale in zip(initial_derivative, scales)
            )
            / problem.dimension
        )
        if state_norm < 1.0e-5 or derivative_norm < 1.0e-5:
            step = min(1.0e-6, span / 100.0)
        else:
            step = min(0.01 * state_norm / derivative_norm, span / 100.0)
    else:
        step = _positive_finite(initial_step, name="initial_step")
    step = min(step, maximum_step, span)

    times = [time]
    states = [state]
    previous: tuple[float, ...] | None = None
    previous_step: float | None = None
    accepted = 0
    rejected = 0
    accepted_qss_events = 0
    quantizer_state: _Liqss2State | None = None

    while time < problem.t_bound:
        if accepted + rejected >= step_limit:
            raise IntegrationError("liqss-bdf exceeded max_steps")
        step = min(step, maximum_step, problem.t_bound - time)
        if step < minimum_step or time + step == time:
            raise IntegrationError("liqss-bdf required a step below min_step")
        predictor = tuple(
            value + step * slope
            for value, slope in zip(state, initial_derivative)
        )
        remaining_events = event_limit - accepted_qss_events
        if remaining_events <= 0 and qss_indices:
            raise IntegrationError("liqss-bdf exceeded max_events")

        try:
            high, high_quantizer_state, qss_events, used = _mixed_endpoint(
                problem,
                time,
                step,
                state,
                previous,
                previous_step,
                bdf_indices,
                qss_indices,
                quanta,
                absolute_tolerances,
                relative_tolerance,
                predictor,
                quantizer_state,
                force_euler=previous is None,
                jacobian=jacobian,
                jacobian_step=jacobian_delta,
                max_newton_iterations=newton_limit,
                newton_tolerance=newton_delta,
                max_coupling_iterations=coupling_limit,
                coupling_tolerance=coupling_delta,
                max_events=remaining_events,
                simultaneous_tolerance=simultaneous_delta,
                derivative_step=derivative_step,
            )
            evaluations += used
            if previous is None:
                low = predictor
            else:
                low, _low_quantizer_state, _low_events, used = _mixed_endpoint(
                    problem,
                    time,
                    step,
                    state,
                    previous,
                    previous_step,
                    bdf_indices,
                    qss_indices,
                    quanta,
                    absolute_tolerances,
                    relative_tolerance,
                    high,
                    quantizer_state,
                    force_euler=True,
                    jacobian=jacobian,
                    jacobian_step=jacobian_delta,
                    max_newton_iterations=newton_limit,
                    newton_tolerance=newton_delta,
                    max_coupling_iterations=coupling_limit,
                    coupling_tolerance=coupling_delta,
                    max_events=remaining_events,
                    simultaneous_tolerance=simultaneous_delta,
                    derivative_step=derivative_step,
                )
                evaluations += used
            error = _error_norm(
                high,
                low,
                state,
                qss_indices,
                quanta,
                absolute_tolerances,
                relative_tolerance,
            )
        except _StepFailure:
            rejected += 1
            step *= 0.25
            continue

        if error <= 1.0:
            old_state = state
            old_time = time
            time = min(problem.t_bound, time + step)
            state = high
            quantizer_state = high_quantizer_state
            previous = old_state
            previous_step = time - old_time
            times.append(time)
            states.append(state)
            accepted += 1
            accepted_qss_events += qss_events
            initial_derivative = problem.evaluate(time, state)
            evaluations += 1
            factor = 2.0 if error == 0.0 else min(2.0, 0.9 * error**-0.5)
            step *= max(0.2, factor)
        else:
            rejected += 1
            step *= max(0.2, 0.9 * error**-0.5)

    return IntegrationResult(
        method="liqss-bdf",
        times=tuple(times),
        states=tuple(states),
        stats=SolverStats(
            accepted + accepted_qss_events,
            rejected,
            evaluations,
        ),
    )


liqssbdf = liqss_bdf


__all__ = ["liqss_bdf", "liqssbdf"]
