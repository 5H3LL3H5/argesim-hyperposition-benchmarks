"""Generate C14 validation outputs and plots."""

import numpy as np
import matplotlib.pyplot as plt

from argesim_benchmarks.models.c14_supply_chain import (
    c14_task_a1,
    c14_task_c2,
)

def main():
    print("Running ARGESIM C14 Supply Chain Validation...")

    # Task a1: Single trajectory for 30 days
    history = c14_task_a1(seed=123)

    times_days = []
    total_stock_d1 = []

    for time_sec, stock in history:
        times_days.append(time_sec / (3600 * 24))
        total_stock_d1.append(sum(stock.values()))

    plt.figure(figsize=(10, 6))
    plt.plot(times_days, total_stock_d1, drawstyle='steps-post', label='D1 Total Stock')
    plt.title('ARGESIM C14 - Task A: Distributor D1 Stock over 30 Days')
    plt.xlabel('Time (Days)')
    plt.ylabel('Total Products in Stock')
    plt.grid(True)
    plt.legend()
    plt.savefig('c14_trajectory.png')
    print("Saved plot to c14_trajectory.png")

    # Task c2: Monte Carlo runs for all 3 strategies
    print("\nRunning Monte Carlo simulations (100 runs per strategy)...")
    metrics = c14_task_c2(seed=123, runs=100)

    print("\nOutcome Comparison (D1 Metrics):")
    print("-" * 80)
    print(f"{'Strategy':<15} | {'Metric':<10} | {'Mean':>10} | {'Dev':>10} | {'Min':>10} | {'Max':>10}")
    print("-" * 80)

    for strategy_name, strategy_metrics in metrics.items():
        for metric_name in ["C", "N", "R"]:
            vals = strategy_metrics[metric_name]
            print(f"{strategy_name:<15} | {metric_name:<10} | {vals['mean']:10.2f} | {vals['dev']:10.2f} | {vals['min']:10.2f} | {vals['max']:10.2f}")
        print("-" * 80)

if __name__ == "__main__":
    main()
