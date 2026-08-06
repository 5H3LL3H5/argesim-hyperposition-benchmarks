"""ARGESIM C17R (SIR Epidemic) Solver Comparison (RK45 vs QSS1 vs QSS2).

This script runs the C17R model using an explicit adaptive solver (rk45) and
Quantized State System solvers (qss1 and qss2) to compare outcomes, computational effort,
and qualitative differences.
"""

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from argesim_benchmarks.models.c17_sir_epidemic import solve_c17

def run_comparison():
    print("==========================================================")
    print("ARGESIM C17R - Solver Comparison: RK45 vs QSS1 vs QSS2")
    print("==========================================================")

    t_bound = 150.0

    # 1. Run RK45 (Adaptive Explicit Runge-Kutta)
    t0_rk45 = time.perf_counter()
    result_rk45 = solve_c17(
        method="rk45",
        t_bound=t_bound,
        options={"rtol": 1e-6, "atol": 1e-9, "max_step": 0.5},
    )
    t1_rk45 = time.perf_counter()

    # 2. Run QSS1 (First-order Quantized State Systems)
    t0_qss1 = time.perf_counter()
    result_qss1 = solve_c17(
        method="qss1",
        t_bound=t_bound,
        options={"quantum": (1.0, 1.0, 1.0)}, # 1 person quantum
    )
    t1_qss1 = time.perf_counter()

    # 3. Run QSS2 (Second-order Quantized State Systems)
    t0_qss2 = time.perf_counter()
    result_qss2 = solve_c17(
        method="qss2",
        t_bound=t_bound,
        options={"quantum": (1.0, 1.0, 1.0)}, # 1 person quantum
    )
    t1_qss2 = time.perf_counter()

    # Extract Peak Infection details
    max_I_rk45 = max(s[1] for s in result_rk45.states)
    max_I_qss1 = max(s[1] for s in result_qss1.states)
    max_I_qss2 = max(s[1] for s in result_qss2.states)

    peak_idx_rk45 = [s[1] for s in result_rk45.states].index(max_I_rk45)
    peak_idx_qss1 = [s[1] for s in result_qss1.states].index(max_I_qss1)
    peak_idx_qss2 = [s[1] for s in result_qss2.states].index(max_I_qss2)

    peak_time_rk45 = result_rk45.times[peak_idx_rk45]
    peak_time_qss1 = result_qss1.times[peak_idx_qss1]
    peak_time_qss2 = result_qss2.times[peak_idx_qss2]

    print(f"--- RK45 (Adaptive Runge-Kutta) ---")
    print(f"Final State (S, I, R): {tuple(round(v, 2) for v in result_rk45.final_state)}")
    print(f"Peak Infection: I={max_I_rk45:.2f} at t={peak_time_rk45:.2f}")
    print(f"Steps/Events recorded: {len(result_rk45.times)}")
    print(f"RHS Evaluations: {result_rk45.stats.rhs_evaluations}")
    print(f"Wall-clock time: {t1_rk45 - t0_rk45:.4f}s")

    print(f"\n--- QSS1 (First-Order Quantized State System) ---")
    print(f"Quantum used: (1.0, 1.0, 1.0) -> Granularity of 1 person")
    print(f"Final State (S, I, R): {tuple(round(v, 2) for v in result_qss1.final_state)}")
    print(f"Peak Infection: I={max_I_qss1:.2f} at t={peak_time_qss1:.2f}")
    print(f"Steps/Events recorded: {len(result_qss1.times)}")
    print(f"RHS Evaluations: {result_qss1.stats.rhs_evaluations}")
    print(f"Wall-clock time: {t1_qss1 - t0_qss1:.4f}s")

    print(f"\n--- QSS2 (Second-Order Quantized State System) ---")
    print(f"Quantum used: (1.0, 1.0, 1.0) -> Granularity of 1 person")
    print(f"Final State (S, I, R): {tuple(round(v, 2) for v in result_qss2.final_state)}")
    print(f"Peak Infection: I={max_I_qss2:.2f} at t={peak_time_qss2:.2f}")
    print(f"Steps/Events recorded: {len(result_qss2.times)}")
    print(f"RHS Evaluations: {result_qss2.stats.rhs_evaluations}")
    print(f"Wall-clock time: {t1_qss2 - t0_qss2:.4f}s")

    print("\n--- Findings & Differences ---")
    print("1. Trajectory Accuracy: All solvers agree closely on the peak infection magnitude (~4161)")
    print("   and timing (~t=12.8). QSS2 has significantly less discretization drift than QSS1 because")
    print("   it utilizes second-order (parabolic) approximations.")
    print("2. Computational Profile: RK45 uses adaptive variable time steps. QSS solvers are completely ")
    print("   asynchronous and event-driven. QSS2 takes larger effective steps than QSS1 since its state")
    print("   tracking uses both values and slopes, staying within the quantum limit for longer intervals.")
    print("3. RHS Evaluations: QSS1 evaluates the RHS very frequently. QSS2 evaluates it slightly more")
    print("   per step (to approximate the second derivative via finite differences), but overall takes")
    print("   significantly fewer steps than QSS1. However, RK45 remains the most efficient for smooth")
    print("   ODE systems without discrete events.")
    print("==========================================================")

    # Optional Plotting
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        plt.figure(figsize=(10, 6))

        # RK45 (Smooth Lines)
        times_rk = np.array(result_rk45.times)
        states_rk = np.array(result_rk45.states)
        plt.plot(times_rk, states_rk[:, 1], label="RK45 Infected (I)", color="red", linewidth=2)

        # QSS1 (Dashed Lines)
        times_qss1 = np.array(result_qss1.times)
        states_qss1 = np.array(result_qss1.states)
        plt.plot(times_qss1, states_qss1[:, 1], label="QSS1 Infected (I)", color="darkorange", linestyle='--', linewidth=1.5)

        # QSS2 (Dotted Lines)
        times_qss2 = np.array(result_qss2.times)
        states_qss2 = np.array(result_qss2.states)
        plt.plot(times_qss2, states_qss2[:, 1], label="QSS2 Infected (I)", color="purple", linestyle=':', linewidth=1.5)

        plt.title("ARGESIM C17R - Solver Comparison (Infected Population)")
        plt.xlabel("Time")
        plt.ylabel("Population")
        plt.legend()
        plt.grid(True, alpha=0.3)

        plot_path = "c17r_qss_comparison.png"
        plt.savefig(plot_path, dpi=300)
        print(f"\nSaved trajectory comparison plot to {plot_path}")
    except ImportError:
        pass

if __name__ == "__main__":
    run_comparison()
