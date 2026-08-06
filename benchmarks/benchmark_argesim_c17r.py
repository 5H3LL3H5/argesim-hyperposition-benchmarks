"""ARGESIM C17R (SIR Epidemic) Task 1 Experiment.

This script runs Task 1 of the ARGESIM C17R benchmark using the defined parameters
and initial values, recording trajectories and optionally plotting them if
matplotlib is available. It explicitly compares outcomes with expected
qualitative and quantitative behavior described in the ARGESIM benchmark definition.
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
    print("Reference: Miksch et al., SNE 25(1), 2015, 49-54 (Benchmark C17R Definition)")
    print("Experiment: Model Comparison (ODE base approach, Task 1)")
    print("Initial Parameters (Table 5):")
    print(" - N (Total Population) = 10000")
    print(" - C (Contacts) = 4")
    print(" - alpha (Infection Prob.) = 0.1")
    print(" - beta (Recovery Prob.) = 0.1")
    print(f"Initial State (S0, I0, R0): {C17_INITIAL_STATE}")
    print("----------------------------------------------------------")

    # Run the model using parameters from Task 1 (S0=9500, I0=500, R0=0, C=4, alpha=0.1, beta=0.1)
    result = solve_c17(
        method="rk45",
        t_bound=200.0,  # Extend to 200 to ensure we reach near-equilibrium
        options={"rtol": 1e-8, "atol": 1e-11, "max_step": 0.5},
    )

    final_S, final_I, final_R = result.final_state

    print(f"Outcome: Reached t={result.final_time} successfully.")
    print(f"Final State (S, I, R): ({final_S:.2f}, {final_I:.2f}, {final_R:.2f})")

    # Calculate confidence/conservation
    initial_sum = sum(C17_INITIAL_STATE)
    final_sum = sum(result.final_state)
    conservation_error = abs(initial_sum - final_sum)
    print(f"Confidence (Population Conservation Error): {conservation_error:.2e}")
    print("==========================================================")
    print("Validation against Literature Expectations (SNE 25(1) C17R Definition):")

    # 1. Population Conservation
    print(f" 1. Population invariant: S(t) + I(t) + R(t) = {final_sum:.2f} == N ({initial_sum:.2f}) -> ", end="")
    if conservation_error < 1e-8:
        print("PASS")
    else:
        print("FAIL")

    # 2. Endemic fade-out (I -> 0 as t -> inf)
    print(f" 2. Endemic fade-out: I(t) approaches 0 as time extends. Final I = {final_I:.4f} -> ", end="")
    if final_I < 1.0:
        print("PASS (Infected population practically 0)")
    else:
        print("WARN (Still active infections, consider extending t_bound)")

    # 3. Peak infection occurs
    states = result.states
    max_I = max(state[1] for state in states)
    max_I_idx = [state[1] for state in states].index(max_I)
    peak_time = result.times[max_I_idx]

    print(f" 3. Epidemic peak: Infection peaks at t={peak_time:.2f} with max I={max_I:.2f}")
    if max_I > C17_INITIAL_STATE[1]:
        print("    -> PASS (Classic SIR epidemic outbreak observed)")
    else:
        print("    -> FAIL (No outbreak)")

    print("==========================================================")

    # Optional Plotting
    try:
        import matplotlib.pyplot as plt
        import numpy as np

        times = np.array(result.times)
        states = np.array(result.states)
        S, I, R = states[:, 0], states[:, 1], states[:, 2]

        plt.figure(figsize=(10, 6))
        plt.plot(times, S, label="Susceptible (S)", color="blue", linewidth=2)
        plt.plot(times, I, label="Infected (I)", color="red", linewidth=2)
        plt.plot(times, R, label="Recovered (R)", color="green", linewidth=2)

        # Mark the peak
        plt.axvline(x=peak_time, color='gray', linestyle='--', alpha=0.5, label=f"Peak Infection (t={peak_time:.1f})")
        plt.plot(peak_time, max_I, 'ro')

        plt.title("ARGESIM C17R Task 1 - ODE Reference Solution\nValidating SNE 25(1) Definition Benchmark")
        plt.xlabel("Time")
        plt.ylabel("Population")
        plt.legend(loc="right")
        plt.grid(True, alpha=0.3)

        plot_path = "c17r_task1_trajectories.png"
        plt.savefig(plot_path, dpi=300)
        print(f"Saved highly-detailed trajectory plot to {plot_path}")
    except ImportError:
        print("Note: matplotlib/numpy not installed. Skipping plot generation.")

if __name__ == "__main__":
    run_task1()
