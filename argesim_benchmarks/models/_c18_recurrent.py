"""Sequence-output least squares for the C18 two-delay tanh network."""

import math
import random
from collections.abc import Sequence
from operator import mul

from ..ivp import IntegrationError
from ..solvers._polynomial import solve_linear_system


def _sequence(
    parameters: Sequence[float],
    inputs: Sequence[float],
    targets: Sequence[float],
    *,
    derivatives: bool,
) -> tuple[list[float], list[list[float]]]:
    """Return target minus model output and, if requested, d(output)/d(weights).

    Each hidden unit has four input weights, a bias and an output weight.
    The final parameter is the linear output bias. Signals are standardized.
    Only the first two target samples initialize the feedback path.
    """
    units = [parameters[i : i + 6] for i in range(0, len(parameters) - 1, 6)]
    width = len(parameters)
    older, newer = targets[:2]
    older_gradient = newer_gradient = [0.0] * width
    residuals, jacobian = [], []
    for t in range(2, len(inputs)):
        u1, u2 = inputs[t - 1], inputs[t - 2]
        prediction = parameters[-1]
        if derivatives:
            direct = []
            delay1 = delay2 = 0.0
        for w1, w2, w3, w4, bias, output_weight in units:
            activation = math.tanh(w1 * newer + w2 * older + w3 * u1 + w4 * u2 + bias)
            prediction += output_weight * activation
            if derivatives:
                slope = output_weight * (1.0 - activation * activation)
                delay1 += slope * w1
                delay2 += slope * w2
                direct.extend(
                    (
                        slope * newer,
                        slope * older,
                        slope * u1,
                        slope * u2,
                        slope,
                        activation,
                    )
                )
        if derivatives:
            direct.append(1.0)
            gradient = [
                d + delay1 * g1 + delay2 * g2
                for d, g1, g2 in zip(direct, newer_gradient, older_gradient)
            ]
            jacobian.append(gradient)
            older_gradient, newer_gradient = newer_gradient, gradient
        residuals.append(targets[t] - prediction)
        older, newer = newer, prediction
    return residuals, jacobian


def fit_sequence(
    inputs: Sequence[float],
    targets: Sequence[float],
    *,
    hidden: int,
    epochs: int,
    seed: int,
) -> list[float]:
    """Damped Gauss–Newton on the complete training rollout.

    Scale the sensitivity columns before forming the damped normal equations.
    Reject non-improving steps and retain the last finite accepted model.
    """
    rng = random.Random(seed)
    parameters = []
    for _ in range(hidden):
        parameters.extend(rng.uniform(-0.5, 0.5) for _ in range(4))
        parameters.extend((0.0, rng.uniform(-0.2, 0.2)))
    parameters.append(0.0)
    width = len(parameters)
    root_n = math.sqrt(len(targets) - 2)
    damping = 1.0e-3
    residuals, jacobian = _sequence(parameters, inputs, targets, derivatives=True)
    cost = math.hypot(*residuals)
    if not math.isfinite(cost):
        raise ValueError("non-finite initial C18 training rollout")
    for _ in range(epochs):
        columns = list(zip(*jacobian))
        scales = [max(math.hypot(*column), root_n) for column in columns]
        if not all(map(math.isfinite, scales)) or cost == 0.0:
            break
        columns = [[v / scale for v in col] for col, scale in zip(columns, scales)]
        gram = [[0.0] * width for _ in columns]
        for i, col in enumerate(columns):
            for j in range(i + 1):
                gram[i][j] = gram[j][i] = sum(map(mul, col, columns[j]))
        rhs = [sum(map(mul, col, residuals)) for col in columns]
        for _attempt in range(12):
            system = [row.copy() for row in gram]
            for i, row in enumerate(system):
                row[i] += damping
            try:
                step = solve_linear_system(system, rhs)
            except IntegrationError:
                damping *= 10.0
                continue
            trial = [
                w + change / scale for w, change, scale in zip(parameters, step, scales)
            ]
            errors, _ = _sequence(trial, inputs, targets, derivatives=False)
            new_cost = math.hypot(*errors)
            if new_cost < cost:
                errors, sensitivities = _sequence(
                    trial, inputs, targets, derivatives=True
                )
                if all(all(map(math.isfinite, row)) for row in sensitivities):
                    parameters, residuals, jacobian = trial, errors, sensitivities
                    improvement, cost = cost - new_cost, new_cost
                    damping = max(damping / 3.0, 1.0e-12)
                    break
            damping *= 10.0
        else:
            break
        if improvement <= 1.0e-10 * max(cost, 1.0e-12):
            break
    return parameters
