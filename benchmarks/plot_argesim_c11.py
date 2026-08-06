#!/usr/bin/env python3
"""Plotting script for ARGESIM C11 trajectories."""

import sys
from pathlib import Path

try:
    import matplotlib.pyplot as plt
    import numpy as np
except ImportError:
    print("This script requires numpy and matplotlib.")
    sys.exit(1)

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argesim_benchmarks.models.c11_scara_robot import solve_c11, C11_TARGET_STATE

def plot_task(task: str, title: str, filename: str):
    print(f"Solving task {task}...")
    res = solve_c11('rk45', t_bound=2.0, task=task)
    times = np.array(res.times)
    states = np.array(res.states)

    q1 = states[:, 0]
    q2 = states[:, 1]
    q3 = states[:, 2]

    plt.figure(figsize=(10, 6))
    plt.plot(times, q1, label="q1 (rad)")
    plt.plot(times, q2, label="q2 (rad)")
    plt.plot(times, q3, label="q3 (m)")

    plt.axhline(C11_TARGET_STATE[0], color='r', linestyle='--', label="target q1/q2")
    plt.axhline(C11_TARGET_STATE[2], color='g', linestyle='--', label="target q3")

    plt.xlabel("Time (s)")
    plt.ylabel("Joint Positions")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(filename)
    print(f"Saved plot to {filename}")

if __name__ == "__main__":
    plot_task('b', 'ARGESIM C11 Task B - Point-to-point Trajectory', 'c11_task_b_trajectory.png')
    plot_task('c', 'ARGESIM C11 Task C - Collision Avoidance Trajectory', 'c11_task_c_trajectory.png')
