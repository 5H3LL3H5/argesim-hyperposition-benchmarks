"""ARGESIM CP2: Parallel and Distributed Simulation.

Task 1: Monte Carlo Study (Spring-Mass System)
Task 2: Lattice Boltzmann Simulation (Cavity Flow, D2Q9)
Task 3: Partial Differential Equation Case Study (Swinging Rope)
"""

from __future__ import annotations

import math
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass
from enum import Enum

from ..ivp import InitialValueProblem, Rhs, Vector
from ..parallel import OrderedExecutor, ParallelRun, benchmark_ordered_map
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


class CP2LBMCell(str, Enum):
    """Cell labels from the CP2 cavity geometry matrix."""

    DRIVING = "D"
    WALL = "W"
    FLUID = "F"


def cp2_lbm_geometry(nx: int = 257) -> tuple[tuple[CP2LBMCell, ...], ...]:
    """Return the published ``D/W/F`` cavity geometry.

    The complete top row is a driving boundary, the bottom and side rows are
    stationary walls, and all remaining cells are fluid cells.
    """

    if not isinstance(nx, int) or isinstance(nx, bool):
        raise TypeError("grid size nx must be an integer")
    if nx < 3:
        raise ValueError("grid size nx must be at least 3")
    return tuple(
        tuple(
            CP2LBMCell.DRIVING
            if y == nx - 1
            else CP2LBMCell.WALL
            if y == 0 or x == 0 or x == nx - 1
            else CP2LBMCell.FLUID
            for x in range(nx)
        )
        for y in range(nx)
    )


def cp2_lbm_initial_state(
    nx: int = 257,
) -> tuple[tuple[tuple[float, ...], ...], ...]:
    """Create the initial D2Q9 grid for Task 2."""
    if not isinstance(nx, int) or isinstance(nx, bool):
        raise TypeError("grid size nx must be an integer")
    if nx < 3:
        raise ValueError("grid size nx must be at least 3")

    # Initial macroscopic variables: rho = 1, u = (0, 0)
    # The equilibrium distribution for u=0 is just w_i * rho = w_i
    grid = []
    for _ in range(nx):
        row = []
        for _ in range(nx):
            row.append(CP2_LBM_WEIGHTS)
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
    grid: tuple[tuple[tuple[float, ...], ...], ...],
    nx: int,
    omega: float,
    u0_x: float = 0.1,
) -> tuple[tuple[tuple[float, ...], ...], ...]:
    """Perform one reference D2Q9 BGK collision/propagation step.

    This follows the published CEA-Wismar scalar implementation: fluid cells
    use BGK collision, stationary wall cells use full-way bounce-back, and the
    complete driving row is replaced by its equilibrium distribution at
    ``(u0_x, 0)``.  Directional propagation retains the current population at
    a global edge when no upstream lattice point exists.
    """

    if not isinstance(nx, int) or isinstance(nx, bool):
        raise TypeError("nx must be an integer")
    if nx < 3:
        raise ValueError("nx must be at least 3")
    if isinstance(omega, bool) or not math.isfinite(float(omega)):
        raise ValueError("omega must be finite")
    if not 0.0 < float(omega) < 2.0:
        raise ValueError("omega must lie in the BGK stability interval (0, 2)")
    if isinstance(u0_x, bool) or not math.isfinite(float(u0_x)):
        raise ValueError("u0_x must be finite")
    if abs(float(u0_x)) >= 1.0:
        raise ValueError("u0_x magnitude must be below the lattice speed")
    if len(grid) != nx or any(len(row) != nx for row in grid):
        raise ValueError("grid shape must be nx by nx")
    if any(len(cell) != 9 for row in grid for cell in row):
        raise ValueError("each D2Q9 cell must contain nine populations")
    if any(
        not math.isfinite(float(value))
        for row in grid
        for cell in row
        for value in cell
    ):
        raise ValueError("LBM populations must be finite")

    collided = _cp2_lbm_collision_chunk((0, nx, grid, nx, omega, u0_x))
    return _cp2_lbm_stream(collided, nx, u0_x)


def _cp2_lbm_collision_chunk(
    payload: tuple[
        int,
        int,
        tuple[tuple[tuple[float, ...], ...], ...],
        int,
        float,
        float,
    ],
) -> tuple[tuple[tuple[float, ...], ...], ...]:
    start, stop, grid, nx, omega, u0_x = payload
    result = []
    for y in range(start, stop):
        row = []
        for x in range(nx):
            populations = grid[y][x]
            rho = sum(populations)
            if rho <= 0.0:
                raise ValueError("LBM cell density must remain positive")
            ux = (
                populations[1]
                + populations[5]
                + populations[8]
                - populations[3]
                - populations[6]
                - populations[7]
            ) / rho
            uy = (
                populations[2]
                + populations[5]
                + populations[6]
                - populations[4]
                - populations[7]
                - populations[8]
            ) / rho
            if y == nx - 1:
                row.append(_compute_equilibrium(rho, u0_x, 0.0))
            elif y == 0 or x == 0 or x == nx - 1:
                row.append(tuple(populations[index] for index in CP2_LBM_REVERSE))
            else:
                equilibrium = _compute_equilibrium(rho, ux, uy)
                row.append(
                    tuple(
                        populations[index]
                        - omega * (populations[index] - equilibrium[index])
                        for index in range(9)
                    )
                )
        result.append(tuple(row))
    return tuple(result)


def _cp2_lbm_stream(
    collided: tuple[tuple[tuple[float, ...], ...], ...],
    nx: int,
    u0_x: float,
) -> tuple[tuple[tuple[float, ...], ...], ...]:
    """Propagate all nine populations exactly as the reference shifts do."""

    del u0_x  # the driving equilibrium was imposed during collision
    new_grid = [[list(cell) for cell in row] for row in collided]
    for y in range(nx):
        for x in range(nx):
            for index, (cx, cy) in enumerate(CP2_LBM_VELOCITIES):
                source_x = x - cx
                source_y = y - cy
                if 0 <= source_x < nx and 0 <= source_y < nx:
                    new_grid[y][x][index] = collided[source_y][source_x][index]
    return tuple(tuple(tuple(cell) for cell in row) for row in new_grid)


def _cp2_lbm_partition(size: int, parts: int) -> tuple[tuple[int, int], ...]:
    width, remainder = divmod(size, parts)
    ranges = []
    start = 0
    for index in range(parts):
        stop = start + width + (1 if index < remainder else 0)
        if stop > start:
            ranges.append((start, stop))
        start = stop
    return tuple(ranges)


def _cp2_lbm_step_with_pool(
    grid: tuple[tuple[tuple[float, ...], ...], ...],
    nx: int,
    omega: float,
    u0_x: float,
    pool: OrderedExecutor,
) -> tuple[tuple[tuple[float, ...], ...], ...]:
    chunks = _cp2_lbm_partition(nx, min(nx, pool.workers))
    collision_chunks = pool.map(
        _cp2_lbm_collision_chunk,
        tuple((start, stop, grid, nx, omega, u0_x) for start, stop in chunks),
    )
    collided = tuple(row for chunk in collision_chunks for row in chunk)
    return _cp2_lbm_stream(collided, nx, u0_x)


def cp2_lbm_step_parallel(
    grid: tuple[tuple[tuple[float, ...], ...], ...],
    nx: int,
    omega: float,
    *,
    u0_x: float = 0.1,
    workers: int = 2,
    backend: str = "thread",
) -> tuple[tuple[tuple[float, ...], ...], ...]:
    """One collision-partitioned LBM step with deterministic serial streaming."""

    if len(grid) != nx or any(len(row) != nx for row in grid):
        raise ValueError("grid shape must be nx by nx")
    if not 0.0 < omega < 2.0:
        raise ValueError("omega must lie in (0, 2)")
    with OrderedExecutor(workers, backend=backend) as pool:
        return _cp2_lbm_step_with_pool(grid, nx, omega, u0_x, pool)


# Task 3: Swinging Rope PDE
# u_xx = 1/nu^2 * u_tt -> u_tt = nu^2 * u_xx
# Corrected reference parameters: nu = 0.06, L = 0.5.  The 2007 definition
# printed nu = 0.6; the peer-reviewed 2022 solution and its reference code
# explicitly correct that typo.
# Initial conditions:
# u(x, 0) = 2h/L * x for x in [0, L/2]
# u(x, 0) = 2h*(1 - x/L) for x in [L/2, L]
# u_t(x, 0) = 0
# Boundary conditions: u(0, t) = u(L, t) = 0
# h = 0.05
# N = 500 spatial intervals, hence N - 1 = 499 interior unknowns

@dataclass(frozen=True)
class CP2SwingingRopeParameters:
    nu: float = 0.06
    length: float = 0.5
    h: float = 0.05
    interior_points: int = 499

    def __post_init__(self) -> None:
        if self.nu <= 0.0 or not math.isfinite(self.nu):
            raise ValueError("nu must be positive and finite")
        if self.length <= 0.0 or not math.isfinite(self.length):
            raise ValueError("length must be positive and finite")
        if not math.isfinite(self.h):
            raise ValueError("h must be finite")
        if not isinstance(self.interior_points, int) or isinstance(
            self.interior_points, bool
        ):
            raise TypeError("interior_points must be an integer")
        if self.interior_points < 1:
            raise ValueError("interior_points must be positive")


_CP2_ROPE_DEFAULT_PARAMETERS = CP2SwingingRopeParameters()
CP2_PRINTED_ROPE_PARAMETERS = CP2SwingingRopeParameters(nu=0.6)


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


# --- Complete benchmark workloads ---


@dataclass(frozen=True)
class CP2MonteCarloStudy:
    """Task-1 ensemble output and serial/parallel timing evidence."""

    dampings: tuple[float, ...]
    times: tuple[float, ...]
    mean_position: tuple[float, ...]
    execution: ParallelRun[tuple[float, ...]]


@dataclass(frozen=True)
class CP2LBMResult:
    """Task-2 cavity state, requested velocity field and mass diagnostic."""

    grid: tuple[tuple[tuple[float, ...], ...], ...]
    relative_speed: tuple[tuple[float, ...], ...]
    iterations: int
    elapsed: float
    mass_error: float
    maximum_speed: float


@dataclass(frozen=True)
class CP2RopeComparison:
    """Task-3 method-of-lines values compared with the Fourier solution."""

    times: tuple[float, ...]
    positions: tuple[float, ...]
    numerical: tuple[tuple[float, ...], ...]
    analytical: tuple[tuple[float, ...], ...]
    maximum_error: float


@dataclass(frozen=True)
class CP2ImplicitRopeResult:
    times: tuple[float, ...]
    positions: tuple[float, ...]
    displacement: tuple[tuple[float, ...], ...]
    snapshot_times: tuple[float, ...] = ()
    snapshot_positions: tuple[float, ...] = ()
    snapshots: tuple[tuple[float, ...], ...] = ()


@dataclass(frozen=True)
class CP2RopeStudy:
    """All trace, profile and surface outputs requested by CP2 Task 3."""

    trace_times: tuple[float, ...]
    trace_positions: tuple[float, ...]
    numerical_traces: tuple[tuple[float, ...], ...]
    analytical_traces: tuple[tuple[float, ...], ...]
    profile_times: tuple[float, ...]
    profile_positions: tuple[float, ...]
    numerical_profiles: tuple[tuple[float, ...], ...]
    analytical_profiles: tuple[tuple[float, ...], ...]
    surface_times: tuple[float, ...]
    surface: tuple[tuple[float, ...], ...]
    maximum_trace_error: float
    maximum_profile_error: float


@dataclass(frozen=True)
class CP2LBMExecution:
    serial_seconds: float
    parallel_seconds: float
    speedup: float
    maximum_population_error: float
    workers: int


def cp2_monte_carlo_analytical(
    time_value: float,
    parameters: CP2MonteCarloParameters = _CP2_MC_DEFAULT_PARAMETERS,
    *,
    initial_position: float = 0.0,
    initial_velocity: float = 0.1,
) -> float:
    """Exact damped-oscillator displacement used as Task-1 reference."""

    time_number = float(time_value)
    if not math.isfinite(time_number) or time_number < 0.0:
        raise ValueError("time must be non-negative and finite")
    alpha = parameters.damping / (2.0 * parameters.mass)
    omega_squared = parameters.stiffness / parameters.mass - alpha * alpha
    if omega_squared > 1.0e-15:
        omega = math.sqrt(omega_squared)
        sine_coefficient = (initial_velocity + alpha * initial_position) / omega
        return math.exp(-alpha * time_number) * (
            initial_position * math.cos(omega * time_number)
            + sine_coefficient * math.sin(omega * time_number)
        )
    if abs(omega_squared) <= 1.0e-15:
        return math.exp(-alpha * time_number) * (
            initial_position
            + (initial_velocity + alpha * initial_position) * time_number
        )
    root = math.sqrt(-omega_squared)
    first = 0.5 * (initial_position + (initial_velocity + alpha * initial_position) / root)
    second = initial_position - first
    return first * math.exp((-alpha + root) * time_number) + second * math.exp(
        (-alpha - root) * time_number
    )


def _cp2_oscillator_case(
    payload: tuple[float, tuple[float, ...]],
) -> tuple[float, ...]:
    damping, times = payload
    parameters = CP2MonteCarloParameters(damping=damping)
    return tuple(cp2_monte_carlo_analytical(time_value, parameters) for time_value in times)


def _cp2_time_case(payload: tuple[float, tuple[float, ...]]) -> float:
    time_value, dampings = payload
    return sum(
        cp2_monte_carlo_analytical(
            time_value, CP2MonteCarloParameters(damping=damping)
        )
        for damping in dampings
    ) / len(dampings)


def cp2_task1_monte_carlo(
    *,
    samples: int = 1000,
    seed: int = 1729,
    output_step: float = 0.01,
    t_bound: float = 2.0,
    workers: int = 2,
    backend: str = "thread",
    warmups: int = 0,
    repeats: int = 1,
) -> CP2MonteCarloStudy:
    """Run official CP2 Task 1 at 201 output times."""

    if not isinstance(samples, int) or isinstance(samples, bool) or samples <= 0:
        raise ValueError("samples must be a positive integer")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    if output_step <= 0.0 or t_bound <= 0.0:
        raise ValueError("output_step and t_bound must be positive")
    intervals = round(t_bound / output_step)
    if not math.isclose(intervals * output_step, t_bound, abs_tol=1.0e-14):
        raise ValueError("t_bound must be an integer multiple of output_step")
    times = tuple(index * output_step for index in range(intervals + 1))
    rng = random.Random(seed)
    dampings = tuple(rng.uniform(800.0, 1200.0) for _ in range(samples))
    payloads = tuple((damping, times) for damping in dampings)
    execution = benchmark_ordered_map(
        _cp2_oscillator_case,
        payloads,
        workers=workers,
        backend=backend,
        warmups=warmups,
        repeats=repeats,
        tolerance=0.0,
    )
    mean_position = tuple(
        sum(trajectory[index] for trajectory in execution.parallel_values) / samples
        for index in range(len(times))
    )
    return CP2MonteCarloStudy(dampings, times, mean_position, execution)


def cp2_task1_time_parallel(
    *,
    samples: int = 1000,
    seed: int = 1729,
    output_step: float = 0.01,
    t_bound: float = 2.0,
    workers: int = 2,
    backend: str = "thread",
    repeats: int = 1,
) -> tuple[tuple[float, ...], ParallelRun[float]]:
    """Alternative official strategy: distribute the 201 output instants."""

    if samples <= 0:
        raise ValueError("samples must be positive")
    intervals = round(t_bound / output_step)
    if not math.isclose(intervals * output_step, t_bound, abs_tol=1.0e-14):
        raise ValueError("t_bound must be an integer multiple of output_step")
    times = tuple(index * output_step for index in range(intervals + 1))
    rng = random.Random(seed)
    dampings = tuple(rng.uniform(800.0, 1200.0) for _ in range(samples))
    execution = benchmark_ordered_map(
        _cp2_time_case,
        tuple((time_value, dampings) for time_value in times),
        workers=workers,
        backend=backend,
        warmups=0,
        repeats=repeats,
        tolerance=0.0,
    )
    return times, execution


def cp2_lbm_relaxation(nx: int = 257, *, u0_x: float = 0.1, reynolds: float = 1000.0) -> float:
    """Return the BGK relaxation rate from the official Reynolds number."""

    if nx < 3 or u0_x <= 0.0 or reynolds <= 0.0:
        raise ValueError("nx >= 3, u0_x > 0, and reynolds > 0 are required")
    viscosity = (nx - 1) * u0_x / reynolds
    return 1.0 / (3.0 * viscosity + 0.5)


def cp2_lbm_velocity_magnitude(
    grid: tuple[tuple[tuple[float, ...], ...], ...],
    *,
    reference_speed: float = 1.0,
    driving_speed: float | None = None,
) -> tuple[tuple[float, ...], ...]:
    """Recover relative velocity magnitude ``|u| / reference_speed``.

    When ``driving_speed`` is supplied, the complete top row is reported at
    that prescribed velocity.  This mirrors the official MATLAB output,
    which imposes the lid's macroscopic velocity before producing the field.
    """

    if not math.isfinite(reference_speed) or reference_speed <= 0.0:
        raise ValueError("reference_speed must be positive and finite")
    if driving_speed is not None and (
        not math.isfinite(driving_speed) or abs(driving_speed) >= 1.0
    ):
        raise ValueError("driving_speed must be finite and below lattice speed")

    values: list[tuple[float, ...]] = []
    for row_index, row in enumerate(grid):
        magnitudes = []
        for populations in row:
            rho = sum(populations)
            if rho <= 0.0:
                magnitudes.append(0.0)
                continue
            ux = (
                populations[1]
                + populations[5]
                + populations[8]
                - populations[3]
                - populations[6]
                - populations[7]
            ) / rho
            uy = (
                populations[2]
                + populations[5]
                + populations[6]
                - populations[4]
                - populations[7]
                - populations[8]
            ) / rho
            if driving_speed is not None and row_index == len(grid) - 1:
                ux, uy = driving_speed, 0.0
            magnitudes.append(math.hypot(ux, uy) / reference_speed)
        values.append(tuple(magnitudes))
    return tuple(values)


def cp2_task2_lid_driven_cavity(
    *,
    nx: int = 257,
    iterations: int = 350_000,
    u0_x: float = 0.1,
    reynolds: float = 1000.0,
    workers: int = 1,
    backend: str = "thread",
) -> CP2LBMResult:
    """Run official CP2 Task 2 with D2Q9 BGK and wall bounce-back.

    Defaults encode the published workload; reduced values are useful for CI
    and correctness studies. The returned timing covers only time stepping.
    """

    if not isinstance(iterations, int) or isinstance(iterations, bool) or iterations < 0:
        raise ValueError("iterations must be a non-negative integer")
    grid = cp2_lbm_initial_state(nx)
    initial_mass = float(nx * nx)
    omega = cp2_lbm_relaxation(nx, u0_x=u0_x, reynolds=reynolds)
    started = time.perf_counter()
    with OrderedExecutor(workers, backend=backend) as pool:
        for _ in range(iterations):
            grid = _cp2_lbm_step_with_pool(grid, nx, omega, u0_x, pool)
    elapsed = time.perf_counter() - started
    final_mass = sum(value for row in grid for cell in row for value in cell)
    magnitudes = cp2_lbm_velocity_magnitude(
        grid,
        reference_speed=u0_x,
        driving_speed=u0_x,
    )
    return CP2LBMResult(
        grid,
        magnitudes,
        iterations,
        elapsed,
        final_mass - initial_mass,
        max((max(row) for row in magnitudes), default=0.0),
    )


def cp2_task2_compare_execution(
    *,
    nx: int = 33,
    iterations: int = 100,
    workers: int = 2,
    backend: str = "thread",
) -> CP2LBMExecution:
    """Measure equivalent serial/parallel LBM workloads and verify populations."""

    serial = cp2_task2_lid_driven_cavity(
        nx=nx, iterations=iterations, workers=1, backend="serial"
    )
    parallel = cp2_task2_lid_driven_cavity(
        nx=nx, iterations=iterations, workers=workers, backend=backend
    )
    maximum_error = max(
        abs(left - right)
        for left_row, right_row in zip(serial.grid, parallel.grid)
        for left_cell, right_cell in zip(left_row, right_row)
        for left, right in zip(left_cell, right_cell)
    )
    speedup = math.inf if parallel.elapsed == 0.0 else serial.elapsed / parallel.elapsed
    return CP2LBMExecution(
        serial.elapsed, parallel.elapsed, speedup, maximum_error, workers
    )


def cp2_swinging_rope_analytical(
    x: float,
    time_value: float,
    parameters: CP2SwingingRopeParameters = _CP2_ROPE_DEFAULT_PARAMETERS,
    *,
    terms: int = 400,
) -> float:
    """Fourier-series solution for the triangular initial displacement."""

    if not isinstance(terms, int) or isinstance(terms, bool) or terms <= 0:
        raise ValueError("terms must be a positive integer")
    coordinate = float(x)
    time_number = float(time_value)
    if not 0.0 <= coordinate <= parameters.length or time_number < 0.0:
        raise ValueError("x must lie on the rope and time must be non-negative")
    total = 0.0
    for index in range(terms):
        harmonic = 2 * index + 1
        total += (
            (-1.0) ** index
            / (harmonic * harmonic)
            * math.sin(harmonic * math.pi * coordinate / parameters.length)
            * math.cos(
                harmonic
                * math.pi
                * parameters.nu
                * time_number
                / parameters.length
            )
        )
    return 8.0 * parameters.h / (math.pi * math.pi) * total


def cp2_swinging_rope_implicit(
    *,
    parameters: CP2SwingingRopeParameters = _CP2_ROPE_DEFAULT_PARAMETERS,
    t_bound: float = 10.0,
    time_step: float = 0.01,
    positions: Sequence[float] = (0.375, 0.25),
    snapshot_times: Sequence[float] = (),
) -> CP2ImplicitRopeResult:
    """Unconditionally stable Newmark/central-space Task-3 solver.

    ``snapshot_times`` captures the complete spatial state without forcing the
    time traces to retain every spatial node at every step.
    """

    if time_step <= 0.0 or t_bound <= 0.0:
        raise ValueError("time_step and t_bound must be positive")
    steps = round(t_bound / time_step)
    if not math.isclose(steps * time_step, t_bound, abs_tol=1.0e-12):
        raise ValueError("t_bound must be an integer multiple of time_step")
    coordinates = tuple(float(value) for value in positions)
    if any(value < 0.0 or value > parameters.length for value in coordinates):
        raise ValueError("positions must lie on the rope")
    requested_snapshots = tuple(sorted({float(value) for value in snapshot_times}))
    if any(
        not math.isfinite(value) or value < 0.0 or value > t_bound
        for value in requested_snapshots
    ):
        raise ValueError("snapshot times must lie in [0, t_bound]")
    snapshot_steps = tuple(round(value / time_step) for value in requested_snapshots)
    if any(
        not math.isclose(index * time_step, value, abs_tol=1.0e-12)
        for index, value in zip(snapshot_steps, requested_snapshots)
    ):
        raise ValueError("snapshot times must be multiples of time_step")
    displacement, initial_velocity = cp2_swinging_rope_initial_state(parameters)
    current = list(displacement)
    velocity = list(initial_velocity)
    count = parameters.interior_points
    spacing = parameters.length / (count + 1)
    ratio = (parameters.nu * time_step / spacing) ** 2
    beta = 0.25
    gamma = 0.5
    diagonal = 1.0 + 2.0 * beta * ratio
    lower = -beta * ratio
    upper = -beta * ratio

    def acceleration(values: Sequence[float]) -> list[float]:
        coefficient = parameters.nu * parameters.nu / (spacing * spacing)
        padded = (0.0, *values, 0.0)
        return [
            coefficient
            * (padded[index] - 2.0 * padded[index + 1] + padded[index + 2])
            for index in range(count)
        ]

    current_acceleration = acceleration(current)

    # Constant Thomas factors are reusable for all 1000 time steps.
    modified_upper = [0.0] * max(0, count - 1)
    denominators = [0.0] * count
    denominators[0] = diagonal
    if count > 1:
        modified_upper[0] = upper / denominators[0]
    for index in range(1, count):
        denominators[index] = diagonal - lower * modified_upper[index - 1]
        if index < count - 1:
            modified_upper[index] = upper / denominators[index]

    def sample(values: Sequence[float], coordinate: float) -> float:
        position = coordinate / spacing
        left_grid = math.floor(position)
        fraction = position - left_grid

        def node(grid_index: int) -> float:
            if grid_index <= 0 or grid_index >= count + 1:
                return 0.0
            return values[grid_index - 1]

        return node(left_grid) + fraction * (node(left_grid + 1) - node(left_grid))

    trajectories = [[sample(current, coordinate)] for coordinate in coordinates]
    times = [0.0]
    snapshots_by_step: dict[int, tuple[float, ...]] = {}
    if 0 in snapshot_steps:
        snapshots_by_step[0] = (0.0, *current, 0.0)
    for step_index in range(1, steps + 1):
        right = [
            value
            + time_step * speed
            + time_step * time_step * (0.5 - beta) * rate
            for value, speed, rate in zip(
                current, velocity, current_acceleration
            )
        ]
        forward = [0.0] * count
        forward[0] = right[0] / denominators[0]
        for index in range(1, count):
            forward[index] = (
                right[index] - lower * forward[index - 1]
            ) / denominators[index]
        next_values = [0.0] * count
        next_values[-1] = forward[-1]
        for index in range(count - 2, -1, -1):
            next_values[index] = (
                forward[index] - modified_upper[index] * next_values[index + 1]
            )
        next_acceleration = acceleration(next_values)
        velocity = [
            speed
            + time_step
            * ((1.0 - gamma) * old_rate + gamma * new_rate)
            for speed, old_rate, new_rate in zip(
                velocity, current_acceleration, next_acceleration
            )
        ]
        current = next_values
        current_acceleration = next_acceleration
        times.append(step_index * time_step)
        for trajectory, coordinate in zip(trajectories, coordinates):
            trajectory.append(sample(current, coordinate))
        if step_index in snapshot_steps:
            snapshots_by_step[step_index] = (0.0, *current, 0.0)
    snapshot_positions = tuple(index * spacing for index in range(count + 2))
    return CP2ImplicitRopeResult(
        tuple(times),
        coordinates,
        tuple(tuple(trajectory) for trajectory in trajectories),
        requested_snapshots,
        snapshot_positions,
        tuple(snapshots_by_step[index] for index in snapshot_steps),
    )


def cp2_task3_swinging_rope(
    *,
    parameters: CP2SwingingRopeParameters = _CP2_ROPE_DEFAULT_PARAMETERS,
    t_bound: float = 10.0,
    time_step: float = 0.01,
    trace_positions: Sequence[float] = (0.375, 0.25),
    profile_times: Sequence[float] = (5.0, 8.0),
    surface_step: float = 0.1,
    terms: int = 100,
) -> CP2RopeStudy:
    """Run the corrected complete CP2 Task-3 output study.

    The 2022 peer-reviewed solution resolves inconsistencies in the 2007
    printing: ``nu=0.06``, a 0--10 s horizon, and spatial profiles at 5 s and
    8 s.  The lower-level solver remains configurable and
    :data:`CP2_PRINTED_ROPE_PARAMETERS` reproduces the printed ``nu=0.6``
    variant for provenance studies.
    """

    if not math.isfinite(surface_step) or surface_step <= 0.0:
        raise ValueError("surface_step must be positive and finite")
    if not isinstance(terms, int) or isinstance(terms, bool) or terms <= 0:
        raise ValueError("terms must be a positive integer")
    profile_output_times = tuple(float(value) for value in profile_times)
    if any(value < 0.0 or value > t_bound for value in profile_output_times):
        raise ValueError("profile times must lie in [0, t_bound]")
    surface_intervals = round(t_bound / surface_step)
    if not math.isclose(
        surface_intervals * surface_step, t_bound, abs_tol=1.0e-12
    ):
        raise ValueError("t_bound must be an integer multiple of surface_step")
    surface_times = tuple(index * surface_step for index in range(surface_intervals + 1))
    captured_times = tuple(sorted({*profile_output_times, *surface_times}))
    implicit = cp2_swinging_rope_implicit(
        parameters=parameters,
        t_bound=t_bound,
        time_step=time_step,
        positions=trace_positions,
        snapshot_times=captured_times,
    )
    snapshot_map = dict(zip(implicit.snapshot_times, implicit.snapshots))
    analytical_traces = tuple(
        tuple(
            cp2_swinging_rope_analytical(
                coordinate, time_value, parameters, terms=terms
            )
            for time_value in implicit.times
        )
        for coordinate in implicit.positions
    )
    numerical_profiles = tuple(snapshot_map[value] for value in profile_output_times)
    analytical_profiles = tuple(
        tuple(
            cp2_swinging_rope_analytical(
                coordinate, time_value, parameters, terms=terms
            )
            for coordinate in implicit.snapshot_positions
        )
        for time_value in profile_output_times
    )
    maximum_trace_error = max(
        (
            abs(value - reference)
            for values, references in zip(
                implicit.displacement, analytical_traces
            )
            for value, reference in zip(values, references)
        ),
        default=0.0,
    )
    maximum_profile_error = max(
        (
            abs(value - reference)
            for values, references in zip(
                numerical_profiles, analytical_profiles
            )
            for value, reference in zip(values, references)
        ),
        default=0.0,
    )
    return CP2RopeStudy(
        implicit.times,
        implicit.positions,
        implicit.displacement,
        analytical_traces,
        profile_output_times,
        implicit.snapshot_positions,
        numerical_profiles,
        analytical_profiles,
        surface_times,
        tuple(snapshot_map[value] for value in surface_times),
        maximum_trace_error,
        maximum_profile_error,
    )


def cp2_task3_compare(
    *,
    parameters: CP2SwingingRopeParameters = _CP2_ROPE_DEFAULT_PARAMETERS,
    times: Sequence[float] = (0.0, 5.0, 8.0, 10.0),
    positions: Sequence[float] = (0.375, 0.25),
    terms: int = 400,
) -> CP2RopeComparison:
    """Evaluate Task-3 output locations against the independent exact series.

    The analytical reference avoids conflating output interval ``0.01`` with
    the much smaller stable internal step required by a 500-point explicit MOL.
    """

    output_times = tuple(float(value) for value in times)
    coordinates = tuple(float(value) for value in positions)
    if any(value < 0.0 for value in output_times):
        raise ValueError("times must be non-negative")
    if any(value < 0.0 or value > parameters.length for value in coordinates):
        raise ValueError("positions must lie on the rope")

    analytical = tuple(
        tuple(
            cp2_swinging_rope_analytical(x, time_value, parameters, terms=terms)
            for time_value in output_times
        )
        for x in coordinates
    )
    implicit = cp2_swinging_rope_implicit(
        parameters=parameters,
        t_bound=max(output_times) if output_times else 0.01,
        time_step=0.01,
        positions=coordinates,
    )
    indices = tuple(round(value / 0.01) for value in output_times)
    if any(
        not math.isclose(index * 0.01, value, abs_tol=1.0e-12)
        for index, value in zip(indices, output_times)
    ):
        raise ValueError("comparison times must be multiples of 0.01 seconds")
    numerical = tuple(
        tuple(trajectory[index] for index in indices)
        for trajectory in implicit.displacement
    )
    maximum_error = max(
        abs(value - reference)
        for row, expected in zip(numerical, analytical)
        for value, reference in zip(row, expected)
    )
    return CP2RopeComparison(
        output_times,
        coordinates,
        numerical,
        analytical,
        maximum_error,
    )
