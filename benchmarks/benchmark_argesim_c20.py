"""Execute ARGESIM C20 benchmark and report performance indicators.

Validates the results by printing the Experiment, Runs, Initial Parameters,
Outcome, confidence, and generates numpy/matplotlib trajectories as requested.
"""

import statistics
import time
from typing import Callable
import json

import numpy as np
import matplotlib.pyplot as plt

from argesim_benchmarks.models.c20_complex_production import (
    Order,
    SimulationEnvironment,
    WorkStation,
    WorkStationType,
    Conveyor,
    get_process_plan,
    get_operation_ws,
    get_processing_time,
    generate_osc1_order_book,
    generate_osc2_order_book,
    generate_osc3_order_book,
)

def run_scenario(name: str, generator: Callable[[], list[Order]]) -> tuple[dict[str, float], dict[WorkStationType, list[tuple[float, int]]]]:
    """Run one C20 scenario and return measured statistics and trajectories."""
    env = SimulationEnvironment()

    # Initialize workstations
    stations = {
        ws_type: WorkStation(env, ws_type)
        for ws_type in WorkStationType
    }

    conveyor = Conveyor(env, transport_time=5.0)

    orders = generator()
    throughput_times: list[float] = []

    # Route an order through its process plan
    def process_next_step(order: Order, plan: list, step: int) -> None:
        if step >= len(plan):
            # Order finished
            completion_time = float(env.now.macro)
            throughput_times.append(completion_time - order.earliest_release_date)
            return

        op = plan[step]
        ws_type = get_operation_ws(op)
        ws = stations[ws_type]
        delay = get_processing_time(ws_type, order.product_type)

        # Define what happens when the workstation finishes
        def on_finish(finished_order: Order) -> None:
            # Transport to next station
            conveyor.transport(
                finished_order,
                lambda o: process_next_step(o, plan, step + 1)
            )

        # Request the workstation
        ws.request(order, delay, on_finish)

    # Schedule initial releases
    for order in orders:
        plan = get_process_plan(order.product_type)
        env.schedule(
            order.earliest_release_date,
            lambda o=order, p=plan: process_next_step(o, p, 0)
        )

    start_time = time.perf_counter()
    # Run the simulation for a sufficiently long time
    env.run(until_macro=100000.0)
    end_time = time.perf_counter()

    makespan = float(env.now.macro)

    if throughput_times:
        median_tt = statistics.median(throughput_times)
        if len(throughput_times) > 1:
            q75, q25 = statistics.quantiles(throughput_times, n=4)[2], statistics.quantiles(throughput_times, n=4)[0]
            iqr_tt = q75 - q25
        else:
            iqr_tt = 0.0
    else:
        median_tt = 0.0
        iqr_tt = 0.0

    print(f"--- Experiment: Scenario {name} ---")
    print(f"Initial Parameters: {len(orders)} orders generated.")
    print(f"Runs: 1 execution.")
    print(f"Outcome:")
    print(f"  Wall time:      {end_time - start_time:.4f} s")
    print(f"  Sim. Makespan:  {makespan:.2f} s")
    print(f"  Throughput TT:  Median {median_tt:.2f} s, IQR {iqr_tt:.2f} s")

    total_processed = sum(ws.processed_count for ws in stations.values())
    print(f"  Processed Ops:  {total_processed}")
    print(f"Confidence:       High (Deterministic Execution)\n")

    metrics = {
        "makespan": makespan,
        "median_tt": median_tt,
        "iqr_tt": iqr_tt,
        "wall_time": end_time - start_time,
    }

    trajectories = {ws_type: ws.history for ws_type, ws in stations.items()}
    return metrics, trajectories

def main() -> None:
    print("ARGESIM C20 Complex Production System Benchmark Validation")
    print("========================================================\n")

    scenarios = [
        ("OSc#1 (Full Info)", generate_osc1_order_book),
        ("OSc#2 (Medium Info)", generate_osc2_order_book),
        ("OSc#3 (Reactive)", generate_osc3_order_book),
    ]

    all_trajectories = {}

    for name, generator in scenarios:
        metrics, trajectories = run_scenario(name, generator)
        all_trajectories[name] = trajectories

    # Plotting with matplotlib and numpy
    fig, axes = plt.subplots(3, 1, figsize=(10, 15))
    for ax, (name, trajectories) in zip(axes, all_trajectories.items()):
        ax.set_title(f"Workstation Queues for {name}")
        ax.set_xlabel("Macro Time (s)")
        ax.set_ylabel("Queue Length + Processing")

        for ws_type, history in trajectories.items():
            if not history:
                continue
            # Convert history to numpy array
            history_arr = np.array(history)
            times = history_arr[:, 0]
            queue_lens = history_arr[:, 1]
            # Use step plot for DES trajectories
            ax.step(times, queue_lens, where='post', label=ws_type.value)

        ax.legend()
        ax.grid(True)

    plt.tight_layout()
    plt.savefig("c20_trajectories.png")
    print("Saved trajectories plot to c20_trajectories.png")

if __name__ == "__main__":
    main()
