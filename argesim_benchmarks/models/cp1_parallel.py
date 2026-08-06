"""ARGESIM CP1: Parallel Simulation Techniques.

This file provides the numerical benchmark models for the CP1 tasks:
- Task A: Monte Carlo study of a damped mass-spring system.
- Task B: Coupled predator-prey population model (10 ODEs).
- Task C: Swinging rope PDE discretized by the method of lines.
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from ..ivp import InitialValueProblem, Rhs, Vector


# --- Task A: Monte Carlo Study ---

def cp1_task_a_ivp(
    damping_factor: float,
    *,
    mass: float = 450.0,
    stiffness: float = 9000.0,
    t_bound: float = 2.0,
) -> InitialValueProblem:
    """Create the IVP for the Monte Carlo mass-spring study.

    Equation: m x'' + d x' + k x = 0
    State vector: (x, x')
    Initial condition: x(0) = 0.1, x'(0) = 0
    The damping factor d is typically drawn from U(800, 1200).
    """
    m = float(mass)
    k = float(stiffness)
    d = float(damping_factor)
    if m <= 0.0:
        raise ValueError("mass must be positive")

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        x, v = state
        # x' = v
        # v' = (-k * x - d * v) / m
        return (v, (-k * x - d * v) / m)

    return InitialValueProblem(
        rhs,
        0.0,
        (0.1, 0.0),
        t_bound,
        name=f"ARGESIM-CP1-A-damped-oscillator-d{d:.1f}",
        autonomous=True,
    )


# --- Task B: Coupled Predator-Prey Population ---

# Terminal values at t=100 from the official definition table
CP1_TASK_B_TERMINAL_VALUES: dict[str, float] = {
    "v1": 0.40494874,
    "v2": 3.9389271,
    "w1": 0.45572852,
    "w2": 2.06389283,
    "x1": 1.86489724,
    "x2": 3.18278282,
    "y1": 0.4677289,
    "y2": 1.20213106,
    "z1": 2.27700122,
    "z2": 4.10808012,
}

# Equilibrium solutions from the official definition table
CP1_TASK_B_EQUILIBRIUM: dict[str, float] = {
    "v1": 0.41235712,
    "v2": 3.992722,
    "w1": 0.45765668,
    "w2": 2.07652643,
    "x1": 1.86502448,
    "x2": 3.18097946,
    "y1": 0.47392759,
    "y2": 1.20497504,
    "z1": 2.2773994,
    "z2": 4.10656804,
}

def cp1_task_b_rhs() -> Rhs:
    """Return the RHS function for the coupled predator-prey model."""
    # Parameters for v
    a_v, b_v, c_v, d_v, e_v, f_v = 2.0, 0.5, 0.01, 0.2, 0.4, 0.02
    g_v, h_v, j_v, k_v = 0.01, 0.02, 0.01, 0.03
    # Parameters for w
    a_w, b_w, c_w, d_w, e_w, f_w = 1.0, 0.5, 0.02, 0.1, 0.4, 0.04
    g_w, h_w = 0.02, 0.04
    # Parameters for x
    a_x, b_x, c_x, d_x, e_x, f_x = 3.0, 0.9, 0.02, 0.2, 0.2, 0.04
    g_x, h_x = 0.025, 0.1
    # Parameters for y
    a_y, b_y, c_y, d_y, e_y, f_y = 1.0, 0.8, 0.04, 0.2, 0.6, 0.07
    g_y, h_y = 0.03, 0.025
    # Parameters for z
    a_z, b_z, c_z, d_z, e_z, f_z = 3.0, 0.7, 0.02, 0.5, 0.3, 0.04
    g_z, h_z = 0.02, 0.04

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        v1, v2, w1, w2, x1, x2, y1, y2, z1, z2 = state

        # Equations for v
        r_v = v2 * (g_v * w1 + h_v * x1 + j_v * y1 + k_v * z1)
        dv1 = a_v * v1 - b_v * v1 * v2 - c_v * v1 * v1
        dv2 = -d_v * v2 + e_v * v1 * v2 - f_v * v2 * v2 + r_v

        # Equations for w
        r_w = w1 * (-g_w * v2 + h_w * x2)
        dw1 = a_w * w1 - b_w * w1 * w2 - c_w * w1 * w1 + r_w
        dw2 = -d_w * w2 + e_w * w1 * w2 - f_w * w2 * w2

        # Equations for x
        r_x = -g_x * x1 * v2
        s_x = -h_x * x2 * w1
        dx1 = a_x * x1 - b_x * x1 * x2 - c_x * x1 * x1 + r_x
        dx2 = -d_x * x2 + e_x * x1 * x2 - f_x * x2 * x2 + s_x

        # Equations for y
        r_y = y1 * (-g_y * v2 + h_y * z2)
        dy1 = a_y * y1 - b_y * y1 * y2 - c_y * y1 * y1 + r_y
        dy2 = -d_y * y2 + e_y * y1 * y2 - f_y * y2 * y2

        # Equations for z
        r_z = -g_z * z1 * v2
        s_z = -h_z * z2 * y1
        dz1 = a_z * z1 - b_z * z1 * z2 - c_z * z1 * z1 + r_z
        dz2 = -d_z * z2 + e_z * z1 * z2 - f_z * z2 * z2 + s_z

        return (dv1, dv2, dw1, dw2, dx1, dx2, dy1, dy2, dz1, dz2)

    return rhs

def cp1_task_b_ivp(*, t_bound: float = 100.0) -> InitialValueProblem:
    """Create the IVP for the coupled predator-prey model."""
    # All initial populations are normalized to 1.
    initial_state = (1.0,) * 10
    return InitialValueProblem(
        cp1_task_b_rhs(),
        0.0,
        initial_state,
        t_bound,
        name="ARGESIM-CP1-B-predator-prey",
        autonomous=True,
    )


# --- Task C: Partial Differential Equation ---

def cp1_task_c_ivp(
    interior_points: int = 799,
    *,
    t_bound: float = 30.0,
    a: float = 2.0,
    b: float = 1.0,
    d: float = 0.2,
    omega: float = 1.0,
    length: float = 10.0,
) -> InitialValueProblem:
    """Create the IVP for the swinging rope PDE (Method of Lines).

    PDE: u_xx = a * u_tt
    Boundary: u(0, t) = 0, u(L, t) = b * exp(-d*t) * sin(omega*t)
    Initial: u(x, 0) = u_t(x, 0) = 0
    """
    if interior_points < 1:
        raise ValueError("interior_points must be positive")
    if length <= 0.0:
        raise ValueError("length must be positive")

    # N is the number of intervals. N = interior_points + 1
    n_intervals = interior_points + 1
    k = length / n_intervals
    coefficient = 1.0 / (k * k * a)

    def rhs(time: float, state: Sequence[float]) -> Vector:
        # state consists of `interior_points` positions followed by `interior_points` velocities
        u = state[:interior_points]
        v = state[interior_points:]

        # boundaries
        u0 = 0.0
        uL = b * math.exp(-d * time) * math.sin(omega * time)

        padded_u = (u0, *u, uL)

        accelerations = tuple(
            coefficient * (padded_u[i] - 2.0 * padded_u[i+1] + padded_u[i+2])
            for i in range(interior_points)
        )

        # derivative is (velocities, accelerations)
        return (*v, *accelerations)

    # Initial conditions: u(x,0) = 0, u_t(x,0) = 0
    initial_state = (0.0,) * (2 * interior_points)

    return InitialValueProblem(
        rhs,
        0.0,
        initial_state,
        t_bound,
        name=f"ARGESIM-CP1-C-swinging-rope-N{n_intervals}",
        autonomous=False,
    )
