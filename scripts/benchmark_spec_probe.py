"""Independent numerical spot checks for the 2026-11-18 definition audit.

Requires NumPy and SciPy (audit used 2.3.5 / 1.17.0). Run this script from
any directory; each JSON line records its declared tolerance and outcome.
No candidate RHS is used by the independent reference calculations.
"""

import json
import math
import sys
from pathlib import Path

import numpy as np
import scipy
from scipy.integrate import solve_ivp
from scipy.linalg import expm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argesim_benchmarks.models.c01_lithium_cluster import C01Parameters, solve_c01
from argesim_benchmarks.models.c03_amplifier import C03Parameters, solve_c03
from argesim_benchmarks.models.c07_constrained_pendulum import C07Parameters, solve_c07
from argesim_benchmarks.models.c15_clearance import C15Bolus, solve_c15

results = {"numpy": np.__version__, "scipy": scipy.__version__, "checks": []}


def record(case, maximum, tolerance, details):
    row = {
        "case": case,
        "maximum_absolute_error": float(maximum),
        "tolerance": tolerance,
        "passed": bool(maximum <= tolerance),
        "details": details,
    }
    results["checks"].append(row)
    print(json.dumps(row), flush=True)


for loss in (100.0, 1000.0, 10000.0):

    def lithium(t, y, loss=loss):
        r, m, f = y
        return [
            -0.1 * r + m * f,
            0.1 * r - m + 0.1 * f * f - m * f,
            0.1 * r + 2 * m - m * f - 0.2 * f * f - loss * f,
        ]

    reference = solve_ivp(
        lithium,
        (0, 10),
        (84.99, 1.674, 9.975),
        method="Radau",
        rtol=2e-12,
        atol=2e-13,
        dense_output=True,
    )
    assert reference.success
    candidate = solve_c01(parameters=C01Parameters(loss_f=loss))
    error = np.max(
        np.abs(np.array(candidate.states).T - reference.sol(candidate.times))
    )
    record(
        f"C01 loss={loss:g}",
        error,
        2e-6,
        f"Radau reference, all {len(candidate.times)} candidate trajectory samples",
    )

# C03 ideal-switch limit: exact affine flow on each ON/OFF half-period.
# This uses a 5x5 matrix exponential; no candidate RHS or stepper is reused.
candidate = solve_c03(parameters=C03Parameters(trf=0.0))
state = np.zeros(4)
errors = []
for i in range(20):
    start, end = i * 5e-6, (i + 1) * 5e-6
    resistance = 5e6 if i % 2 == 0 else 0.05
    a = np.array(
        [
            [0, -1 / 79.9e-6, 0, 0, 5 / 79.9e-6],
            [1 / 17.9e-9, -1 / (17.9e-9 * resistance), -1 / 17.9e-9, 0, 0],
            [0, 1 / 232e-6, -52.4 / 232e-6, -1 / 232e-6, 0],
            [0, 0, 1 / 9.66e-9, 0, 0],
            [0, 0, 0, 0, 0],
        ]
    )
    state = (expm(a * (end - start)) @ np.r_[state, 1])[:4]
    index = min(
        range(len(candidate.times)), key=lambda k: abs(candidate.times[k] - end)
    )
    assert abs(candidate.times[index] - end) < 1e-15
    errors.append(np.max(np.abs(np.array(candidate.states[index]) - state)))
record(
    "C03 ideal-switch limit",
    max(errors),
    5e-5,
    "Independent matrix exponentials at all 20 half-cycle boundaries through 100 us",
)

# C07: independently segmented DOP853 with pin guards and velocity resets.
for initial, damping in (((math.pi / 6, 0.0), 0.2), ((-math.pi / 6, 0.0), 0.1)):
    candidate = solve_c07(initial_state=initial, parameters=C07Parameters(d=damping))
    current, state = 0.0, np.array(initial)
    short = state[0] < -math.pi / 12
    reference_segments = []
    for iteration in range(100):
        length = 0.3 if short else 1.0

        def pendulum(t, y, length=length, damping=damping):
            return [y[1], -9.81 / length * math.sin(y[0]) - damping / 1.02 * y[1]]

        def pin(t, y):
            return y[0] + math.pi / 12

        pin.direction = 1 if short else -1
        pin.terminal = True
        reference = solve_ivp(
            pendulum,
            (current, 10.0),
            state,
            method="DOP853",
            rtol=2e-12,
            atol=2e-13,
            max_step=0.005,
            events=pin,
            dense_output=True,
        )
        assert reference.success
        reference_segments.append(reference)
        current, state = reference.t[-1], reference.y[:, -1].copy()
        if current >= 10.0:
            break
        state[1] *= 0.3 if short else 1 / 0.3
        short = not short
    else:
        raise RuntimeError("pin event budget")
    differences = []
    # Avoid comparing opposite sides of a discontinuous velocity reset.
    for t, y in zip(candidate.times, candidate.states):
        if any(abs(t - seg.t[-1]) < 1e-6 for seg in reference_segments[:-1]):
            continue
        segment = next(seg for seg in reference_segments if seg.t[0] <= t <= seg.t[-1])
        differences.append(np.max(np.abs(np.array(y) - segment.sol(t))))
    record(
        f"C07 initial angle={initial[0]:.6f}",
        max(differences),
        5e-7,
        f"DOP853, {len(reference_segments) - 1} pin events; excludes 1 us around velocity jumps",
    )

for tau in (0.5, 3.0, 240.0):
    a = np.array([[-0.0041 - 0.0498, 0.0585], [0.0498, -0.0585]])
    augmented = np.zeros((3, 3))
    augmented[:2, :2] = a
    augmented[0, 2] = 2500 / tau
    state = (expm(augmented * tau) @ np.array([0.0, 0.0, 1.0]))[:2]
    expected = expm(a * (240 - tau)) @ state
    candidate = solve_c15(bolus=C15Bolus(2500.0, tau))
    record(
        f"C15 bolus tau={tau:g}",
        np.max(np.abs(np.array(candidate.final_state) - expected)),
        2e-5,
        "Independent augmented matrix exponential, both compartments at 240 min",
    )

assert all(row["passed"] for row in results["checks"]), "Independent reference mismatch"
