#!/usr/bin/env python3
"""Timing experiment for ARGESIM CP2 (Parallel and Distributed Simulation)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.cp2_parallel_and_distributed import (
    cp2_lbm_initial_state,
    cp2_lbm_step,
    cp2_monte_carlo_problem,
    cp2_swinging_rope_problem,
)
from argesim_benchmarks.solvers import rk45


def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]


def run_task_1() -> object:
    prob = cp2_monte_carlo_problem(t_bound=2.0)
    return rk45(prob)


def run_task_2() -> object:
    nx = 33
    omega = 1.0
    grid = cp2_lbm_initial_state(nx=nx)
    for _ in range(10):
        grid = cp2_lbm_step(grid, nx=nx, omega=omega)
    return grid


def run_task_3() -> object:
    prob = cp2_swinging_rope_problem(t_bound=1.0)
    return rk45(prob)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Timing experiment for ARGESIM CP2."
    )
    parser.add_argument("--repeat", type=int, default=9, help="Number of repetitions.")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs.")
    arguments = parser.parse_args()
    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    report: dict[str, object] = {
        "benchmark": "ARGESIM-CP2",
        "definition": "https://www.argesim.org/benchmarks/cp2/",
        "tasks": {},
    }

    tasks = {
        "Task1_MonteCarlo": run_task_1,
        "Task2_LBM": run_task_2,
        "Task3_SwingingRope": run_task_3,
    }

    for task_name, task_func in tasks.items():
        for _ in range(arguments.warmup):
            task_func()

        durations: list[int] = []
        result = None
        for _ in range(arguments.repeat):
            started = time.perf_counter_ns()
            result = task_func()
            durations.append(time.perf_counter_ns() - started)
        assert result is not None

        first_quartile, third_quartile = _quartiles(durations)
        task_report: dict[str, object] = {
            "durations_ns": durations,
            "median_ns": statistics.median(durations),
            "iqr_ns": third_quartile - first_quartile,
        }
        if hasattr(result, "method"):
            task_report["method"] = result.method
            task_report["accepted_steps"] = result.stats.accepted_steps
            task_report["rejected_steps"] = result.stats.rejected_steps
            task_report["rhs_evaluations"] = result.stats.rhs_evaluations

        report["tasks"][task_name] = task_report

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
