#!/usr/bin/env python3
"""Validation script for ARGESIM C03 (Generalized Class-E Amplifier)."""

import os
import sys
from pathlib import Path
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import numpy as np
    import matplotlib.pyplot as plt
    HAS_PLOTTING = True
except ImportError:
    HAS_PLOTTING = False

from argesim_benchmarks.models.c03_amplifier import (
    C03Parameters,
    c03_task_b,
    c03_task_c,
)

def plot_task_b(result) -> None:
    if not HAS_PLOTTING:
        print("matplotlib/numpy not installed. Skipping plot generation.")
        return

    times = np.array(result.times) * 1e6  # convert to microseconds
    states = np.array(result.states)

    # states are x1=IL1, x2=VC2, x3=IL3, x4=VC4
    # The benchmark defines R(t) = 0.05 or 5E6, and asks for:
    # 1. Current in switch resistor IR(t) = x2 / R(t)
    # 2. Output voltage VL = x3 * RL

    p = C03Parameters()
    def get_rt(t):
        from argesim_benchmarks.models.c03_amplifier import _r_t
        return _r_t(t, p)

    rt = np.array([get_rt(t) for t in result.times])
    ir = states[:, 1] / rt
    vl = states[:, 2] * p.rl

    fig, axes = plt.subplots(3, 1, figsize=(10, 12), sharex=True)

    # State variables
    axes[0].plot(times, states[:, 0], label="IL1 (A)")
    axes[0].plot(times, states[:, 2], label="IL3 (A)")
    axes[0].set_ylabel("Current (A)")
    axes[0].legend()
    axes[0].grid(True)

    axes[1].plot(times, states[:, 1], label="VC2 (V)")
    axes[1].plot(times, states[:, 3], label="VC4 (V)")
    axes[1].plot(times, vl, label="VL (V)")
    axes[1].set_ylabel("Voltage (V)")
    axes[1].legend()
    axes[1].grid(True)

    axes[2].plot(times, ir, label="IR(t) (A)")
    axes[2].set_xlabel("Time (us)")
    axes[2].set_ylabel("Current (A)")
    axes[2].legend()
    axes[2].grid(True)

    plt.suptitle("C03 Task B: Simulation over [0, 100 us]")
    plt.tight_layout()
    plt.savefig("c03_task_b.png")
    print("Saved C03 Task B plot to c03_task_b.png")

def plot_task_c(results) -> None:
    if not HAS_PLOTTING:
        return

    fig, axes = plt.subplots(1, 1, figsize=(8, 6))

    for trf, result in results.items():
        states = np.array(result.states)
        # Phase plane curve of dx3/dt = VL3 as function of x3 = IL3
        # We need dx3/dt.
        # dx3 = (x2 - RL*x3 - x4) / L3
        p = C03Parameters()
        x2 = states[:, 1]
        x3 = states[:, 2]
        x4 = states[:, 3]
        dx3_dt = (x2 - p.rl * x3 - x4) / p.l3

        axes.plot(x3, dx3_dt, label=f"TRF = {trf:.1e} s")

    axes.set_xlabel("IL3 = x3 (A)")
    axes.set_ylabel("d(IL3)/dt = VL3/L3 (A/s)")
    axes.set_title("C03 Task C: Phase plane curves")
    axes.legend()
    axes.grid(True)

    plt.tight_layout()
    plt.savefig("c03_task_c.png")
    print("Saved C03 Task C plot to c03_task_c.png")

def main():
    print("Running C03 Task B...")
    # Use loose tolerance to ensure it finishes quickly for this validation script
    res_b = c03_task_b(options={"rtol": 1e-4, "atol": 1e-6, "max_step": 1e-6})
    print(f"Task B completed with {len(res_b.times)} steps. Final state: {res_b.final_state}")
    plot_task_b(res_b)

    print("\nRunning C03 Task C...")
    # Again, loose tolerances for quick run
    res_c = c03_task_c(options={"rtol": 1e-4, "atol": 1e-6, "max_step": 1e-6}, initial_state=res_b.final_state)
    for trf, res in res_c.items():
        print(f"Task C (TRF={trf:.1e}) completed with {len(res.times)} steps. Final state: {res.final_state}")
    plot_task_c(res_c)

if __name__ == "__main__":
    main()

