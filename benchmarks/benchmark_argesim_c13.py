#!/usr/bin/env python3
"""Accuracy-checked timing experiment for ARGESIM C13."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c13_crane import (
    c13_task_a,
    c13_task_b,
    c13_task_c,
    solve_c13_task_b_c,
)


def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]


def _verify_task_a(result: dict[float, dict[str, float]]) -> None:
    """Check task A steady-state positions against expected values."""
    expected = {
        -750.0: {"linear": 294.08445, "nonlinear": 294.08414},
        -800.0: {"linear": -0.00485, "nonlinear": -0.00513},
        -850.0: {"linear": -294.09415, "nonlinear": -294.09445},
    }
    tolerance = 1.0e-3
    for dist, ref in expected.items():
        for model_key, ref_val in ref.items():
            actual = result[dist][model_key]
            error = abs(actual - ref_val)
            if error >= tolerance:
                raise RuntimeError(
                    f"Task A dist={dist} {model_key}: error {error:.6e} "
                    f"exceeds tolerance {tolerance}"
                )


def _verify_task_b_c(
    label: str,
    result: object,
    expected_final_xc: float,
    expected_final_alpha: float,
    tolerance: float = 1.0e-3,
) -> None:
    """Check task B/C final state against expected values."""
    xc = result.final_state[0]
    alpha = result.final_state[2]
    err_xc = abs(xc - expected_final_xc)
    err_alpha = abs(alpha - expected_final_alpha)
    if err_xc >= tolerance:
        raise RuntimeError(
            f"{label} xc error {err_xc:.6e} exceeds tolerance {tolerance}"
        )
    if err_alpha >= tolerance:
        raise RuntimeError(
            f"{label} alpha error {err_alpha:.6e} exceeds tolerance {tolerance}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Accuracy-checked timing experiment for ARGESIM C13."
    )
    parser.add_argument("--repeat", type=int, default=9, help="Number of repetitions.")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs.")
    arguments = parser.parse_args()
    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    report: dict[str, object] = {
        "benchmark": "ARGESIM-C13",
        "definition": "https://www.argesim.org/benchmarks/c13/",
        "interpretation": (
            "Runtime comparisons are reported only after every endpoint passes its "
            "declared accuracy threshold. Solver configuration and work counts differ "
            "and are therefore retained with the timing data."
        ),
        "tasks": {},
    }

    # --- Task A ---
    for _ in range(arguments.warmup):
        c13_task_a()

    durations_a: list[int] = []
    result_a = None
    for _ in range(arguments.repeat):
        started = time.perf_counter_ns()
        result_a = c13_task_a()
        durations_a.append(time.perf_counter_ns() - started)
    assert result_a is not None
    _verify_task_a(result_a)

    first_q, third_q = _quartiles(durations_a)
    report["tasks"]["Task_A"] = {
        "result": {str(k): v for k, v in result_a.items()},
        "durations_ns": durations_a,
        "median_ns": statistics.median(durations_a),
        "iqr_ns": third_q - first_q,
    }

    # --- Tasks B and C ---
    task_bc_configs = [
        ("Task_B", False, 3.70588, 0.00843),
        ("Task_C", True, 5.00606, -0.18938),
    ]
    for task_name, with_diag, expected_xc, expected_alpha in task_bc_configs:
        func = c13_task_c if with_diag else c13_task_b
        for _ in range(arguments.warmup):
            func()

        durations: list[int] = []
        result = None
        for _ in range(arguments.repeat):
            started = time.perf_counter_ns()
            full_result, _xl_traj, _brake_traj = solve_c13_task_b_c(
                with_diagnosis=with_diag
            )
            durations.append(time.perf_counter_ns() - started)
            result = full_result
        assert result is not None
        _verify_task_b_c(task_name, result, expected_xc, expected_alpha)

        first_q, third_q = _quartiles(durations)
        report["tasks"][task_name] = {
            "method": result.method,
            "final_state": result.final_state,
            "accepted_steps": result.stats.accepted_steps,
            "rejected_steps": result.stats.rejected_steps,
            "rhs_evaluations": result.stats.rhs_evaluations,
            "durations_ns": durations,
            "median_ns": statistics.median(durations),
            "iqr_ns": third_q - first_q,
        }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
