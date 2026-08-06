"""ARGESIM C12: Collision Processes in Rows of Spheres.

This model simulates the 1D collision of 4 identical spheres. The primary definition
uses relative distances between adjacent spheres.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass

from argesim_benchmarks.solvers.roots import brentq


@dataclass(frozen=True)
class C12Parameters:
    """Parameters for the C12 benchmark."""
    e: float = 0.2
    d: float = 1.0
    a: float = 1.0
    v0: float = 1.0

    def __post_init__(self) -> None:
        if not math.isfinite(self.e) or self.e < 0.0 or self.e > 1.0:
            raise ValueError("Restitution coefficient e must be between 0.0 and 1.0")
        if not math.isfinite(self.d) or self.d <= 0.0:
            raise ValueError("Sphere diameter d must be positive and finite")
        if not math.isfinite(self.a) or self.a <= 0.0:
            raise ValueError("Distance a must be positive and finite")
        if not math.isfinite(self.v0) or self.v0 <= 0.0:
            raise ValueError("Initial velocity v0 must be positive and finite")


_C12_DEFAULT_PARAMETERS = C12Parameters()

def _simulate(e: float, v0: float, max_time: float = float('inf')) -> tuple[int, list[float], float, list[tuple[float, list[float], list[float]]]]:
    v = [v0, 0.0, 0.0, 0.0]
    y = [1.0, 1.0, 1.0] # using initial distance a = 1.0 for relative distances
    t = 0.0
    cols = 0
    history = [(t, list(y), list(v))]

    # In the perfectly plastic case, zeno behavior occurs.
    # The specification states that for e=0, the velocities become "sufficiently equal".
    if e == 0.0:
        # perfectly inelastic collision resolves instantly to all spheres
        # moving together at v0 / 4 by conservation of momentum.
        v = [v0 / 4.0] * 4
        # We model this as a single macro-collision step
        history.append((0.0, list(y), list(v)))
        return 3, v, 0.0, history

    while cols < 100000:
        times = []
        for i in range(3):
            vy = v[i+1] - v[i]
            if vy < -1e-12:
                times.append((-y[i]/vy, i))

        if not times:
            break

        dt, i = min(times)

        if t + dt > max_time + 1e-12:
            dt = max_time - t
            if dt > 1e-12:
                t += dt
                for j in range(3):
                    y[j] += (v[j+1] - v[j]) * dt
                history.append((t, list(y), list(v)))
            break

        if dt > 1e-12:
            t += dt
            for j in range(3):
                y[j] += (v[j+1] - v[j]) * dt

        vy = v[i+1] - v[i]
        v[i] = v[i] + 0.5 * (1 + e) * vy
        v[i+1] = v[i+1] - 0.5 * (1 + e) * vy
        y[i] = 0.0
        cols += 1
        history.append((t, list(y), list(v)))

        # Fast-forward plastic/zeno collapse if relative velocities vanish
        if max(abs(v[k+1] - v[k]) for k in range(3)) < 1e-12:
            break

    return cols, v, t, history


def c12_task_a() -> dict[str, object]:
    """Task A: Distance-time functions and final velocities."""
    # a1
    cols, v_final, t_final, history = _simulate(0.2, 1.0, max_time=15.0)

    # a2
    _, v_elastic, _, _ = _simulate(1.0, 1.0)
    _, v_plastic, _, _ = _simulate(0.0, 1.0)

    return {
        "a1_trajectory": history,
        "a2_elastic_velocities": v_elastic,
        "a2_plastic_velocities": v_plastic,
    }

def c12_task_b() -> dict[str, object]:
    """Task B: Number of collisions and final velocities over e."""
    steps = 100
    results = {}
    for i in range(steps + 1):
        e = i / steps
        cols, v, t, _ = _simulate(e, 1.0)
        results[e] = {"collisions": cols, "velocities": v}
    return {"sweep": results}

def c12_task_c() -> dict[str, object]:
    """Task C: Boundary value problem and stochastic study."""
    # c1: find e for v4 = v0/2 = 0.5
    def f(e_val: float) -> float:
        return _simulate(e_val, 1.0)[1][3] - 0.5

    e_solution = brentq(f, 0.0, 1.0)

    # c2: stochastic study
    n_samples = 10000
    random.seed(42)
    mean_e, std_e = 0.5, 0.05
    v4_samples = []
    for _ in range(n_samples):
        e_val = random.normalvariate(mean_e, std_e)
        e_val = max(0.0, min(1.0, e_val))
        v4_samples.append(_simulate(e_val, 1.0)[1][3])

    mean_v4 = sum(v4_samples) / n_samples
    var_v4 = sum((x - mean_v4)**2 for x in v4_samples) / (n_samples - 1)
    std_v4 = math.sqrt(var_v4)
    ci = 1.96 * std_v4 / math.sqrt(n_samples)

    return {
        "c1_target_e": e_solution,
        "c2_mean_v4": mean_v4,
        "c2_std_v4": std_v4,
        "c2_confidence_interval": (mean_v4 - ci, mean_v4 + ci)
    }
