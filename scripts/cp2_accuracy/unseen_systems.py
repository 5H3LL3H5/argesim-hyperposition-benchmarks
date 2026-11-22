"""Two manufactured systems outside the archived C03–C21 selection table."""

from __future__ import annotations

import itertools
import json
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

from argesim_benchmarks.models.c19_groundwater import C19Parameters, c19_rhs

OUT = (
    Path(__file__).resolve().parents[2]
    / "docs/lehrbuch/studienbuch/material/cp2_genauigkeit"
)


def run():
    # The model-independent selection in the archive returned RK45. These new
    # problems have exact solutions; budgets and tolerances are fixed for all.
    grid = np.linspace(0, 2, 1001)

    def duffing(t, y):
        return [y[1], -(y[0] ** 3) - np.sin(t) + np.sin(t) ** 3]

    def coupled(t, y):
        return [
            -12000 * (y[0] - np.cos(t)) + 300 * (y[1] - np.exp(-t)) - np.sin(t),
            -y[1],
        ]

    rows = []
    for (name, rhs, start, exact), method in itertools.product(
        [
            ("duffing", duffing, [0.0, 1.0], np.array([np.sin(grid), np.cos(grid)])),
            (
                "fast_coupled",
                coupled,
                [1.0, 1.0],
                np.array([np.cos(grid), np.exp(-grid)]),
            ),
        ],
        ["RK45", "Radau", "BDF"],
    ):
        sol = solve_ivp(
            rhs, (0, 2), start, method=method, rtol=1e-6, atol=1e-8, t_eval=grid
        )
        assert sol.success
        error = float(abs(sol.y - exact).max())
        rows.append(
            {
                "case": name,
                "method": method,
                "error": error,
                "nfev": sol.nfev,
                "lu": sol.nlu,
                "meets_budget": error <= 1e-4 and sol.nfev <= 8000,
            }
        )
    p = C19Parameters()
    n = 9
    space = 0.25
    dt = 200000.0
    c = np.indices((n, n)).sum(axis=0).ravel() % 2
    fun = c19_rhs(p, n, n, space, space, 10.0, 5.0)
    k1 = np.array(fun(0, c))
    k2 = np.array(fun(dt / 2, c + dt * k1 / 2))
    k3 = np.array(fun(dt / 2, c + dt * k2 / 2))
    k4 = np.array(fun(dt, c + dt * k3))
    out = c + dt * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    assert min(out) < 0
    report = {
        "solver": rows,
        "transport_counterexample": {
            "nodes": n,
            "spacing": space,
            "step": dt,
            "minimum": float(min(out)),
            "initial": "checkerboard; source outside domain",
        },
    }
    (OUT / "gegenproben.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    run()
