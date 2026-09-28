"""ARGESIM C19R: Pollution in Groundwater Flow.

The equations, parameters, initial values and tasks follow the one-page
official C19(R) definition. This is a 2D Method of Lines PDE approximation.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..runtime import solve_ivp


@dataclass(frozen=True)
class C19Parameters:
    """Parameters in the notation of the official C19R definition."""
    mass_rate: float = 2.0  # M (mg/s)
    thickness: float = 10.0  # m (m)
    porosity: float = 0.25  # ne
    pore_velocity_x: float = 1.7 / (24 * 3600)  # ux (m/s)
    dispersivity: float = 0.05  # alpha_T = alpha_L (m)
    retardation: float = 1.0  # R
    degradation: float = 1.0e-6 * math.log(10.0)  # lambda (1/s)

    def __post_init__(self) -> None:
        positive = (
            self.mass_rate,
            self.thickness,
            self.porosity,
            self.pore_velocity_x,
            self.dispersivity,
            self.retardation,
        )
        if any(not math.isfinite(value) or value <= 0.0 for value in positive):
            raise ValueError("C19 transport parameters must be positive and finite")
        if not math.isfinite(self.degradation) or self.degradation < 0.0:
            raise ValueError("degradation must be non-negative and finite")


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
        return math.inf
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
    if t <= 0:
        return 0.0
    r = math.sqrt(x * x + y * y)
    if r == 0.0:
        return math.inf
    u = parameters.pore_velocity_x
    alpha = parameters.dispersivity
    c0 = parameters.mass_rate / (parameters.thickness * parameters.porosity * u)

    term1 = c0 / (4.0 * math.sqrt(math.pi * alpha) * math.sqrt(r))
    term2 = math.exp((x - r) / (2.0 * alpha))
    arg = (r - u * t) / math.sqrt(2.0 * alpha * u * t)
    term3 = math.erfc(arg)

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
    if not isinstance(nx, int) or isinstance(nx, bool) or nx < 2:
        raise ValueError("nx must be an integer of at least two")
    if not isinstance(ny, int) or isinstance(ny, bool) or ny < 2:
        raise ValueError("ny must be an integer of at least two")
    if any(not math.isfinite(value) or value <= 0.0 for value in (dx, dy)):
        raise ValueError("dx and dy must be positive and finite")
    if any(not math.isfinite(value) for value in (x_offset, y_offset)):
        raise ValueError("grid offsets must be finite")
    if facility_mode not in {"none", "continuous", "schedule"}:
        raise ValueError("facility_mode must be 'none', 'continuous', or 'schedule'")
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

    deg_val = parameters.degradation

    source_term = [0.0] * (nx * ny)
    # The source is a point source M at (0,0). In a discrete grid, it corresponds to the cell
    # containing (0,0). The transport equation is integrated over the cell volume:
    # the concentration rate is M / (dx * dy * thickness * ne).
    # However, since we are doing 2D Method of Lines, the PDE is typically formulated
    # in terms of concentration per unit length, or we need to ensure the delta function
    # is scaled properly. The analytical solution uses c0 = M / (m * ne * u).
    # Note: the entire time derivative is scaled by retardation R, so the source term
    # must be divided by R as well. (m maps to thickness in parameters)
    vol = dx * dy * parameters.thickness * parameters.porosity
    source_rate = parameters.mass_rate / (vol * R)

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

    is_continuous = (facility_mode == "continuous")
    is_schedule = (facility_mode == "schedule")

    def rhs(t: float, c: Sequence[float]) -> tuple[float, ...]:
        dc = [0.0] * (nx * ny)

        is_active = False
        if is_continuous:
            is_active = True
        elif is_schedule:
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


def solve_c19(
    method: str = "rk45",
    *,
    nx: int = 71,
    ny: int = 41,
    dx: float = 1.0,
    dy: float = 1.0,
    x_offset: float = -10.0,
    y_offset: float = -20.0,
    facility_mode: str = "none",
    parameters: C19Parameters = _C19_DEFAULT_PARAMETERS,
    t_bound: float = 150 * 24 * 3600,
    initial_state: Sequence[float] | None = None,
    max_step: float = 12 * 3600,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Solve one C19R MOL problem through the shared backend dispatcher.

    RK45 has a benchmark-scale default step cap. Fixed-step and quantized
    methods deliberately require an explicit ``step`` or ``quantum`` option,
    because their useful values depend on the grid and concentration scale.
    QSS backends also correctly reject the schedule-driven non-autonomous task.
    """

    if isinstance(max_step, bool):
        raise TypeError("max_step must be a real number")
    max_step_value = float(max_step)
    if not math.isfinite(max_step_value) or max_step_value <= 0.0:
        raise ValueError("max_step must be positive and finite")
    problem = c19_problem(
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        x_offset=x_offset,
        y_offset=y_offset,
        facility_mode=facility_mode,
        parameters=parameters,
        t_bound=t_bound,
        initial_state=initial_state,
    )
    return solve_ivp(
        problem,
        method,
        options=options,
        defaults={"rk45": {"max_step": max_step_value}},
    )

def c19_task_a(nx: int = 71, ny: int = 41, dx: float = 1.0, dy: float = 1.0, x_offset: float = -10.0, y_offset: float = -20.0) -> IntegrationResult:
    """Task A: Simulation of unregulated pollution spread for 150 days."""
    # Using explicit RK45. The spatial discretization of diffusion makes the system stiff.
    # For a realistic grid (dx=1), the stability limit forces very small steps.
    # An implicit solver would be more appropriate, but explicit is used here out of necessity
    # to maintain benchmark framework compatibility.
    return solve_c19(
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        x_offset=x_offset,
        y_offset=y_offset,
        facility_mode="none",
        max_step=12 * 3600,
    )


def _steady_state_grid(
    nx: int,
    ny: int,
    dx: float,
    dy: float,
    x_offset: float,
    y_offset: float,
) -> list[float]:
    """Sample the analytical field with a finite source-cell regularization."""

    state = []
    source_radius = 0.5 * min(dx, dy)
    for j in range(ny):
        y = y_offset + j * dy
        for i in range(nx):
            x = x_offset + i * dx
            if x == 0.0 and y == 0.0:
                state.append(c19_analytical_steady_state(source_radius, 0.0))
            else:
                state.append(c19_analytical_steady_state(x, y))
    return state

def c19_task_b(nx: int = 71, ny: int = 41, dx: float = 1.0, dy: float = 1.0, x_offset: float = -10.0, y_offset: float = -20.0) -> IntegrationResult:
    """Task B: Pollution reduction with continuous facility operation.

    Starts from the steady-state approximation.
    """
    state = _steady_state_grid(nx, ny, dx, dy, x_offset, y_offset)

    return solve_c19(
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        x_offset=x_offset,
        y_offset=y_offset,
        facility_mode="continuous",
        initial_state=state,
        # Task C compares the continuous result with scheduled operation
        # through day 150; keep Task B on the same observation horizon.
        t_bound=150 * 24 * 3600,
        max_step=12 * 3600,
    )

def c19_task_c(nx: int = 71, ny: int = 41, dx: float = 1.0, dy: float = 1.0, x_offset: float = -10.0, y_offset: float = -20.0) -> IntegrationResult:
    """Task C: Schedule-controlled pollution reduction.

    Starts from the steady-state approximation.
    """
    state = _steady_state_grid(nx, ny, dx, dy, x_offset, y_offset)

    return solve_c19(
        nx=nx,
        ny=ny,
        dx=dx,
        dy=dy,
        x_offset=x_offset,
        y_offset=y_offset,
        facility_mode="schedule",
        initial_state=state,
        t_bound=150 * 24 * 3600,
        max_step=6 * 3600,
    )
