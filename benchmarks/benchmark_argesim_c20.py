#!/usr/bin/env python3
"""Timing harness for the physical ARGESIM C20 production model.

For statistical replications across fixed books use scripts/c20_experiment.py.
This harness repeats identical seeded inputs to measure execution time.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c20_complex_production import run_c20_replication


def run_scenario(
    order_scenario: str,
    plant_scenario: str = "PSc1",
    *,
    seed: int = 20,
    order_seed: int = 20,
    order_count: int = 5000,
) -> dict:
    """Run the same physical engine as the registered C20 benchmark."""
    metrics = asdict(
        run_c20_replication(
            order_scenario,
            plant_scenario,
            seed=seed,
            order_seed=order_seed,
            order_count=order_count,
        )
    )
    metrics.pop("orders")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--orders", type=int, default=5000)
    parser.add_argument("--seed", type=int, default=20)
    parser.add_argument("--order-seed", type=int, default=20)
    parser.add_argument(
        "--plant",
        nargs="+",
        choices=[f"PSc{i}" for i in range(1, 5)],
        default=[f"PSc{i}" for i in range(1, 5)],
    )
    arguments = parser.parse_args()
    if arguments.repeat < 1 or arguments.warmup < 0 or arguments.orders < 1:
        parser.error("repeat/orders must be positive; warmup must be non-negative")
    report = {
        "benchmark": "ARGESIM-C20",
        "model": "physical",
        "order_book": "generated",
        "order_seed": arguments.order_seed,
        "order_count": arguments.orders,
        "seed": arguments.seed,
        "scenarios": {},
    }
    for osc in ("OSc1", "OSc2", "OSc3"):
        for psc in arguments.plant:
            durations = []
            metrics = None
            for iteration in range(-arguments.warmup, arguments.repeat):
                started = time.perf_counter_ns()
                current = run_scenario(
                    osc,
                    psc,
                    seed=arguments.seed,
                    order_seed=arguments.order_seed,
                    order_count=arguments.orders,
                )
                elapsed = time.perf_counter_ns() - started
                if metrics is not None and current != metrics:
                    raise RuntimeError(
                        "identical seeded inputs produced different results"
                    )
                metrics = current
                if iteration >= 0:
                    durations.append(elapsed)
            quartiles = (
                statistics.quantiles(durations, n=4, method="inclusive")
                if len(durations) > 1
                else [float(durations[0])] * 3
            )
            report["scenarios"][f"{osc}/{psc}"] = {
                "metrics": metrics,
                "durations_ns": durations,
                "median_ns": statistics.median(durations),
                "iqr_ns": quartiles[2] - quartiles[0],
            }
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
