#!/usr/bin/env python3
"""Timing experiment for ARGESIM C17R (SIR Epidemic)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c17_sir_epidemic import solve_c17


def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Timing experiment for ARGESIM C17R."
    )
    parser.add_argument("--repeat", type=int, default=9, help="Number of repetitions.")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs.")
    arguments = parser.parse_args()
    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    report: dict[str, object] = {
        "benchmark": "ARGESIM-C17R",
        "definition": "https://www.argesim.org/benchmarks/c17r/",
        "tasks": {},
    }

    solvers = {
        "rk45": lambda: solve_c17(method="rk45", t_bound=150.0),
        "rk4": lambda: solve_c17(method="rk4", t_bound=150.0),
        "euler": lambda: solve_c17(method="euler", t_bound=150.0),
        "qss1": lambda: solve_c17(method="qss1", t_bound=150.0, options={"quantum": (1.0, 1.0, 1.0)}),
        "qss2": lambda: solve_c17(method="qss2", t_bound=150.0, options={"quantum": (1.0, 1.0, 1.0)}),
    }

    for solver_name, solver_func in solvers.items():
        for _ in range(arguments.warmup):
            solver_func()

        durations: list[int] = []
        result = None
        for _ in range(arguments.repeat):
            started = time.perf_counter_ns()
            result = solver_func()
            durations.append(time.perf_counter_ns() - started)
        assert result is not None

        first_quartile, third_quartile = _quartiles(durations)
        report["tasks"][solver_name] = {
            "final_state": result.final_state,
            "accepted_steps": result.stats.accepted_steps,
            "rejected_steps": result.stats.rejected_steps,
            "rhs_evaluations": result.stats.rhs_evaluations,
            "durations_ns": durations,
            "median_ns": statistics.median(durations),
            "iqr_ns": third_quartile - first_quartile,
        }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
