"""Standalone script to run and plot ARGESIM C22 benchmark trajectories.
Requires matplotlib and numpy for visualization.
"""

import os
import sys

# Make sure our module path is available
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from argesim_benchmarks.models.c22_queuing_policies import (
    c22_basic,
    c22_classing,
    c22_jockeying,
    c22_reneging,
)

def run_and_plot():
    # Make sure we use an agg backend if headless
    import matplotlib
    matplotlib.use('Agg')

    print("Running C22 Benchmark Tasks...")

    # Run Basic
    res_basic = c22_basic()
    det_basic = res_basic["deterministic"]
    stoch_basic = res_basic["stochastic"]
    print(f"Basic (Deterministic): avg_wait={det_basic['tq_avg']:.2f}, max_wait={det_basic['tq_max']:.2f}")
    print(f"Basic (Stochastic): avg_wait={stoch_basic['tq_avg']:.2f}, max_wait={stoch_basic['tq_max']:.2f}")

    # Run Jockeying
    res_jock = c22_jockeying()
    stoch_jock = res_jock["stochastic"]
    print(f"Jockeying (Stochastic): avg_wait={stoch_jock['tq_avg']:.2f}, max_wait={stoch_jock['tq_max']:.2f}, events={stoch_jock['jockey_events']}")

    # Run Reneging
    res_ren = c22_reneging()
    stoch_ren = res_ren["stochastic"]
    print(f"Reneging (Stochastic): avg_wait={stoch_ren['tq_avg']:.2f}, max_wait={stoch_ren['tq_max']:.2f}, events={stoch_ren['renege_events']}")

    # Run Classing
    res_class = c22_classing()
    stoch_class = res_class["stochastic"]
    print(f"Classing (Stochastic):")
    for c, stats in stoch_class["class_stats"].items():
        print(f"  Class {c}: avg_wait={stats['avg']:.2f}, max_wait={stats['max']:.2f}")

    try:
        import matplotlib.pyplot as plt
        import numpy as np

        # Plot for Basic Deterministic
        plt.figure(figsize=(10, 6))
        times = det_basic["times_out"]
        ids = det_basic["ids_out"]
        plt.stem(times, ids, basefmt=" ")
        plt.title("C22 Basic (Deterministic) - IDs over Termination Time")
        plt.xlabel("Time (t)")
        plt.ylabel("Entity ID")
        plt.grid(True)
        plt.savefig("c22_basic_deterministic.png")
        plt.close()
        print("Generated c22_basic_deterministic.png")
    except ImportError:
        print("Warning: matplotlib and/or numpy not installed. Skipping plot generation.")

if __name__ == "__main__":
    run_and_plot()
