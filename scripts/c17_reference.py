"""Check the C17R default ODE and compare FHP-I with Reichl et al., Eq. 4.

Run with --spatial-replications 32 for the independent-seed comparison.
The publication reports a single stochastic realization without a seed.
"""

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np
from scipy.integrate import solve_ivp

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argesim_benchmarks.models.c17_sir_epidemic import simulate_c17_ca, solve_c17


def scalar_reference():
    def rate(_t, r):
        s = 9500 * np.exp(-0.0004 * r)
        return -math.log1p(-0.1) * (10000 - s - r)

    result = solve_ivp(
        rate,
        (0, 100),
        [0.0],
        method="DOP853",
        atol=1e-12,
        rtol=2e-13,
        max_step=0.25,
        dense_output=True,
    )
    if not result.success:
        raise RuntimeError(result.message)

    def populations(times):
        r = result.sol(times)[0]
        s = 9500 * np.exp(-0.0004 * r)
        return np.column_stack((s, 10000 - s - r, r))

    return populations


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spatial-replications", type=int, default=0)
    count = parser.parse_args().spatial_replications
    if count < 0:
        parser.error("replication count must be non-negative")
    reference = scalar_reference()
    rows = []
    for method, quantum, limit in (
        ("rk45", None, 3e-5),
        ("qss2", 1.0, 1.0),
        ("qss2", 0.1, 0.1),
        ("qss2", 0.01, 0.01),
    ):
        options = {} if quantum is None else {"quantum": (quantum,) * 3}
        candidate = solve_c17(method, t_bound=100.0, options=options)
        if (candidate.times[0], candidate.times[-1]) != (0.0, 100.0):
            raise RuntimeError("incomplete C17R ODE trajectory")
        error = np.abs(reference(candidate.times) - candidate.states).max(axis=0)
        rows.append(
            {
                "method": method,
                "quantum": quantum,
                "samples": len(candidate.times),
                "max_error_by_state": error.tolist(),
                "limit": limit,
                "passed": bool(error.max() <= limit),
            }
        )

    report = {"ode": rows}
    if count:
        infected = reference(np.arange(101))[:, 1]
        norms = []
        for seed in range(count):
            candidate = simulate_c17_ca(seed=seed, steps=100, movement="fhp-i")
            # Eq. 3, evaluated on integer times 1..100 as in the MATLAB study.
            error = np.abs(infected[1:] - candidate.infected[1:]) / 10000
            norms.append(float((error[:-1] + error[1:]).sum() / 2))
        report["spatial"] = {
            "published_single_run": 1.4844,
            "first_seed": 0,
            "norm_by_seed": norms,
            "minimum": min(norms),
            "median": statistics.median(norms),
            "maximum": max(norms),
            "runs_at_or_below_published": sum(v <= 1.4844 for v in norms),
        }
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(row["passed"] for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
