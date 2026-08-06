"""ARGESIM C19R: Pollution in Groundwater Flow.

The equations, parameters, initial values and tasks follow the one-page
official C19(R) definition. This is a 2D Method of Lines PDE approximation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..solvers import euler, rk4, rk45


@dataclass(frozen=True)
class C19Parameters:
    """Parameters in the notation of the official C19R definition."""
    mass_rate: float = 2.0  # M (mg/s)
    thickness: float = 10.0  # m (m)
    porosity: float = 0.25  # ne
    pore_velocity_x: float = 1.7 / (24 * 3600)  # ux (m/s)
    dispersivity: float = 0.05  # alpha_T = alpha_L (m)
    retardation: float = 1.0  # R
    degradation: float = 0.0  # lambda (1/s)


_C19_DEFAULT_PARAMETERS = C19Parameters()


def _k0_approx(x: float) -> float:
    """Analytical approximation for modified Bessel function K0.

    Uses polynomial approximations from Abramowitz & Stegun.
    """
    if x <= 2.0:
        y = x * x / 4.0
        # I0(x) approx
        t = x / 3.75
        t2 = t * t
        i0 = (
            1.0
            + 3.5156229 * t2
            + 3.0899424 * t2**2
            + 1.2067492 * t2**3
            + 0.2659732 * t2**4
            + 0.0360768 * t2**5
            + 0.0045813 * t2**6
        )
        return (
            -math.log(x / 2.0) * i0
            - 0.57721566
            + 0.42278420 * y
            + 0.23069756 * y**2
            + 0.03488590 * y**3
            + 0.00262698 * y**4
            + 0.00010750 * y**5
            + 0.00000740 * y**6
        )
    y = 2.0 / x
    return (math.exp(-x) / math.sqrt(x)) * (
        1.25331414
        - 0.07832358 * y
        + 0.02189568 * y**2
        - 0.01062446 * y**3
        + 0.00587872 * y**4
        - 0.00251540 * y**5
        + 0.00053208 * y**6
    )


def c19_analytical_steady_state(
    x: float, y: float, parameters: C19Parameters = _C19_DEFAULT_PARAMETERS
) -> float:
    """Steady-state analytical approximation (without degradation)."""
    r = math.sqrt(x * x + y * y)
    if r == 0.0:
        return 0.0
    c0 = parameters.mass_rate / (
        parameters.thickness * parameters.porosity * parameters.pore_velocity_x
    )
    alpha = parameters.dispersivity
    term1 = (c0 / (2.0 * math.pi * alpha)) * math.exp(x / (2.0 * alpha))
    term2 = _k0_approx(r / (2.0 * alpha))
    return term1 * term2


def c19_analytical_transient(
    x: float, y: float, t: float, parameters: C19Parameters = _C19_DEFAULT_PARAMETERS
) -> float:
    """Transient analytical approximation for homogeneous spread."""
    r = math.sqrt(x * x + y * y)
    if r == 0.0:
        return 0.0
    u = parameters.pore_velocity_x
    alpha = parameters.dispersivity
    c0 = parameters.mass_rate / (parameters.thickness * parameters.porosity * u)

    term1 = c0 / (4.0 * math.sqrt(math.pi * alpha) * math.sqrt(r))
    term2 = math.exp((x - r) / (2.0 * alpha))
    if t <= 0:
        return 0.0
    arg = (r - u * t) / math.sqrt(2.0 * alpha * u * t)
    # erfc(x) = 1 - erf(x)
    term3 = 1.0 - math.erf(arg)

    return term1 * term2 * term3

def c19_rhs(
    parameters: C19Parameters,
    nx: int,
    ny: int,
    dx: float,
    dy: float,
    x_offset: float = -10.0,
    y_offset: float = -20.0,
    facility_mode: str = "none"
) -> Rhs:
    """Return the right-hand side function for the 2D Method of Lines."""
    # facility_mode can be "none", "continuous", or "schedule"
    ux = parameters.pore_velocity_x
    R = parameters.retardation
    alpha_L = parameters.dispersivity
    alpha_T = parameters.dispersivity

    # Diffusion coefficients
    dx2 = dx * dx
    dy2 = dy * dy
    diff_x = (alpha_L * ux / R) / dx2
    diff_y = (alpha_T * ux / R) / dy2

    # Upwind convection coefficient (assuming ux > 0, uy = 0)
    conv_x = (ux / R) / dx

    deg_val = 1e-6 * math.log(10.0)  # lambda = 10^-6 * ln(10)

    source_term = [0.0] * (nx * ny)
    # The source is a point source M at (0,0). In a discrete grid, it corresponds to the cell
    # containing (0,0). The transport equation is integrated over the cell volume:
    # the concentration rate is M / (dx * dy * m * ne).
    # However, since we are doing 2D Method of Lines, the PDE is typically formulated
    # in terms of concentration per unit length, or we need to ensure the delta function
    # is scaled properly. The analytical solution uses c0 = M / (m * ne * u).
    vol = dx * dy * parameters.thickness * parameters.porosity
    source_rate = parameters.mass_rate / vol

    # Precalculate facility indices for efficiency (avoid distance checks in inner loop)
    facility_indices: list[int] = []
    if facility_mode in ("continuous", "schedule"):
        for j in range(ny):
            y_pos = y_offset + j * dy
            for i in range(nx):
                x_pos = x_offset + i * dx
                r1 = math.sqrt((x_pos - 40.0)**2 + (y_pos - 5.0)**2)
                r2 = math.sqrt((x_pos - 40.0)**2 + (y_pos + 5.0)**2)
                if r1 <= 5.0 or r2 <= 5.0:
                    facility_indices.append(j * nx + i)

    # Find the closest cell to (0,0)
    ix0 = max(0, min(nx - 1, int(round((0.0 - x_offset) / dx))))
    iy0 = max(0, min(ny - 1, int(round((0.0 - y_offset) / dy))))

    source_idx = iy0 * nx + ix0

    def rhs(t: float, c: Sequence[float]) -> tuple[float, ...]:
        dc = [0.0] * (nx * ny)

        is_active = False
        if facility_mode == "continuous":
            is_active = True
        elif facility_mode == "schedule":
            # Monday to Friday 0-8am, 8pm-12pm
            # Weekends around the clock
            # Assuming t=0 is Monday 00:00. Time is in seconds.
            day_of_week = int(t / (24 * 3600)) % 7  # 0=Monday, 6=Sunday
            hour_of_day = (t % (24 * 3600)) / 3600.0

            if day_of_week >= 5: # Saturday, Sunday
                is_active = True
            elif hour_of_day < 8.0 or hour_of_day >= 20.0:
                is_active = True

        for j in range(ny):
            for i in range(nx):
                idx = j * nx + i
                c_ij = c[idx]

                # Boundary conditions:
                # Left (upstream): x = -10. Zero gradient.
                # Right (downstream): convection driven, zero gradient.
                # Top/Bottom: diffusion driven, zero gradient.
                # Note: Zero gradient implies no flux for diffusion, and outward flux for convection.
                c_left = c[idx - 1] if i > 0 else c_ij
                c_right = c[idx + 1] if i < nx - 1 else c_ij
                c_down = c[idx - nx] if j > 0 else c_ij
                c_up = c[idx + nx] if j < ny - 1 else c_ij

                # Upwind convection: - ux * dC/dx
                # (c_ij - c_left)/dx
                conv = -conv_x * (c_ij - c_left)

                # Central difference diffusion: alpha * |u| * d2C/dx2
                diff = diff_x * (c_left - 2.0 * c_ij + c_right) + diff_y * (c_down - 2.0 * c_ij + c_up)

                dc[idx] = conv + diff

        # Degradation application
        if is_active:
            for idx in facility_indices:
                dc[idx] -= deg_val * c[idx]

        # Source application
        dc[source_idx] += source_rate

        return tuple(dc)

    return rhs

def c19_problem(
    nx: int = 71,
    ny: int = 41,
    dx: float = 1.0,
    dy: float = 1.0,
    x_offset: float = -10.0,
    y_offset: float = -20.0,
    facility_mode: str = "none",
    parameters: C19Parameters = _C19_DEFAULT_PARAMETERS,
    t_bound: float = 150 * 24 * 3600,  # 150 days in seconds
    initial_state: Sequence[float] | None = None
) -> InitialValueProblem:
    if initial_state is None:
        # Default to steady-state approximation if not specified,
        # but the first task starts from zero (or maybe steady state?
        # The first task is "Simulation of Pollution Spread" with observation period 150 days.
        # We start from zero concentration.)
        initial_state = [0.0] * (nx * ny)

    return InitialValueProblem(
        c19_rhs(parameters, nx, ny, dx, dy, x_offset, y_offset, facility_mode),
        0.0,
        initial_state,
        t_bound,
        name="ARGESIM-C19-groundwater",
        autonomous=(facility_mode != "schedule")
    )

def c19_task_a(nx: int = 71, ny: int = 41, dx: float = 1.0, dy: float = 1.0, x_offset: float = -10.0, y_offset: float = -20.0) -> IntegrationResult:
    """Task A: Simulation of unregulated pollution spread for 150 days."""
    problem = c19_problem(nx=nx, ny=ny, dx=dx, dy=dy, x_offset=x_offset, y_offset=y_offset, facility_mode="none")
    # Using explicit Euler or RK45. Because of diffusion, max step is limited.
    # For a realistic grid (dx=1), dt should be around 0.5 days. Let's use adaptive.
    # But since it's just a reference, we can use a small step or coarse grid for tests.
    return rk45(problem, max_step=12*3600)  # max step 12 hours

def c19_task_b(nx: int = 71, ny: int = 41, dx: float = 1.0, dy: float = 1.0, x_offset: float = -10.0, y_offset: float = -20.0) -> IntegrationResult:
    """Task B: Pollution reduction with continuous facility operation.

    Starts from the steady-state approximation.
    """
    # Initialize from analytical steady state
    state = []
    for j in range(ny):
        y = y_offset + j * dy
        for i in range(nx):
            x = x_offset + i * dx
            state.append(c19_analytical_steady_state(x, y))

    problem = c19_problem(
        nx=nx, ny=ny, dx=dx, dy=dy, x_offset=x_offset, y_offset=y_offset, facility_mode="continuous", initial_state=state, t_bound=100*24*3600
    )
    return rk45(problem, max_step=12*3600)

def c19_task_c(nx: int = 71, ny: int = 41, dx: float = 1.0, dy: float = 1.0, x_offset: float = -10.0, y_offset: float = -20.0) -> IntegrationResult:
    """Task C: Schedule-controlled pollution reduction.

    Starts from the steady-state approximation.
    """
    # Initialize from analytical steady state
    state = []
    for j in range(ny):
        y = y_offset + j * dy
        for i in range(nx):
            x = x_offset + i * dx
            state.append(c19_analytical_steady_state(x, y))

    problem = c19_problem(
        nx=nx, ny=ny, dx=dx, dy=dy, x_offset=x_offset, y_offset=y_offset, facility_mode="schedule", initial_state=state, t_bound=150*24*3600
    )
    return rk45(problem, max_step=6*3600)
