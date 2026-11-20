"""ARGESIM C19R: Pollution in Groundwater Flow.

The revised C19R definition specifies the aquifer, source and facility schedule.
The grid model uses conservative fluxes. Task A also supports numerical
integration of the unbounded homogeneous aquifer response.
"""

from __future__ import annotations

import bisect
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..ivp import InitialValueProblem, IntegrationError, IntegrationResult, Rhs
from ..runtime import (
    merge_integration_results,
    merge_solver_options,
    normalise_solver_name,
    solve_ivp,
)


@dataclass(frozen=True)
class C19Parameters:
    """Parameters in the notation of the official C19R definition."""
    mass_rate: float = 2.0  # M (mg/s)
    thickness: float = 10.0  # m (m)
    porosity: float = 0.25  # ne
    pore_velocity_x: float = 1.0e-5  # ux (m/s), revised definition, Table 1
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


def _scaled_k0(x: float) -> float:
    """Approximate exp(x) K0(x) without exponentiating a large argument.

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
        return math.exp(x) * (
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
    return (1.0 / math.sqrt(x)) * (
        1.25331414
        - 0.07832358 * y
        + 0.02189568 * y**2
        - 0.01062446 * y**3
        + 0.00587872 * y**4
        - 0.00251540 * y**5
        + 0.00053208 * y**6
    )


def _downstream_exponent(x: float, y: float, r: float, alpha: float) -> float:
    # Rationalize x - r in the downstream plume where x and r nearly coincide.
    difference = -abs(y) * (abs(y) / r) / (1.0 + x / r) if x > 0.0 else x - r
    return difference / (2.0 * alpha)


def c19_analytical_steady_state(
    x: float, y: float, parameters: C19Parameters = _C19_DEFAULT_PARAMETERS
) -> float:
    """Steady-state analytical approximation (without degradation)."""
    r = math.hypot(x, y)
    if r == 0.0:
        return math.inf
    c0 = parameters.mass_rate / (
        parameters.thickness * parameters.porosity * parameters.pore_velocity_x
    )
    alpha = parameters.dispersivity
    factor = math.exp(_downstream_exponent(x, y, r, alpha))
    return c0 / (2.0 * math.pi * alpha) * factor * _scaled_k0(r / (2.0 * alpha))


def c19_analytical_transient(
    x: float, y: float, t: float, parameters: C19Parameters = _C19_DEFAULT_PARAMETERS
) -> float:
    """Transient analytical approximation for homogeneous spread."""
    if t <= 0:
        return 0.0
    r = math.hypot(x, y)
    if r == 0.0:
        return math.inf
    u = parameters.pore_velocity_x
    alpha = parameters.dispersivity
    c0 = parameters.mass_rate / (parameters.thickness * parameters.porosity * u)

    term1 = c0 / (4.0 * math.sqrt(math.pi * alpha) * math.sqrt(r))
    term2 = math.exp(_downstream_exponent(x, y, r, alpha))
    distance = u * (t / parameters.retardation)
    if distance == 0.0:
        return 0.0
    arg = -math.inf if math.isinf(distance) else (r - distance) / math.sqrt(2.0 * alpha * distance)
    term3 = math.erfc(arg)

    return term1 * term2 * term3

def c19_homogeneous_transient(
    x: float, y: float, t: float, parameters: C19Parameters = _C19_DEFAULT_PARAMETERS
) -> float:
    """Numerically integrate the homogeneous infinite-plane point-source response."""
    if t <= 0:
        return 0.0
    r = math.hypot(x, y)
    if r == 0:
        return math.inf
    alpha = parameters.dispersivity
    distance = parameters.pore_velocity_x * (t / parameters.retardation)
    if distance == 0.0:
        return 0.0
    # Logarithmic travel distance q = log(u*time/(R*r)) removes the singular
    # 1/time factor in the 2D heat kernel. Its peak is always at q=0.
    shape = r / alpha
    cutoff = 2 * math.asinh(28 / math.sqrt(shape))
    upper = min(math.log(distance) - math.log(r), cutoff)
    if upper <= -cutoff:
        return 0.0
    # Composite eight-point Gauss-Legendre quadrature. In the far field the
    # peak narrows as 1/sqrt(shape). Bound the panel width on that scale.
    panels = math.ceil((upper + cutoff) * max(1.0, math.sqrt(shape)))
    width = (upper + cutoff) / panels
    nodes = ((0.1834346424956498, 0.3626837833783620),
             (0.5255324099163290, 0.3137066458778873),
             (0.7966664774136267, 0.2223810344533745),
             (0.9602898564975363, 0.1012285362903763))
    total = 0.0
    for i in range(panels):
        middle = -cutoff + (i + 0.5) * width
        for node, weight in nodes:
            delta = node * width / 2
            for q in (middle - delta, middle + delta):
                total += weight * math.exp(-shape * math.sinh(q / 2)**2)
    scale = parameters.mass_rate / (
        4 * math.pi * alpha * parameters.thickness * parameters.porosity * parameters.pore_velocity_x
    )
    return scale * math.exp(_downstream_exponent(x, y, r, alpha)) * total * width / 2


def _disk_cell_area(x: float, y: float, dx: float, dy: float, radius: float) -> float:
    """Area of an origin-centred disk in a cell centred at (x, y)."""
    near_x = max(0.0, abs(x) - dx / 2)
    near_y = max(0.0, abs(y) - dy / 2)
    if math.hypot(near_x, near_y) >= radius:
        return 0.0
    if math.hypot(abs(x) + dx / 2, abs(y) + dy / 2) <= radius:
        return dx * dy

    def integral(u: float) -> float:
        return (u * math.sqrt(max(0.0, radius**2 - u**2)) + radius**2 * math.asin(u / radius)) / 2

    def quadrant(a: float, b: float) -> float:
        width, height = min(abs(a), radius), min(abs(b), radius)
        flat = min(width, math.sqrt(max(0.0, radius**2 - height**2)))
        return math.copysign(height * flat + integral(width) - integral(flat), a * b)

    left, right = x - dx / 2, x + dx / 2
    bottom, top = y - dy / 2, y + dy / 2
    return max(0.0, quadrant(right, top) - quadrant(left, top)
               - quadrant(right, bottom) + quadrant(left, bottom))


def _facility_schedule(t: float) -> tuple[bool, float]:
    """Return activity and the next actual switch, starting Monday at midnight."""
    hour = 3600
    day = 24 * hour
    day_index, seconds = divmod(t, day)
    weekday = int(day_index) % 7
    midnight = day_index * day
    if weekday < 5:
        if seconds < 8 * hour:
            return True, midnight + 8 * hour
        if seconds < 20 * hour:
            return False, midnight + 20 * hour
    days_to_opening = 1 if weekday < 4 else 7 - weekday
    return True, midnight + days_to_opening * day + 8 * hour


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

    # Cell-average transport coefficient, with positive x velocity.
    conv_x = (ux / R) / dx

    deg_val = parameters.degradation

    # A cell containing the source receives M/(volume * porosity * R).
    vol = dx * dy * parameters.thickness * parameters.porosity
    source_rate = parameters.mass_rate / (vol * R)

    # The two 5 m disks are tangent, so their cell areas add without overlap.
    facility_rates = []
    if facility_mode != "none":
        for j in range(ny):
            y = y_offset + j * dy
            for i in range(nx):
                x = x_offset + i * dx - 40.0
                area = _disk_cell_area(x, y - 5.0, dx, dy, 5.0) + _disk_cell_area(x, y + 5.0, dx, dy, 5.0)
                if area > 0.0:
                    facility_rates.append((j * nx + i, deg_val * min(1.0, area / (dx * dy))))

    # Half-open cells place a point on an interior face in the upper cell.
    ix0 = math.floor(-x_offset / dx + 0.5)
    iy0 = math.floor(-y_offset / dy + 0.5)
    source_idx = iy0 * nx + ix0 if 0 <= ix0 < nx and 0 <= iy0 < ny else None

    def rhs(t: float, c: Sequence[float]) -> tuple[float, ...]:
        dc = [0.0] * (nx * ny)
        is_active = facility_mode == "continuous" or (
            facility_mode == "schedule" and _facility_schedule(t)[0]
        )

        for j in range(ny):
            west_face = c[j * nx]
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

                # Conservative upwind face reconstruction with the monotonized
                # central limiter. Reuse the east face at the next cell.
                left_jump = c_ij - c_left
                right_jump = c_right - c_ij
                if left_jump > 0.0 and right_jump > 0.0:
                    slope = min(2 * left_jump, 2 * right_jump, (left_jump + right_jump) / 2)
                elif left_jump < 0.0 and right_jump < 0.0:
                    slope = max(2 * left_jump, 2 * right_jump, (left_jump + right_jump) / 2)
                else:
                    slope = 0.0
                east_face = c_ij + slope / 2
                conv = -conv_x * (east_face - west_face)
                west_face = east_face

                # Central difference diffusion: alpha * |u| * d2C/dx2
                diff = diff_x * (c_left - 2.0 * c_ij + c_right) + diff_y * (c_down - 2.0 * c_ij + c_up)

                dc[idx] = conv + diff

        # Degradation application
        if is_active:
            for idx, rate in facility_rates:
                dc[idx] -= rate * c[idx]

        # Source application
        if source_idx is not None:
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
    defaults = {"rk45": {"max_step": max_step_value}}
    method = normalise_solver_name(method)
    if facility_mode != "schedule" or method not in {"rk45", "rk4", "euler"}:
        return solve_ivp(problem, method, options=options, defaults=defaults)

    # Freeze the forcing on each side so even RK stages at a switch use the
    # correct one-sided derivative. Reuse the two spatial operators all week.
    modes = {
        active: c19_rhs(parameters, nx, ny, dx, dy, x_offset, y_offset, mode)
        for active, mode in ((False, "none"), (True, "continuous"))
    }
    segment_options = merge_solver_options(options)
    start, state = problem.t0, problem.y0
    segments = []
    while start < problem.t_bound:
        active, next_switch = _facility_schedule(start)
        end = min(next_switch, problem.t_bound)
        part = InitialValueProblem(modes[active], start, state, end, name=problem.name, autonomous=True)
        result = solve_ivp(part, method, options=segment_options, defaults=defaults)
        segments.append(result)
        if end < problem.t_bound and "max_steps" in segment_options:
            segment_options["max_steps"] -= result.stats.accepted_steps + result.stats.rejected_steps
            if segment_options["max_steps"] <= 0:
                raise IntegrationError("C19 schedule reached max_steps")
        start, state = end, result.final_state
    return merge_integration_results(segments)


def c19_task_a(
    nx: int = 71, ny: int = 41, dx: float = 1.0, dy: float = 1.0,
    x_offset: float = -10.0, y_offset: float = -20.0, *, profiles: bool = False,
) -> IntegrationResult | list[dict[str, float]]:
    """Return the grid trajectory or the Task A transverse profiles at x=50 m."""
    if not isinstance(profiles, bool):
        raise TypeError("profiles must be bool")
    if profiles and not x_offset <= 50.0 <= x_offset + (nx - 1) * dx:
        raise ValueError("Task A profiles require a grid containing x=50 m")
    result = solve_c19(nx=nx, ny=ny, dx=dx, dy=dy, x_offset=x_offset, y_offset=y_offset)
    if not profiles:
        return result

    position = (50.0 - x_offset) / dx
    left = min(math.floor(position), nx - 2)
    frac = position - left
    rows = []
    for day in (50, 100, 150):
        time = day * 86400
        end = bisect.bisect_left(result.times, time)
        start = end - 1
        w = (time - result.times[start]) / (result.times[end] - result.times[start])
        for j in range(ny):
            y = y_offset + j * dy
            i = j * nx + left
            before, after = result.states[start], result.states[end]
            a = before[i] + frac * (before[i + 1] - before[i])
            b = after[i] + frac * (after[i + 1] - after[i])
            value = a + w * (b - a)
            printed = c19_analytical_transient(50, y, time)
            rows.append({"day": day, "y_m": y, "mol": value, "printed_approximation": printed,
                         "mol_minus_printed": value - printed,
                         "infinite_plane": c19_homogeneous_transient(50, y, time)})
    return rows


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
