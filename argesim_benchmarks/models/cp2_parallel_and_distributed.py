"""ARGESIM CP2: Parallel and Distributed Simulation.

Task 1: Monte Carlo Study (Spring-Mass System)
Task 2: Lattice Boltzmann Simulation (Cavity Flow, D2Q9)
Task 3: Partial Differential Equation Case Study (Swinging Rope)
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..ivp import InitialValueProblem, Rhs, Vector
from ..pde import wave_1d_ivp

# Task 1: Monte Carlo Study (Spring-Mass System)
# m * x'' + d * x' + k * x = 0
# Initial state: x(0) = 0, x'(0) = 0.1
# Parameters: k = 9000, m = 450
# d is uniformly distributed in [800, 1200]

CP2_MC_INITIAL_STATE: Vector = (0.0, 0.1)


@dataclass(frozen=True)
class CP2MonteCarloParameters:
    mass: float = 450.0
    stiffness: float = 9000.0
    damping: float = 1000.0

    def __post_init__(self) -> None:
        if self.mass <= 0.0 or not math.isfinite(self.mass):
            raise ValueError("mass must be positive and finite")
        if self.stiffness <= 0.0 or not math.isfinite(self.stiffness):
            raise ValueError("stiffness must be positive and finite")
        if self.damping < 0.0 or not math.isfinite(self.damping):
            raise ValueError("damping must be non-negative and finite")


_CP2_MC_DEFAULT_PARAMETERS = CP2MonteCarloParameters()


def cp2_monte_carlo_rhs(
    parameters: CP2MonteCarloParameters = _CP2_MC_DEFAULT_PARAMETERS,
) -> Rhs:
    """Return the rate equations for the spring-mass system (Task 1)."""
    k_m = parameters.stiffness / parameters.mass
    d_m = parameters.damping / parameters.mass

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        position, velocity = state
        return (velocity, -d_m * velocity - k_m * position)

    return rhs


def cp2_monte_carlo_problem(
    *,
    parameters: CP2MonteCarloParameters = _CP2_MC_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = CP2_MC_INITIAL_STATE,
    t_bound: float = 2.0,
) -> InitialValueProblem:
    """Build the CP2 Task 1 initial-value problem."""
    return InitialValueProblem(
        cp2_monte_carlo_rhs(parameters),
        0.0,
        initial_state,
        t_bound,
        name="ARGESIM-CP2-monte-carlo",
        autonomous=True,
    )


# Task 2: Lattice Boltzmann Simulation (Cavity Flow)
# Parameters:
# Grid size: nx * nx (e.g., 257)
# Top wall velocity: u0 = (0.1, 0)
# Reynolds number: Re = 1000
# Viscosity: nu = (nx - 1) * u0_x / Re
# D2Q9 velocities and weights:
# c0 = (0, 0), w0 = 4/9
# c1, c2, c3, c4 = (+-1, 0), (0, +-1), w = 1/9
# c5, c6, c7, c8 = (+-1, +-1), w = 1/36

CP2_LBM_WEIGHTS = (4.0 / 9.0,) + (1.0 / 9.0,) * 4 + (1.0 / 36.0,) * 4
CP2_LBM_VELOCITIES = (
    (0, 0),
    (1, 0),
    (0, 1),
    (-1, 0),
    (0, -1),
    (1, 1),
    (-1, 1),
    (-1, -1),
    (1, -1),
)
# Bounce-back reversed directions
CP2_LBM_REVERSE = (0, 3, 4, 1, 2, 7, 8, 5, 6)


def cp2_lbm_initial_state(
    nx: int = 257,
) -> tuple[tuple[list[float], ...], ...]:
    """Create the initial D2Q9 grid for Task 2."""
    if nx < 3:
        raise ValueError("grid size nx must be at least 3")

    # Initial macroscopic variables: rho = 1, u = (0, 0)
    # The equilibrium distribution for u=0 is just w_i * rho = w_i
    grid = []
    for _ in range(nx):
        row = []
        for _ in range(nx):
            row.append(list(CP2_LBM_WEIGHTS))
        grid.append(tuple(row))
    return tuple(grid)


def _compute_equilibrium(
    rho: float, ux: float, uy: float
) -> tuple[float, ...]:
    """Compute D2Q9 equilibrium distribution."""
    u_sq = ux * ux + uy * uy
    eq = []
    for i, w in enumerate(CP2_LBM_WEIGHTS):
        cx, cy = CP2_LBM_VELOCITIES[i]
        cu = cx * ux + cy * uy
        eq.append(w * rho * (1.0 + 3.0 * cu + 4.5 * cu * cu - 1.5 * u_sq))
    return tuple(eq)


def cp2_lbm_step(
    grid: tuple[tuple[list[float], ...], ...],
    nx: int,
    omega: float,
    u0_x: float = 0.1,
) -> tuple[tuple[list[float], ...], ...]:
    """Perform one LBM collision and propagation step."""

    # Collision
    f_post_collision = []
    for y in range(nx):
        row = []
        for x in range(nx):
            f = grid[y][x]
            rho = sum(f)

            # Boundary condition handling during collision
            if y == nx - 1: # Top wall (moving)
                # Compute equilibrium with u = (u0_x, 0)
                eq = _compute_equilibrium(rho, u0_x, 0.0)
                row.append(list(eq))
            elif y == 0 or x == 0 or x == nx - 1: # Fixed walls
                # Bounce-back: reverse incoming populations
                # We defer bounce back to the propagation step or handle here
                # Standard full-way bounce-back sets f*[x, c_i] = f[x, -c_i]
                bb = [f[i] for i in range(9)]
                row.append(bb)
            else: # Bulk
                ux = (f[1] + f[5] + f[8] - f[3] - f[6] - f[7]) / rho
                uy = (f[2] + f[5] + f[6] - f[4] - f[7] - f[8]) / rho
                eq = _compute_equilibrium(rho, ux, uy)
                row.append([f[i] - omega * (f[i] - eq[i]) for i in range(9)])
        f_post_collision.append(row)

    # Propagation
    # f_new_i(x + c_i, t+1) = f_post_collision_i(x, t)
    # We initialize the new grid with zeros
    new_grid = []
    for _ in range(nx):
        new_grid.append([[0.0] * 9 for _ in range(nx)])

    for y in range(nx):
        for x in range(nx):
            for i in range(9):
                cx, cy = CP2_LBM_VELOCITIES[i]
                nx_x = x + cx
                nx_y = y + cy
                # Only propagate if within bounds. Populations leaving the domain are lost,
                if 0 <= nx_x < nx and 0 <= nx_y < nx:
                    new_grid[nx_y][nx_x][i] = f_post_collision[y][x][i]
                else:
                    new_grid[y][x][CP2_LBM_REVERSE[i]] += f_post_collision[y][x][i]

    # Convert inner lists back to tuples for structure consistency if needed, or keep lists
    return tuple(tuple(col) for col in new_grid)


# Task 3: Swinging Rope PDE
# u_xx = 1/nu^2 * u_tt -> u_tt = nu^2 * u_xx
# Parameters: nu = 0.06, L = 0.5
# Initial conditions:
# u(x, 0) = 2h/L * x for x in [0, L/2]
# u(x, 0) = 2h*(1 - x/L) for x in [L/2, L]
# u_t(x, 0) = 0
# Boundary conditions: u(0, t) = u(L, t) = 0
# h = 0.05
# N = 500 (interior points)

@dataclass(frozen=True)
class CP2SwingingRopeParameters:
    nu: float = 0.06
    length: float = 0.5
    h: float = 0.05
    interior_points: int = 500

    def __post_init__(self) -> None:
        if self.nu <= 0.0 or not math.isfinite(self.nu):
            raise ValueError("nu must be positive and finite")
        if self.length <= 0.0 or not math.isfinite(self.length):
            raise ValueError("length must be positive and finite")
        if not math.isfinite(self.h):
            raise ValueError("h must be finite")
        if self.interior_points < 1:
            raise ValueError("interior_points must be positive")


_CP2_ROPE_DEFAULT_PARAMETERS = CP2SwingingRopeParameters()


def cp2_swinging_rope_initial_state(
    parameters: CP2SwingingRopeParameters = _CP2_ROPE_DEFAULT_PARAMETERS,
) -> tuple[Vector, Vector]:
    """Return the initial displacement and velocity for Task 3."""
    spacing = parameters.length / (parameters.interior_points + 1)
    displacement = []
    for i in range(1, parameters.interior_points + 1):
        x = i * spacing
        if x <= parameters.length / 2.0:
            val = 2.0 * parameters.h / parameters.length * x
        else:
            val = 2.0 * parameters.h * (1.0 - x / parameters.length)
        displacement.append(val)
    velocity = [0.0] * parameters.interior_points
    return tuple(displacement), tuple(velocity)


def cp2_swinging_rope_problem(
    *,
    parameters: CP2SwingingRopeParameters = _CP2_ROPE_DEFAULT_PARAMETERS,
    t_bound: float = 10.0,
) -> InitialValueProblem:
    """Build the CP2 Task 3 initial-value problem using wave_1d_ivp."""
    displacement, velocity = cp2_swinging_rope_initial_state(parameters)
    # The PDE is u_tt = c^2 u_xx, where c = nu.
    return wave_1d_ivp(
        displacement,
        velocity,
        t_bound,
        wave_speed=parameters.nu,
        length=parameters.length,
    )
