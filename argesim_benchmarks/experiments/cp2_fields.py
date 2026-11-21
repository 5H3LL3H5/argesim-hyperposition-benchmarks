"""Physical inputs, reference fields and independent comparisons for the CP2 lab."""

from __future__ import annotations

from dataclasses import replace
from math import pi

import numpy as np

from ..models import cp2_parallel_and_distributed as cp2

ROPE = cp2.CP2SwingingRopeParameters()
PROFILE_TIMES = (5.0, 8.0)
ROPE_NODES = 65
CAVITY_NODES = 17
CAVITY_STEPS = 16
LID_SPEED = 0.1
REYNOLDS = 1000.0
DENSITY_SCALE = 0.02


def rope_samples(count, rng, *, nodes=ROPE_NODES):
    """Independent smooth initial shapes in metres; zero initial velocity."""
    k = np.arange(1, 9)
    basis = np.sin(pi * k[:, None] * np.linspace(0, 1, nodes))
    basis[:, [0, -1]] = 0.0
    coefficients = ROPE.h * rng.normal(size=(count, k.size)) / k**1.25
    profiles = []
    for t in PROFILE_TIMES:
        propagation = np.cos(pi * k * ROPE.nu * t / ROPE.length)
        profiles.append((coefficients * propagation) @ basis)
    return (coefficients @ basis).astype("float32"), np.stack(profiles, axis=1).astype(
        "float32"
    )


def triangle_reference(x, t):
    """d'Alembert solution for the CP2 triangular pluck, fixed ends and zero speed."""

    def odd_extension(coordinate):
        r = (coordinate / ROPE.length + 1.0) % 2.0 - 1.0
        distance = np.abs(r)
        return np.sign(r) * 2 * ROPE.h * np.minimum(distance, 1.0 - distance)

    return (odd_extension(x - ROPE.nu * t) + odd_extension(x + ROPE.nu * t)) / 2


def canonical_rope(nodes):
    """Same sample coordinates for the benchmark input, exact and Newmark fields."""
    parameters = replace(ROPE, interior_points=nodes - 2)
    displacement, _ = cp2.cp2_swinging_rope_initial_state(parameters)
    initial = np.array([0.0, *displacement, 0.0])
    numerical = cp2.cp2_swinging_rope_implicit(
        parameters=parameters,
        time_step=0.01,
        t_bound=max(PROFILE_TIMES),
        positions=(),
        snapshot_times=PROFILE_TIMES,
    )
    x = np.array(numerical.snapshot_positions)
    exact = np.stack([triangle_reference(x, t) for t in PROFILE_TIMES])
    return initial, exact, np.array(numerical.snapshots)


def cavity_field(density):
    """Run the repository's scalar D2Q9 reference from a resting density field."""
    n = density.shape[0]
    if density.shape != (n, n) or not np.isfinite(density).all() or density.min() <= 0:
        raise ValueError("density must be a positive finite square field")
    # At zero initial velocity, f_i^eq = rho * w_i; the walls match the core solver.
    populations = density[:, :, None] * np.asarray(cp2.CP2_LBM_WEIGHTS)
    state = tuple(tuple(tuple(cell) for cell in row) for row in populations.tolist())
    omega = cp2.cp2_lbm_relaxation(n, u0_x=LID_SPEED, reynolds=REYNOLDS)
    for _ in range(CAVITY_STEPS):
        state = cp2.cp2_lbm_step(state, n, omega, LID_SPEED)
    return np.asarray(
        cp2.cp2_lbm_velocity_magnitude(
            state,
            reference_speed=LID_SPEED,
            driving_speed=LID_SPEED,
        )
    )


def cavity_samples(count, rng):
    """Resting fields with smooth positive density variations about one."""
    z = pi * np.linspace(0, 1, CAVITY_NODES)
    pairs = ((1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (2, 2))
    patterns = np.stack([np.outer(np.cos(ky * z), np.cos(kx * z)) for kx, ky in pairs])
    amplitudes = rng.uniform(-1.0, 1.0, size=(count, len(pairs)))
    fluctuation = np.einsum("bk,kyx->byx", amplitudes, patterns) / np.sqrt(len(pairs))
    density = (1.0 + DENSITY_SCALE * fluctuation).astype("float32")
    fields = np.stack([cavity_field(row) for row in density]).astype("float32")
    return density, fields[:, None]


def relative_l2(predicted, reference):
    """Relative Euclidean norm on the supplied grid; undefined for a zero field."""
    denominator = np.linalg.norm(reference)
    if denominator == 0:
        raise ValueError("relative error is undefined for a zero reference")
    return float(np.linalg.norm(predicted - reference) / denominator)
