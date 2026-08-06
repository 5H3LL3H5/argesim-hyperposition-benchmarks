#!/usr/bin/env python3
"""Execute ARGESIM C16 tasks, generate plots and print validation metrics."""

import argparse
import random
import statistics

from argesim_benchmarks.models.c16_restaurant_business import (
    C16Parameters,
    C16Simulation,
    c16_task_a,
    c16_task_b,
    c16_task_c,
)

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

def run_task_a(runs: int) -> None:
    print(f"--- Task A: Time Domain Analysis (Runs: {runs}) ---")
    print("Initial Parameters: Default (3000 people, 30 restaurants, tax=20%)")

    # Run multiple times to calculate confidence
    results = []
    time_series = None

    # Perform runs
    for run in range(runs):
        res = c16_task_a(runs=1, seed=42 + run)
        results.append(res["average_after_5_years"])
        if run == 0:
            time_series = res["time_series_10_years"]

    mean = statistics.mean(results)
    stdev = statistics.stdev(results) if runs > 1 else 0.0

    print(f"Outcome (Average after 5th year): {mean:.2f} restaurants")
    print(f"Confidence (StdDev): {stdev:.2f}")

    # Generate Plot
    if HAS_MATPLOTLIB and time_series:
        weeks = list(range(len(time_series)))
        plt.figure(figsize=(10, 6))
        plt.plot(weeks, time_series, label="Run 1 Trajectory")
        plt.title("Task A: Number of Restaurants over 10 Years")
        plt.xlabel("Weeks")
        plt.ylabel("Number of Restaurants")
        plt.grid(True)
        plt.legend()
        plt.savefig("c16_task_a_trajectory.png")
        print("Saved plot to c16_task_a_trajectory.png")
        plt.close()

def run_task_b() -> None:
    print("\n--- Task B: Tax Income Maximization ---")
    print("Initial Parameters: Default, varying tax rate from 0% to 100% in 5% steps")
    tax_rates = [i * 0.05 for i in range(21)]

    # Reduce runs per rate to speed up test execution since pure python
    runs_per_rate = 2
    averaged_results = {rate: 0.0 for rate in tax_rates}

    for run in range(runs_per_rate):
        res = c16_task_b(tax_rates=tax_rates, seed=100 + run)
        for rate, tax in res.items():
            averaged_results[rate] += tax / runs_per_rate

    best_rate = max(averaged_results, key=averaged_results.get)
    best_tax = averaged_results[best_rate]

    print(f"Outcome (Optimal Tax Rate): {best_rate*100:.0f}%")
    print(f"Maximum Tax Collected: {best_tax:.2f}")

    if HAS_MATPLOTLIB:
        rates = sorted(averaged_results.keys())
        taxes = [averaged_results[r] for r in rates]
        plt.figure(figsize=(10, 6))
        plt.plot([r*100 for r in rates], taxes, marker='o')
        plt.title("Task B: Tax Income vs Tax Rate")
        plt.xlabel("Tax Rate (%)")
        plt.ylabel("Total Tax Collected")
        plt.grid(True)
        plt.savefig("c16_task_b_tax.png")
        print("Saved plot to c16_task_b_tax.png")
        plt.close()

def run_task_c() -> None:
    print("\n--- Task C: Restaurant Revenue Analysis ---")
    print("Initial Parameters: Default, varying k from 0 to 6 in 0.5 steps")
    k_values = [i * 0.5 for i in range(13)]

    # Reduce runs to speed up execution
    runs_per_k = 2
    averaged_results = {k: 0.0 for k in k_values}

    for run in range(runs_per_k):
        res = c16_task_c(k_values=k_values, seed=200 + run)
        for k, rev in res.items():
            averaged_results[k] += rev / runs_per_k

    if HAS_MATPLOTLIB:
        ks = sorted(averaged_results.keys())
        revs = [averaged_results[k] for k in ks]
        plt.figure(figsize=(10, 6))
        plt.plot(ks, revs, marker='o')
        plt.title("Task C: Restaurant Revenue vs k")
        plt.xlabel("Parameter k")
        plt.ylabel("Total System Revenue (proxy)")
        plt.grid(True)
        plt.savefig("c16_task_c_revenue.png")
        print("Saved plot to c16_task_c_revenue.png")
        plt.close()

    print("Task C evaluation completed.")

def main():
    parser = argparse.ArgumentParser(description="Run C16 Benchmark")
    parser.add_argument("--runs", type=int, default=3, help="Number of runs for Task A")
    args = parser.parse_args()

    if not HAS_MATPLOTLIB:
        print("WARNING: matplotlib not installed. Plots will not be generated.")

    run_task_a(args.runs)
    run_task_b()
    run_task_c()

if __name__ == "__main__":
    main()
