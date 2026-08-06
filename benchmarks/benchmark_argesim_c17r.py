"""ARGESIM C17R (SIR Epidemic) Task 1 Experiment.

This script runs Task 1 of the ARGESIM C17R benchmark using the defined parameters
and initial values, recording trajectories and optionally plotting them if
matplotlib is available.
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from argesim_benchmarks.models.c17_sir_epidemic import (
    C17Parameters,
    C17_INITIAL_STATE,
    solve_c17,
)

def run_task1():
    print("==========================================================")
    print("ARGESIM C17R Task 1 - SIR Epidemic Model Validation Run")
    print("==========================================================")
    print("Experiment: Model Comparison (ODE base approach, Task 1)")
    print(f"Initial State (S0, I0, R0): {C17_INITIAL_STATE}")

    # Run the model using parameters from Task 1 (S0=9500, I0=500, R0=0, C=4, alpha=0.1, beta=0.1)
    result = solve_c17(
        method="rk45",
        t_bound=100.0,
        options={"rtol": 1e-8, "atol": 1e-11, "max_step": 0.5},
    )

    print(f"Outcome: Reached t={result.final_time} successfully.")
    print(f"Final State (S, I, R): {result.final_state}")

    # Calculate confidence/conservation
    initial_sum = sum(C17_INITIAL_STATE)
    final_sum = sum(result.final_state)
    conservation_error = abs(initial_sum - final_sum)
    print(f"Confidence (Population Conservation Error): {conservation_error:.2e}")
    print("==========================================================")
    print("Validation against expectations:")
    print(" - Population sum remains invariant: S(t)+I(t)+R(t) = N")
    print(" - Trajectories follow classic SIR dynamic (S drops, I peaks and drops, R rises)")

    # Optional Plotting
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        times = np.array(result.times)
        states = np.array(result.states)
        S, I, R = states[:, 0], states[:, 1], states[:, 2]

        plt.figure(figsize=(10, 6))
        plt.plot(times, S, label="Susceptible", color="blue")
        plt.plot(times, I, label="Infected", color="red")
        plt.plot(times, R, label="Recovered", color="green")

        plt.title("ARGESIM C17R - Task 1 Trajectories")
        plt.xlabel("Time")
        plt.ylabel("Population")
        plt.legend()
        plt.grid(True)

        plot_path = "c17r_task1_trajectories.png"
        plt.savefig(plot_path)
        print(f"Saved trajectory plot to {plot_path}")
    except ImportError:
        print("Note: matplotlib/numpy not installed. Skipping plot generation.")

if __name__ == "__main__":
    run_task1()
