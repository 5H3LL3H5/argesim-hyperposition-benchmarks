"""Method-of-lines reference models for PDE solver validation."""

from __future__ import annotations

import math
from collections.abc import Sequence

from .ivp import InitialValueProblem


def _validate_grid(interior_points: int, length: float) -> tuple[int, float, float]:
    if not isinstance(interior_points, int) or isinstance(interior_points, bool):
        raise TypeError("interior_points must be an integer")
    if interior_points < 1:
        raise ValueError("interior_points must be positive")
    domain_length = float(length)
    if not math.isfinite(domain_length) or domain_length <= 0.0:
        raise ValueError("length must be positive and finite")
    return interior_points, domain_length, domain_length / (interior_points + 1)


def heat_sine_initial(
    interior_points: int,
    *,
    length: float = 1.0,
) -> tuple[float, ...]:
    count, domain_length, spacing = _validate_grid(interior_points, length)
    return tuple(
        math.sin(math.pi * (index + 1) * spacing / domain_length)
        for index in range(count)
    )


def heat_sine_exact(
    interior_points: int,
    time: float,
    *,
    diffusivity: float = 1.0,
    length: float = 1.0,
) -> tuple[float, ...]:
    initial = heat_sine_initial(interior_points, length=length)
    decay = math.exp(-float(diffusivity) * (math.pi / float(length)) ** 2 * float(time))
    return tuple(decay * value for value in initial)


def heat_1d_ivp(
    initial: Sequence[float],
    t_bound: float,
    *,
    diffusivity: float = 1.0,
    length: float = 1.0,
    left_boundary: float = 0.0,
    right_boundary: float = 0.0,
) -> InitialValueProblem:
    state = tuple(float(value) for value in initial)
    count, _, spacing = _validate_grid(len(state), length)
    alpha = float(diffusivity)
    if not math.isfinite(alpha) or alpha <= 0.0:
        raise ValueError("diffusivity must be positive and finite")
    left = float(left_boundary)
    right = float(right_boundary)
    coefficient = alpha / (spacing * spacing)

    def rhs(_time: float, values: Sequence[float]) -> tuple[float, ...]:
        padded = (left, *values, right)
        return tuple(
            coefficient * (padded[index] - 2.0 * padded[index + 1] + padded[index + 2])
            for index in range(count)
        )

    return InitialValueProblem(
        rhs,
        0.0,
        state,
        t_bound,
        name="heat-1d-mol",
        autonomous=True,
    )


def wave_1d_ivp(
    displacement: Sequence[float],
    velocity: Sequence[float],
    t_bound: float,
    *,
    wave_speed: float = 1.0,
    length: float = 1.0,
) -> InitialValueProblem:
    u0 = tuple(float(value) for value in displacement)
    v0 = tuple(float(value) for value in velocity)
    if len(u0) != len(v0):
        raise ValueError("displacement and velocity dimensions must match")
    count, _, spacing = _validate_grid(len(u0), length)
    speed = float(wave_speed)
    if not math.isfinite(speed) or speed <= 0.0:
        raise ValueError("wave_speed must be positive and finite")
    coefficient = speed * speed / (spacing * spacing)

    def rhs(_time: float, state: Sequence[float]) -> tuple[float, ...]:
        displacement_now = state[:count]
        velocity_now = state[count:]
        padded = (0.0, *displacement_now, 0.0)
        acceleration = tuple(
            coefficient * (padded[index] - 2.0 * padded[index + 1] + padded[index + 2])
            for index in range(count)
        )
        return (*velocity_now, *acceleration)

    return InitialValueProblem(
        rhs,
        0.0,
        (*u0, *v0),
        t_bound,
        name="wave-1d-mol",
        autonomous=True,
    )
