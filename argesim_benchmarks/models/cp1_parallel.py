"""ARGESIM CP1: Parallel Simulation Techniques.

This file provides the numerical benchmark models for the CP1 tasks:
- Task A: parallel parameter study of a damped mass-spring system.
- Task B: Coupled predator-prey population model (10 ODEs).
- Task C: Swinging rope PDE discretized by the method of lines.
"""

from __future__ import annotations

import math
import random
import time
from collections.abc import Sequence
from dataclasses import dataclass

from ..ivp import InitialValueProblem, Rhs, Vector
from ..parallel import OrderedExecutor, ParallelRun, benchmark_ordered_map
from ..solvers import rk4

# --- Task A: Parameter Sweep ---

def cp1_task_a_ivp(
    damping_factor: float,
    *,
    mass: float = 450.0,
    stiffness: float = 9000.0,
    t_bound: float = 2.0,
) -> InitialValueProblem:
    """Create one IVP for the parallel damping-parameter study.

    Equation: m x'' + d x' + k x = 0
    State vector: (x, x')
    Initial condition: x(0) = 0.1, x'(0) = 0
    The damping factor d is typically drawn from U(800, 1200).
    """
    m = float(mass)
    k = float(stiffness)
    d = float(damping_factor)
    if any(not math.isfinite(value) for value in (m, k, d)):
        raise ValueError("mass, stiffness, and damping must be finite")
    if m <= 0.0 or k <= 0.0 or d < 0.0:
        raise ValueError("mass and stiffness must be positive; damping non-negative")

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
    if not isinstance(interior_points, int) or isinstance(interior_points, bool):
        raise TypeError("interior_points must be an integer")
    if interior_points < 1:
        raise ValueError("interior_points must be positive")
    if any(not math.isfinite(value) for value in (a, b, d, omega, length)):
        raise ValueError("CP1 task-C parameters must be finite")
    if a <= 0.0 or length <= 0.0 or d < 0.0:
        raise ValueError("a and length must be positive; d must be non-negative")

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


# --- Executable official workloads and reusable timing reports ---


@dataclass(frozen=True)
class CP1TaskAStudy:
    """Monte-Carlo damping study, including equivalent execution timings."""

    dampings: tuple[float, ...]
    times: tuple[float, ...]
    mean_position: tuple[float, ...]
    execution: ParallelRun[tuple[float, ...]]


@dataclass(frozen=True)
class CP1TaskBValidation:
    """Numerical terminal state and error against the published CP1 table."""

    terminal_state: Vector
    published_state: Vector
    maximum_error: float


@dataclass(frozen=True)
class CP1TaskCResult:
    """Selected rope trajectories and execution metadata."""

    times: tuple[float, ...]
    relative_positions: tuple[float, ...]
    displacement: tuple[tuple[float, ...], ...]
    elapsed: float
    workers: int
    backend: str


@dataclass(frozen=True)
class CP1ExecutionComparison:
    serial_seconds: float
    parallel_seconds: float
    speedup: float
    maximum_error: float
    serial_terminal_state: Vector
    parallel_terminal_state: Vector


def _cp1_oscillator_case(
    payload: tuple[float, float, float, float, float, int],
) -> tuple[float, ...]:
    """Integrate one Task-A sample with the prescribed classical RK4 step."""

    damping, mass, stiffness, t_bound, step, output_stride = payload
    x = 0.1
    velocity = 0.0
    positions = [x]
    steps = round(t_bound / step)

    def rates(position: float, speed: float) -> tuple[float, float]:
        return speed, (-stiffness * position - damping * speed) / mass

    for index in range(1, steps + 1):
        k1x, k1v = rates(x, velocity)
        k2x, k2v = rates(x + 0.5 * step * k1x, velocity + 0.5 * step * k1v)
        k3x, k3v = rates(x + 0.5 * step * k2x, velocity + 0.5 * step * k2v)
        k4x, k4v = rates(x + step * k3x, velocity + step * k3v)
        x += step * (k1x + 2.0 * k2x + 2.0 * k3x + k4x) / 6.0
        velocity += step * (k1v + 2.0 * k2v + 2.0 * k3v + k4v) / 6.0
        if index % output_stride == 0 or index == steps:
            positions.append(x)
    return tuple(positions)


def cp1_task_a_study(
    *,
    samples: int = 1000,
    seed: int = 1729,
    step: float = 0.001,
    output_step: float = 0.01,
    t_bound: float = 2.0,
    workers: int = 2,
    backend: str = "thread",
    warmups: int = 0,
    repeats: int = 1,
) -> CP1TaskAStudy:
    """Run official CP1-A and compare serial with parallel sample execution."""

    if not isinstance(samples, int) or isinstance(samples, bool) or samples <= 0:
        raise ValueError("samples must be a positive integer")
    if not isinstance(seed, int) or isinstance(seed, bool):
        raise TypeError("seed must be an integer")
    if step <= 0.0 or output_step < step or t_bound <= 0.0:
        raise ValueError("steps and t_bound must be positive; output_step >= step")
    output_stride = round(output_step / step)
    if not math.isclose(output_stride * step, output_step, abs_tol=1.0e-14):
        raise ValueError("output_step must be an integer multiple of step")
    integration_steps = round(t_bound / step)
    if not math.isclose(integration_steps * step, t_bound, abs_tol=1.0e-14):
        raise ValueError("t_bound must be an integer multiple of step")

    rng = random.Random(seed)
    dampings = tuple(rng.uniform(800.0, 1200.0) for _ in range(samples))
    payloads = tuple(
        (damping, 450.0, 9000.0, t_bound, step, output_stride)
        for damping in dampings
    )
    execution = benchmark_ordered_map(
        _cp1_oscillator_case,
        payloads,
        workers=workers,
        backend=backend,
        warmups=warmups,
        repeats=repeats,
        tolerance=0.0,
    )
    trajectories = execution.parallel_values
    mean_position = tuple(
        sum(trajectory[index] for trajectory in trajectories) / samples
        for index in range(len(trajectories[0]))
    )
    times = tuple(
        min(t_bound, index * output_step) for index in range(len(mean_position))
    )
    return CP1TaskAStudy(dampings, times, mean_position, execution)


def cp1_task_b_validate(*, step: float = 0.01) -> CP1TaskBValidation:
    """Solve CP1-B with the official RK4 step and check its published endpoint."""

    result = rk4(cp1_task_b_ivp(), step)
    names = ("v1", "v2", "w1", "w2", "x1", "x2", "y1", "y2", "z1", "z2")
    published = tuple(CP1_TASK_B_TERMINAL_VALUES[name] for name in names)
    error = max(abs(actual - expected) for actual, expected in zip(result.final_state, published))
    return CP1TaskBValidation(result.final_state, published, error)


def _cp1_task_b_block(
    payload: tuple[int, tuple[float, ...]],
) -> tuple[float, float]:
    """Evaluate one coupled population pair using a shared state snapshot."""

    block, state = payload
    v1, v2, w1, w2, x1, x2, y1, y2, z1, z2 = state
    if block == 0:
        interaction = v2 * (0.01 * w1 + 0.02 * x1 + 0.01 * y1 + 0.03 * z1)
        return (
            2.0 * v1 - 0.5 * v1 * v2 - 0.01 * v1 * v1,
            -0.2 * v2 + 0.4 * v1 * v2 - 0.02 * v2 * v2 + interaction,
        )
    if block == 1:
        interaction = w1 * (-0.02 * v2 + 0.04 * x2)
        return (
            w1 - 0.5 * w1 * w2 - 0.02 * w1 * w1 + interaction,
            -0.1 * w2 + 0.4 * w1 * w2 - 0.04 * w2 * w2,
        )
    if block == 2:
        return (
            3.0 * x1 - 0.9 * x1 * x2 - 0.02 * x1 * x1 - 0.025 * x1 * v2,
            -0.2 * x2 + 0.2 * x1 * x2 - 0.04 * x2 * x2 - 0.1 * x2 * w1,
        )
    if block == 3:
        interaction = y1 * (-0.03 * v2 + 0.025 * z2)
        return (
            y1 - 0.8 * y1 * y2 - 0.04 * y1 * y1 + interaction,
            -0.2 * y2 + 0.6 * y1 * y2 - 0.07 * y2 * y2,
        )
    if block == 4:
        return (
            3.0 * z1 - 0.7 * z1 * z2 - 0.02 * z1 * z1 - 0.02 * z1 * v2,
            -0.5 * z2 + 0.3 * z1 * z2 - 0.04 * z2 * z2 - 0.04 * z2 * y1,
        )
    raise ValueError("CP1-B block must be in 0..4")


def _cp1_task_b_integrate(
    *,
    t_bound: float,
    step: float,
    workers: int,
    backend: str,
) -> tuple[Vector, float]:
    steps = round(t_bound / step)
    if not math.isclose(steps * step, t_bound, abs_tol=1.0e-12):
        raise ValueError("t_bound must be an integer multiple of step")
    state = [1.0] * 10

    def derivative(values: Sequence[float], pool: OrderedExecutor) -> list[float]:
        snapshot = tuple(values)
        blocks = pool.map(
            _cp1_task_b_block,
            tuple((index, snapshot) for index in range(5)),
        )
        return [value for block in blocks for value in block]

    started = time.perf_counter()
    with OrderedExecutor(workers, backend=backend) as pool:
        for _ in range(steps):
            k1 = derivative(state, pool)
            y2 = [value + 0.5 * step * rate for value, rate in zip(state, k1)]
            k2 = derivative(y2, pool)
            y3 = [value + 0.5 * step * rate for value, rate in zip(state, k2)]
            k3 = derivative(y3, pool)
            y4 = [value + step * rate for value, rate in zip(state, k3)]
            k4 = derivative(y4, pool)
            state = [
                value + step * (a + 2.0 * b + 2.0 * c + d) / 6.0
                for value, a, b, c, d in zip(state, k1, k2, k3, k4)
            ]
    return tuple(state), time.perf_counter() - started


def cp1_task_b_compare_execution(
    *,
    t_bound: float = 100.0,
    step: float = 0.01,
    workers: int = 2,
    backend: str = "thread",
) -> CP1ExecutionComparison:
    """Measure the deliberately fine-grained CP1-B decomposition."""

    serial_state, serial_seconds = _cp1_task_b_integrate(
        t_bound=t_bound, step=step, workers=1, backend="serial"
    )
    parallel_state, parallel_seconds = _cp1_task_b_integrate(
        t_bound=t_bound, step=step, workers=workers, backend=backend
    )
    maximum_error = max(
        abs(left - right) for left, right in zip(serial_state, parallel_state)
    )
    speedup = math.inf if parallel_seconds == 0.0 else serial_seconds / parallel_seconds
    return CP1ExecutionComparison(
        serial_seconds,
        parallel_seconds,
        speedup,
        maximum_error,
        serial_state,
        parallel_state,
    )


def _cp1_acceleration_chunk(
    payload: tuple[int, int, tuple[float, ...], float],
) -> tuple[float, ...]:
    start, stop, padded, coefficient = payload
    return tuple(
        coefficient * (padded[index] - 2.0 * padded[index + 1] + padded[index + 2])
        for index in range(start, stop)
    )


def _partition(size: int, parts: int) -> tuple[tuple[int, int], ...]:
    width, remainder = divmod(size, parts)
    ranges = []
    start = 0
    for index in range(parts):
        stop = start + width + (1 if index < remainder else 0)
        if stop > start:
            ranges.append((start, stop))
        start = stop
    return tuple(ranges)


def cp1_task_c_solve(
    *,
    interior_points: int = 799,
    t_bound: float = 30.0,
    step: float = 0.005,
    output_step: float = 0.05,
    relative_positions: Sequence[float] = (0.9, 0.75, 0.5, 0.25, 0.1),
    workers: int = 1,
    backend: str = "thread",
) -> CP1TaskCResult:
    """Run CP1-C by RK4 with reusable spatial-domain workers.

    The official workload uses 800 intervals, ``step=0.005`` and 30 seconds.
    Worker pools are created once and reused for every Runge--Kutta stage.
    """

    problem = cp1_task_c_ivp(interior_points, t_bound=t_bound)
    if step <= 0.0 or output_step < step:
        raise ValueError("step must be positive and output_step must be >= step")
    steps = round(t_bound / step)
    stride = round(output_step / step)
    if not math.isclose(steps * step, t_bound, abs_tol=1.0e-12):
        raise ValueError("t_bound must be an integer multiple of step")
    if not math.isclose(stride * step, output_step, abs_tol=1.0e-12):
        raise ValueError("output_step must be an integer multiple of step")
    positions = tuple(float(value) for value in relative_positions)
    if any(value <= 0.0 or value >= 1.0 for value in positions):
        raise ValueError("relative_positions must lie strictly inside (0, 1)")
    if not isinstance(workers, int) or isinstance(workers, bool) or workers <= 0:
        raise ValueError("workers must be a positive integer")

    n = interior_points
    state = list(problem.y0)
    coefficient = 1.0 / ((10.0 / (n + 1)) ** 2 * 2.0)
    chunks = _partition(n, min(workers, n))
    sample_indices = tuple(
        min(n - 1, max(0, round(value * (n + 1)) - 1)) for value in positions
    )
    output_times = [0.0]
    output = [[state[index]] for index in sample_indices]

    def derivative(
        current_time: float,
        values: Sequence[float],
        pool: OrderedExecutor,
    ) -> list[float]:
        displacement = tuple(values[:n])
        boundary = math.exp(-0.2 * current_time) * math.sin(current_time)
        padded = (0.0, *displacement, boundary)
        payloads = tuple((start, stop, padded, coefficient) for start, stop in chunks)
        acceleration_chunks = pool.map(_cp1_acceleration_chunk, payloads)
        accelerations = [value for chunk in acceleration_chunks for value in chunk]
        return [*values[n:], *accelerations]

    started = time.perf_counter()
    with OrderedExecutor(workers, backend=backend) as pool:
        for iteration in range(1, steps + 1):
            current_time = (iteration - 1) * step
            k1 = derivative(current_time, state, pool)
            y2 = [value + 0.5 * step * rate for value, rate in zip(state, k1)]
            k2 = derivative(current_time + 0.5 * step, y2, pool)
            y3 = [value + 0.5 * step * rate for value, rate in zip(state, k2)]
            k3 = derivative(current_time + 0.5 * step, y3, pool)
            y4 = [value + step * rate for value, rate in zip(state, k3)]
            k4 = derivative(current_time + step, y4, pool)
            state = [
                value + step * (a + 2.0 * b + 2.0 * c + d) / 6.0
                for value, a, b, c, d in zip(state, k1, k2, k3, k4)
            ]
            if iteration % stride == 0 or iteration == steps:
                output_times.append(min(t_bound, iteration * step))
                for trajectory, index in zip(output, sample_indices):
                    trajectory.append(state[index])
    elapsed = time.perf_counter() - started
    return CP1TaskCResult(
        tuple(output_times),
        positions,
        tuple(tuple(trajectory) for trajectory in output),
        elapsed,
        workers,
        backend,
    )
