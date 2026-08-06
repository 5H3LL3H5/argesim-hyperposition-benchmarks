#!/usr/bin/env python3
"""Timing experiment for ARGESIM C07 (Constrained Pendulum)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c07_constrained_pendulum import (
    c07_task_a,
    c07_task_b,
    c07_task_c,
)


def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Timing experiment for ARGESIM C07."
    )
    parser.add_argument("--repeat", type=int, default=9, help="Number of repetitions.")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs.")
    arguments = parser.parse_args()
    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    report: dict[str, object] = {
        "benchmark": "ARGESIM-C07",
        "definition": "https://www.argesim.org/benchmarks/c07/",
        "tasks": {},
    }

    tasks = {
        "Task_A": c07_task_a,
        "Task_B": c07_task_b,
        "Task_C": c07_task_c,
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
        if isinstance(result, dict):
            task_report["subtasks"] = {}
            for name, res in result.items():
                task_report["subtasks"][name] = {
                    "accepted_steps": res.stats.accepted_steps,
                    "rejected_steps": res.stats.rejected_steps,
                    "rhs_evaluations": res.stats.rhs_evaluations,
                }
        elif isinstance(result, float):
            task_report["initial_velocity_result"] = result

        report["tasks"][task_name] = task_report

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
