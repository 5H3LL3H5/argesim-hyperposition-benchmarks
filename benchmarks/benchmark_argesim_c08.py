#!/usr/bin/env python3
"""ARGESIM C08 Task C: Variance Reduction Experiments (Statistical Analysis)."""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.models.c08_canal_and_lock import CanalAndLock, Barge, Direction


def run_replication(
    eastmax: int,
    westmax: int,
    duration: float,
    seed: int
) -> tuple[float, list[tuple[float, int, int]]]:
    """Run a single replication and return the pooled average transit time."""
    rng = random.Random(seed)

    model = CanalAndLock(eastmax, westmax)

    # First arrivals are uniformly distributed
    # East: 15 +/- 15 (i.e. uniform 0 to 30)
    # West: 10 +/- 10 (i.e. uniform 0 to 20)
    east_arrival = rng.uniform(0.0, 30.0)
    west_arrival = rng.uniform(0.0, 20.0)

    barge_id = 0
    from nsa_devs.hypertime import HyperTime

    while east_arrival <= duration:
        model.schedule_arrival(Barge(barge_id, Direction.EASTBOUND, HyperTime.at(east_arrival)))
        barge_id += 1
        east_arrival += rng.expovariate(1.0 / 75.0)

    while west_arrival <= duration:
        model.schedule_arrival(Barge(barge_id, Direction.WESTBOUND, HyperTime.at(west_arrival)))
        barge_id += 1
        west_arrival += rng.expovariate(1.0 / 75.0)

    model.run(duration)

    if not model.completed_barges:
        return 0.0, model.queue_trajectory

    total_time = sum(t for _, t in model.completed_barges)
    avg_time = total_time / len(model.completed_barges)

    return avg_time, model.queue_trajectory


def main() -> None:
    duration = 14400.0  # 10 days
    replications = 100

    # We will just generate 100 random seeds for dataset 1
    base_seed = 42
    rng = random.Random(base_seed)
    seeds = [rng.randint(0, 2**31) for _ in range(replications)]

    # Case 1: Eastmax=5, Westmax=5
    results_5 = []
    trajectory_sample = []
    for i, s in enumerate(seeds):
        avg_time, traj = run_replication(5, 5, duration, s)
        results_5.append(avg_time)
        if i == 0:
            trajectory_sample = traj

    # Case 2: Eastmax=6, Westmax=6
    results_6 = []
    for s in seeds:
        avg_time, _ = run_replication(6, 6, duration, s)
        results_6.append(avg_time)

    # Compute statistics
    mean_5 = sum(results_5) / replications
    variance_5 = sum((x - mean_5)**2 for x in results_5) / (replications - 1)

    mean_6 = sum(results_6) / replications
    variance_6 = sum((x - mean_6)**2 for x in results_6) / (replications - 1)

    differences = [r5 - r6 for r5, r6 in zip(results_5, results_6)]
    mean_diff = sum(differences) / replications

    report = {
        "benchmark": "ARGESIM-C08-task-C",
        "definition": "https://www.argesim.org/benchmarks/c08/",
        "experiment": {
            "duration_minutes": duration,
            "replications": replications,
            "interarrival_distribution": "exponential",
            "interarrival_mean": 75.0,
        },
        "results": {
            "max_5_5": {
                "mean_pooled_transit_time": mean_5,
                "variance": variance_5,
            },
            "max_6_6": {
                "mean_pooled_transit_time": mean_6,
                "variance": variance_6,
            },
            "mean_difference_5_minus_6": mean_diff
        },
        "trajectory_sample_run_0_points": len(trajectory_sample)
    }

    print(json.dumps(report, indent=2))

    if trajectory_sample:
        times = np.array([pt[0] for pt in trajectory_sample])
        east_queue = np.array([pt[1] for pt in trajectory_sample])
        west_queue = np.array([pt[2] for pt in trajectory_sample])

        plt.figure(figsize=(10, 6))
        plt.step(times, east_queue, label="Eastbound Queue", where="post")
        plt.step(times, west_queue, label="Westbound Queue", where="post", alpha=0.7)
        plt.title("ARGESIM C08 - Barge Queue Lengths (Task C, Single Run)")
        plt.xlabel("Time (minutes)")
        plt.ylabel("Number of Barges Waiting")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.savefig("c08_trajectory.png")
        print("Trajectory plot saved to c08_trajectory.png")


if __name__ == "__main__":
    main()
