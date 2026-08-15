#!/usr/bin/env python3
"""Timing experiment for ARGESIM C12 tasks."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c12_collision import c12_task_a, c12_task_b, c12_task_c


def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=9)
    parser.add_argument("--warmup", type=int, default=1)
    arguments = parser.parse_args()

    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    report: dict[str, object] = {
        "benchmark": "ARGESIM-C12",
        "definition": "https://www.argesim.org/benchmarks/c12/",
        "tasks": {},
    }

    tasks = {
        "task_a": c12_task_a,
        "task_b": c12_task_b,
        "task_c": c12_task_c,
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

        first_quartile, third_quartile = _quartiles(durations)

        # Omit full trajectory history from task a
        if task_name == "task_a" and result and "a1_trajectory" in result:
             result["a1_trajectory"] = "omitted for brevity"
        # Omit full sweep points from task b
        if task_name == "task_b" and result and "sweep" in result:
             result["sweep"] = f"omitted {len(result['sweep'])} points"

        report["tasks"][task_name] = {
            "result_summary": result,
            "durations_ns": durations,
            "median_ns": statistics.median(durations),
            "iqr_ns": third_quartile - first_quartile,
        }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

