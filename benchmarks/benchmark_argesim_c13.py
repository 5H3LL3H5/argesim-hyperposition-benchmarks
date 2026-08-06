#!/usr/bin/env python3
"""Timing experiment for ARGESIM C13."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c13_crane import c13_task_a, c13_task_b, c13_task_c


def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark ARGESIM C13.")
    parser.add_argument("--repeat", type=int, default=5, help="Number of repetitions.")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs.")
    arguments = parser.parse_args()

    report: dict[str, object] = {
        "benchmark": "ARGESIM-C13",
        "definition": "https://www.argesim.org/benchmarks/c13/",
        "tasks": {},
    }

    tasks = {
        "Task_A": c13_task_a,
        "Task_B": c13_task_b,
        "Task_C": c13_task_c,
    }

    for task_name, task_func in tasks.items():
        for _ in range(arguments.warmup):
            task_func()

        durations: list[int] = []
        for _ in range(arguments.repeat):
            started = time.perf_counter_ns()
            task_func()
            durations.append(time.perf_counter_ns() - started)

        first_quartile, third_quartile = _quartiles(durations)
        report["tasks"][task_name] = {
            "durations_ns": durations,
            "median_ns": statistics.median(durations),
            "iqr_ns": third_quartile - first_quartile,
        }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
