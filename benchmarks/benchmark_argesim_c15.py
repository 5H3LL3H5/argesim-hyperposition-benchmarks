#!/usr/bin/env python3
"""Accuracy-checked timing experiment for ARGESIM C15 task A."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c15_clearance import solve_c15

METHOD_TOLERANCES = {
    "euler": 8.0e-4,
    "rk4": 4.0e-6,
    "rk45": 2.0e-9,
    "qss1": 4.0,  # Large bound due to large required quantum=1.0 for speed
}

def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]

def _endpoint_error(candidate: tuple[float, ...], reference: tuple[float, ...]) -> float:
    return max(abs(value - expected) for value, expected in zip(candidate, reference))

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repeat", type=int, default=9)
    parser.add_argument("--warmup", type=int, default=1)
    arguments = parser.parse_args()
    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    reference_result = solve_c15(
        "rk45",
        options={"rtol": 1.0e-11, "atol": 1.0e-14, "max_step": 2.0e-3},
    )
    reference = reference_result.final_state
    report: dict[str, object] = {
        "benchmark": "ARGESIM-C15-task-A",
        "definition": "https://www.argesim.org/benchmarks/c15/",
        "reference_endpoint": reference,
        "methods": {},
        "interpretation": (
            "Runtime comparisons are reported only after every endpoint passes its "
            "declared accuracy threshold. Solver configuration and work counts differ "
            "and are therefore retained with the timing data."
        ),
    }

    for method, tolerance in METHOD_TOLERANCES.items():
        for _ in range(arguments.warmup):
            solve_c15(method)
        durations: list[int] = []
        result = None
        for _ in range(arguments.repeat):
            started = time.perf_counter_ns()
            result = solve_c15(method)
            durations.append(time.perf_counter_ns() - started)
        assert result is not None
        error = _endpoint_error(result.final_state, reference)
        if error >= tolerance:
            raise RuntimeError(f"{method} endpoint error {error} exceeds tolerance {tolerance}")
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

    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
