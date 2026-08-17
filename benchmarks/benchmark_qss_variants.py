#!/usr/bin/env python3
"""Accuracy-gated work and timing comparison for LIQSS-family variants."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks import InitialValueProblem, solve_ivp

METHODS = (
    "liqss1",
    "eliqss1",
    "cheqss1",
    "liqss2",
    "eliqss2",
    "cheqss2",
    "liqss3",
    "eliqss3",
    "cheqss3",
)


def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quantum", type=float, default=1.0e-2)
    parser.add_argument("--repeat", type=int, default=9)
    parser.add_argument("--warmup", type=int, default=1)
    arguments = parser.parse_args()
    if arguments.quantum <= 0.0 or not math.isfinite(arguments.quantum):
        parser.error("quantum must be positive and finite")
    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    problem = InitialValueProblem(
        lambda _time, state: (1.0 - state[0],),
        0.0,
        (0.0,),
        5.0,
        name="generalised-liqss-published-scalar",
        autonomous=True,
    )
    exact = 1.0 - math.exp(-problem.t_bound)
    options = {
        "quantum": arguments.quantum,
        "jacobian": lambda _time, _state: ((-1.0,),),
    }
    report: dict[str, object] = {
        "benchmark": "generalised-LIQSS-scalar-work-comparison",
        "equation": "x' = 1 - x; x(0) = 0; t_final = 5",
        "quantum": arguments.quantum,
        "exact_endpoint": exact,
        "methods": {},
        "interpretation": (
            "Endpoint accuracy is checked before timings are reported. Event and "
            "RHS-evaluation counts are the primary implementation-independent work "
            "measures; this repository remains a dense Python reference backend."
        ),
    }

    results = {}
    for method in METHODS:
        for _ in range(arguments.warmup):
            solve_ivp(problem, method, options=options)
        durations: list[int] = []
        result = None
        for _ in range(arguments.repeat):
            started = time.perf_counter_ns()
            result = solve_ivp(problem, method, options=options)
            durations.append(time.perf_counter_ns() - started)
        assert result is not None
        error = abs(result.final_state[0] - exact)
        if error > 2.1 * arguments.quantum:
            raise RuntimeError(
                f"{method} endpoint error {error} exceeds the quantum-scale gate"
            )
        first_quartile, third_quartile = _quartiles(durations)
        results[method] = result
        report["methods"][method] = {
            "endpoint": result.final_state[0],
            "absolute_error": error,
            "accepted_events": result.stats.accepted_steps,
            "rhs_evaluations": result.stats.rhs_evaluations,
            "median_ns": statistics.median(durations),
            "iqr_ns": third_quartile - first_quartile,
        }

    for order in (1, 2, 3):
        baseline = results[f"liqss{order}"].stats.accepted_steps
        for family in ("eliqss", "cheqss"):
            name = f"{family}{order}"
            report["methods"][name]["events_relative_to_liqss"] = (
                results[name].stats.accepted_steps / baseline
            )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
