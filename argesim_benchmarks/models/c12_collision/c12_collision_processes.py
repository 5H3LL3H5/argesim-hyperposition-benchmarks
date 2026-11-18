"""ARGESIM C12: Collision Processes in Rows of Spheres.

This model simulates the 1D collision of 4 identical spheres. The primary definition
uses relative distances between adjacent spheres.
"""

from __future__ import annotations

import math
import random
import statistics
from dataclasses import dataclass

from argesim_benchmarks.solvers.roots import brentq


@dataclass(frozen=True)
class C12Parameters:
    """Parameters for the C12 benchmark."""
    e: float = 0.2
    d: float = 1.0
    a: float = 1.0
    v0: float = 1.0
    # Task A1 plotting horizon; None resolves collisions to their terminal state.
    max_time: float | None = 15.0
    # Task C stochastic parameters
    mean_e: float = 0.5
    std_e: float = 0.05

    def __post_init__(self) -> None:
        if not math.isfinite(self.e) or self.e < 0.0 or self.e > 1.0:
            raise ValueError("Restitution coefficient e must be between 0.0 and 1.0")
        if not math.isfinite(self.d) or self.d <= 0.0:
            raise ValueError("Sphere diameter d must be positive and finite")
        if not math.isfinite(self.a) or self.a <= 0.0:
            raise ValueError("Distance a must be positive and finite")
        if not math.isfinite(self.v0) or self.v0 <= 0.0:
            raise ValueError("Initial velocity v0 must be positive and finite")
        if self.max_time is not None and (
            not math.isfinite(self.max_time) or self.max_time <= 0.0
        ):
            raise ValueError("Max time must be positive and finite, or None")
        if not math.isfinite(self.mean_e) or self.mean_e < 0.0 or self.mean_e > 1.0:
            raise ValueError("Mean e must be between 0.0 and 1.0")
        if not math.isfinite(self.std_e) or self.std_e <= 0.0:
            raise ValueError("Standard deviation of e must be positive")


_C12_DEFAULT_PARAMETERS = C12Parameters()
C12_QUASI_PLASTIC_E = 0.18

def _simulate(
    params: C12Parameters = _C12_DEFAULT_PARAMETERS,
    *,
    velocity_tolerance: float = 1.0e-10,
) -> tuple[int, list[float], float, list[tuple[float, list[float], list[float]]]]:
    if not math.isfinite(velocity_tolerance) or velocity_tolerance <= 0.0:
        raise ValueError("velocity_tolerance must be positive and finite")
    e = params.e
    v0 = params.v0
    a_dist = params.a
    max_time = math.inf if params.max_time is None else params.max_time

    v = [v0, 0.0, 0.0, 0.0]
    # Definition (4): all three free surface gaps initially equal a.
    y = [a_dist, a_dist, a_dist]
    t = 0.0
    cols = 0
    history = [(t, list(y), list(v))]

    while cols < 100000:
        if max(abs(v[k + 1] - v[k]) for k in range(3)) <= velocity_tolerance:
            break

        times = []
        for i in range(3):
            relative_velocity = v[i + 1] - v[i]
            if relative_velocity < -velocity_tolerance:
                collision_time = -y[i] / relative_velocity
                if collision_time >= -1.0e-12:
                    times.append((max(0.0, collision_time), i))

        if not times:
            break

        dt, i = min(times)

        if t + dt > max_time + 1e-12:
            dt = max_time - t
            if dt > 0.0:
                t += dt
                for j in range(3):
                    y[j] = max(0.0, y[j] + (v[j+1] - v[j]) * dt)
                history.append((t, list(y), list(v)))
            break

        if dt > 0.0:
            t += dt
            for j in range(3):
                # Exact event advance cannot create overlap; clip roundoff.
                y[j] = max(0.0, y[j] + (v[j+1] - v[j]) * dt)

        vy = v[i+1] - v[i]
        v[i] = v[i] + 0.5 * (1 + e) * vy
        v[i+1] = v[i+1] - 0.5 * (1 + e) * vy
        y[i] = 0.0
        cols += 1
        history.append((t, list(y), list(v)))

    else:
        raise RuntimeError("C12 collision iteration limit exceeded")

    return cols, v, t, history


def c12_task_a() -> dict[str, object]:
    """Task A: Distance-time functions and final velocities."""
    # a1
    _cols, _v_final, _t_final, history = _simulate(C12Parameters(e=0.2, v0=1.0, max_time=15.0))

    # a2
    _, v_elastic, _, _ = _simulate(C12Parameters(e=1.0, v0=1.0, max_time=None))
    _, v_quasi_plastic, _, _ = _simulate(
        C12Parameters(e=C12_QUASI_PLASTIC_E, v0=1.0, max_time=None)
    )

    return {
        "a1_trajectory": history,
        "a2_elastic_velocities": v_elastic,
        "a2_quasi_plastic_e": C12_QUASI_PLASTIC_E,
        "a2_quasi_plastic_velocities": v_quasi_plastic,
        # Compatibility alias retained for callers of the historical API.
        "a2_plastic_velocities": v_quasi_plastic,
    }

def c12_task_b() -> dict[str, object]:
    """Task B: Number of collisions and final velocities over e."""
    results = {}
    step = 0.01
    count = round((1.0 - C12_QUASI_PLASTIC_E) / step)
    for i in range(count + 1):
        e_val = round(1.0 - i * step, 2)
        cols, v, _t, _ = _simulate(C12Parameters(e=e_val, v0=1.0, max_time=None))
        results[e_val] = {"collisions": cols, "velocities": v}
    return {"sweep": results}

def c12_task_c(*, n_samples: int = 10000, seed: int = 42) -> dict[str, object]:
    """Task C: Boundary value problem and stochastic study."""
    if isinstance(n_samples, bool) or not isinstance(n_samples, int) or n_samples < 2:
        raise ValueError("stochastic study requires an integer sample count of at least two")
    # c1: find e for v4 = v0/2 = 0.5
    def f(e_val: float) -> float:
        return _simulate(C12Parameters(e=e_val, v0=1.0, max_time=None))[1][3] - 0.5

    e_solution = brentq(f, 0.0, 1.0)

    # c2: stochastic study
    rng = random.Random(seed)
    mean_e = _C12_DEFAULT_PARAMETERS.mean_e
    std_e = _C12_DEFAULT_PARAMETERS.std_e

    v4_samples = []
    for _ in range(n_samples):
        e_val = rng.normalvariate(mean_e, std_e)
        e_val = max(0.0, min(1.0, e_val))
        v4_samples.append(
            _simulate(C12Parameters(e=e_val, v0=1.0, max_time=None))[1][3]
        )

    mean_v4 = statistics.mean(v4_samples)
    std_v4 = statistics.stdev(v4_samples)
    ci = 1.96 * std_v4 / math.sqrt(n_samples)
    ordered_samples = sorted(v4_samples)
    empirical_cdf = tuple(
        (value, (rank + 1) / n_samples)
        for rank, value in enumerate(ordered_samples)
    )

    return {
        "c1_target_e": e_solution,
        "c2_mean_v4": mean_v4,
        "c2_std_v4": std_v4,
        "c2_confidence_interval": (mean_v4 - ci, mean_v4 + ci),
        "c2_empirical_cdf": empirical_cdf,
    }
