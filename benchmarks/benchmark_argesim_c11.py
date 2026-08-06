#!/usr/bin/env python3
"""Accuracy-checked timing experiment for ARGESIM C11 task B and C."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c11_scara_robot import solve_c11, C11_TARGET_STATE

METHOD_TOLERANCES = {
    "rk45": 1.0e-3,
}

def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]

def _endpoint_error(candidate: tuple[float, ...], reference: tuple[float, ...]) -> float:
    return max(abs(value - expected) for value, expected in zip(candidate, reference))

def run_task(task_name: str, repeat: int, warmup: int) -> dict:
    reference_result = solve_c11(
        "rk45",
        task=task_name,
        t_bound=2.0,
        options={"rtol": 1.0e-8, "atol": 1.0e-10, "max_step": 1.0e-3},
    )
    reference = reference_result.final_state

    target_pos = C11_TARGET_STATE
    pos_error = _endpoint_error(reference[:3], target_pos)

    report: dict[str, object] = {
        "benchmark": f"ARGESIM-C11-task-{task_name}",
        "definition": "https://www.argesim.org/benchmarks/c11/",
        "reference_endpoint": reference,
        "target_position_error": pos_error,
        "methods": {},
    }

    for method, tolerance in METHOD_TOLERANCES.items():
        for _ in range(warmup):
            solve_c11(method, task=task_name, t_bound=2.0)
        durations: list[int] = []
        result = None
        for _ in range(repeat):
            started = time.perf_counter_ns()
            result = solve_c11(method, task=task_name, t_bound=2.0)
            durations.append(time.perf_counter_ns() - started)
        assert result is not None
        error = _endpoint_error(result.final_state, reference)
        if error >= tolerance:
            raise RuntimeError(
                f"{method} endpoint error {error} exceeds tolerance {tolerance}"
            )
        first_quartile, third_quartile = _quartiles(durations)
        report["methods"][method] = {
            "endpoint": result.final_state,
            "maximum_endpoint_error": error,
            "error_tolerance": tolerance,
            "accepted_steps_or_events": result.stats.accepted_steps,
            "rejected_steps": result.stats.rejected_steps,
            "rhs_evaluations": result.stats.rhs_evaluations,
            "durations_ns": durations,
            "median_ns": statistics.median(durations),
            "iqr_ns": third_quartile - first_quartile,
        }
    return report

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    arguments = parser.parse_args()

    report_b = run_task("b", arguments.repeat, arguments.warmup)
    report_c = run_task("c", arguments.repeat, arguments.warmup)

    final_report = {
        "interpretation": (
            "Runtime comparisons are reported only after every endpoint passes its "
            "declared accuracy threshold against a tight RK45 reference. C11 is stiff "
            "and requires many evaluations for Task C."
        ),
        "task_b": report_b,
        "task_c": report_c,
    }
    print(json.dumps(final_report, indent=2))

if __name__ == "__main__":
    main()
