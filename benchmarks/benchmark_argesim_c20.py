#!/usr/bin/env python3
"""Timing experiment for ARGESIM C20 (Complex Production System)."""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from collections.abc import Callable
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c20_complex_production import (
    Conveyor,
    Order,
    SimulationEnvironment,
    WorkStation,
    WorkStationType,
    generate_osc1_order_book,
    generate_osc2_order_book,
    generate_osc3_order_book,
    get_operation_ws,
    get_process_plan,
    get_processing_time,
)


def _quartiles(values: list[int]) -> tuple[float, float]:
    if len(values) < 2:
        return float(values[0]), float(values[0])
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return quartiles[0], quartiles[2]


def run_scenario(generator: Callable[[], list[Order]]) -> dict[str, float]:
    """Run one C20 scenario and return measured metrics."""
    env = SimulationEnvironment()
    stations = {ws_type: WorkStation(env, ws_type) for ws_type in WorkStationType}
    conveyor = Conveyor(env, transport_time=5.0)

    orders = generator()
    throughput_times: list[float] = []

    def process_next_step(order: Order, plan: list, step: int) -> None:
        if step >= len(plan):
            completion_time = float(env.now.macro)
            throughput_times.append(completion_time - order.earliest_release_date)
            return

        op = plan[step]
        ws_type = get_operation_ws(op)
        ws = stations[ws_type]
        delay = get_processing_time(ws_type, order.product_type)

        def on_finish(finished_order: Order) -> None:
            conveyor.transport(
                finished_order, lambda o: process_next_step(o, plan, step + 1)
            )

        ws.request(order, delay, on_finish)

    for order in orders:
        plan = get_process_plan(order.product_type)
        env.schedule(
            order.earliest_release_date,
            lambda o=order, p=plan: process_next_step(o, p, 0),
        )

    env.run(until_macro=100000.0)

    makespan = float(env.now.macro)
    median_tt = statistics.median(throughput_times) if throughput_times else 0.0
    return {
        "makespan": makespan,
        "median_tt": median_tt,
        "processed_operations": float(
            sum(ws.processed_count for ws in stations.values())
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Timing experiment for ARGESIM C20."
    )
    parser.add_argument("--repeat", type=int, default=9, help="Number of repetitions.")
    parser.add_argument("--warmup", type=int, default=1, help="Number of warmup runs.")
    arguments = parser.parse_args()
    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    report: dict[str, object] = {
        "benchmark": "ARGESIM-C20",
        "definition": "https://www.argesim.org/benchmarks/c20/",
        "scenarios": {},
    }

    scenarios = {
        "OSc1_FullInfo": generate_osc1_order_book,
        "OSc2_MediumInfo": generate_osc2_order_book,
        "OSc3_Reactive": generate_osc3_order_book,
    }

    for scenario_name, generator in scenarios.items():
        for _ in range(arguments.warmup):
            run_scenario(generator)

        durations: list[int] = []
        last_metrics = None
        for _ in range(arguments.repeat):
            started = time.perf_counter_ns()
            last_metrics = run_scenario(generator)
            durations.append(time.perf_counter_ns() - started)
        assert last_metrics is not None

        first_quartile, third_quartile = _quartiles(durations)
        report["scenarios"][scenario_name] = {
            "metrics": last_metrics,
            "durations_ns": durations,
            "median_ns": statistics.median(durations),
            "iqr_ns": third_quartile - first_quartile,
        }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
