"""ARGESIM C11: SCARA Robot.

The equations, parameters, initial values and tasks follow the official
C11 definition. State order is `(q1, q2, q3, dq1, dq2, dq3, I1, I2, I3)`.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from ..ivp import InitialValueProblem, IntegrationError, IntegrationResult, Rhs, Vector
from ..runtime import (
    merge_integration_results,
    merge_solver_options,
    normalise_solver_name,
    solve_ivp,
)


@dataclass(frozen=True)
class C11Parameters:
    # Mechanical system parameters
    m1: float = 8.0
    L1: float = 0.4
    m2: float = 6.0
    L2: float = 0.3
    m3A: float = 2.5
    m3L: float = 0.5
    Theta3_mot: float = 9.1e-6
    g: float = 9.81

    # Motor parameters
    kT1: float = 0.4
    kT2: float = 0.25
    kT3: float = 0.4
    Ra1: float = 3.9
    Ra2: float = 50.0
    Ra3: float = 40.0
    La1: float = 7.3e-3
    La2: float = 25.0e-3
    La3: float = 25.0e-3
    u1: float = 130.0
    u2: float = 100.0
    u3: float = 1047.0
    T1_max: float = 2.3
    T2_max: float = 0.6
    T3_max: float = 0.6

    # Controller parameters
    P1: float = 1000.0
    P2: float = 1000.0
    P3: float = 5000.0
    D1: float = 10.0
    D2: float = 25.0
    D3: float = 10.0

    # Task b limit
    U1_max_reg: float = 100.0
    U2_max_reg: float = 75.0
    U3_max_reg: float = 90.0

    # Task c limit
    U1_max_max: float = 230.0
    U2_max_max: float = 230.0
    U3_max_max: float = 230.0

    # Obstacle properties
    h_obs: float = 0.2
    x_obs: float = 0.25
    d_crit: float = 0.1

    # Motor specific constant for 3-phase DC
    phase_factor: float = 1.5

    # Hardcoded threshold for bang-bang velocity zeroing used in collision avoidance
    # A tiny threshold is needed because exact 0 is practically never hit, and
    # discontinuous control leads to Zeno chattering
    v_zero_threshold: float = 1e-4

    def __post_init__(self) -> None:
        values = tuple(
            value
            for name, value in vars(self).items()
            if name != "x_obs"
        )
        if any(not math.isfinite(value) for value in (*values, self.x_obs)):
            raise ValueError("C11 parameters must be finite")
        if any(value <= 0.0 for value in values):
            raise ValueError("C11 physical and controller parameters must be positive")


_C11_DEFAULT_PARAMETERS = C11Parameters()

C11_INITIAL_STATE: Vector = (0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)

C11_TARGET_STATE = (2.0, 2.0, 0.3)


@dataclass(frozen=True)
class C11TaskAReport:
    """Machine-readable description of the implemented Task-A formulation."""

    formulation: str
    state_order: tuple[str, ...]
    inertia_terms: tuple[float, float, float]
    state_dimension: int
    algebraic_state_dimension: int


@dataclass(frozen=True)
class C11CollisionStudy:
    """Task-C trajectory together with the quantities requested for plotting."""

    result: IntegrationResult
    x_tip: tuple[float, ...]
    vertical_clearance: tuple[float, ...]
    obstacle_x: tuple[float, ...]


def c11_inertia_terms(
    parameters: C11Parameters = _C11_DEFAULT_PARAMETERS,
) -> tuple[float, float, float]:
    """Return the three inertia coefficients from the official C11 model."""

    m3 = parameters.m3A + parameters.m3L
    theta1 = (parameters.m1 / 3.0 + parameters.m2 + m3) * parameters.L1**2
    theta2 = (parameters.m2 / 2.0 + m3) * parameters.L1 * parameters.L2
    theta3 = (parameters.m2 / 3.0 + m3) * parameters.L2**2
    return theta1, theta2, theta3


def _armature_current_limits(p: C11Parameters) -> tuple[float, float, float]:
    # The specified maximum motor torque is before gearing.
    return (
        p.T1_max / (p.phase_factor * p.kT1),
        p.T2_max / (p.phase_factor * p.kT2),
        p.T3_max / (p.phase_factor * p.kT3),
    )


def c11_rhs(
    parameters: C11Parameters = _C11_DEFAULT_PARAMETERS,
    task: str = "b"
) -> Rhs:
    """Return the C11 equations of motion."""

    p = parameters

    Theta1, Theta2, Theta3 = c11_inertia_terms(p)

    I1_max, I2_max, I3_max = _armature_current_limits(p)

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        q1, q2, q3, dq1, dq2, dq3, I1, I2, I3 = state

        # Control
        q1_ref, q2_ref, q3_ref = C11_TARGET_STATE

        # Collision avoidance for task c
        avoiding_collision = False
        if task == "c":
            x_tip = p.L1 * math.cos(q1) + p.L2 * math.cos(q1 + q2)
            if x_tip - p.x_obs <= p.d_crit and q3 < p.h_obs:
                avoiding_collision = True

        U1 = p.P1 * (q1_ref - q1) - p.D1 * dq1
        U2 = p.P2 * (q2_ref - q2) - p.D2 * dq2
        U3 = p.P3 * (q3_ref - q3) - p.D3 * dq3

        U1_max = p.U1_max_reg
        U2_max = p.U2_max_reg
        U3_max = p.U3_max_reg

        if avoiding_collision:
            U1_max = p.U1_max_max
            U2_max = p.U2_max_max
            U1 = -p.U1_max_max if dq1 > p.v_zero_threshold else (p.U1_max_max if dq1 < -p.v_zero_threshold else 0.0)
            U2 = -p.U2_max_max if dq2 > p.v_zero_threshold else (p.U2_max_max if dq2 < -p.v_zero_threshold else 0.0)

        U1 = max(-U1_max, min(U1, U1_max))
        U2 = max(-U2_max, min(U2, U2_max))
        U3 = max(-U3_max, min(U3, U3_max))

        # Limit armature currents
        I1_clamped = max(-I1_max, min(I1, I1_max))
        I2_clamped = max(-I2_max, min(I2, I2_max))
        I3_clamped = max(-I3_max, min(I3, I3_max))

        # Motor electrical equations
        dI1 = (U1 - p.kT1 * p.u1 * dq1 - p.Ra1 * I1_clamped) / p.La1
        dI2 = (U2 - p.kT2 * p.u2 * dq2 - p.Ra2 * I2_clamped) / p.La2
        dI3 = (U3 - p.kT3 * p.u3 * dq3 - p.Ra3 * I3_clamped) / p.La3

        # At saturation only inward derivatives can change the current.
        # The integration loop also projects accepted states onto the limits.
        if I1 >= I1_max and dI1 > 0: dI1 = 0.0
        if I1 <= -I1_max and dI1 < 0: dI1 = 0.0

        if I2 >= I2_max and dI2 > 0: dI2 = 0.0
        if I2 <= -I2_max and dI2 < 0: dI2 = 0.0

        if I3 >= I3_max and dI3 > 0: dI3 = 0.0
        if I3 <= -I3_max and dI3 < 0: dI3 = 0.0

        # Joint torques
        T1 = p.u1 * p.phase_factor * p.kT1 * I1_clamped
        T2 = p.u2 * p.phase_factor * p.kT2 * I2_clamped
        T3 = p.u3 * p.phase_factor * p.kT3 * I3_clamped

        # Mechanical system
        ma11 = Theta1 + 2 * Theta2 * math.cos(q2) + Theta3
        ma12 = Theta2 * math.cos(q2) + Theta3
        ma21 = ma12
        ma22 = Theta3
        ma33 = p.m3L + p.Theta3_mot * p.u3**2

        b1 = T1 + Theta2 * (2 * dq1 * dq2 + dq2**2) * math.sin(q2)
        b2 = T2 - Theta2 * dq1**2 * math.sin(q2)
        b3 = T3 - p.m3L * p.g

        # Invert mass matrix for joint 1 and 2
        det = ma11 * ma22 - ma12 * ma21
        ddq1 = (ma22 * b1 - ma12 * b2) / det
        ddq2 = (-ma21 * b1 + ma11 * b2) / det

        # Joint 3 is decoupled
        ddq3 = b3 / ma33

        return (dq1, dq2, dq3, ddq1, ddq2, ddq3, dI1, dI2, dI3)

    return rhs

def c11_problem(
    *,
    parameters: C11Parameters = _C11_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C11_INITIAL_STATE,
    t_bound: float = 1.0,
    task: str = "b",
) -> InitialValueProblem:
    """Build the C11 equations. Use solve_c11 for bounded integration."""

    if task not in {"a", "b", "c"}:
        raise ValueError("C11 task must be 'a', 'b', or 'c'")

    problem = InitialValueProblem(
        c11_rhs(parameters, task=task),
        0.0,
        initial_state,
        t_bound,
        name=f"ARGESIM-C11-scara-robot-{task}",
        autonomous=True,
    )
    if problem.dimension != 9:
        raise ValueError("C11 initial_state must contain nine state variables")
    return problem


def solve_c11(
    method: str = "rk45",
    *,
    parameters: C11Parameters = _C11_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C11_INITIAL_STATE,
    t_bound: float = 1.0,
    task: str = "b",
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Solve C11 and enforce armature current limits at accepted samples."""

    problem = c11_problem(
        parameters=parameters,
        initial_state=initial_state,
        t_bound=t_bound,
        task=task,
    )
    default_quantum = (
        1.0e-3,
        1.0e-3,
        1.0e-4,
        1.0e-3,
        1.0e-3,
        1.0e-4,
        1.0e-2,
        1.0e-2,
        1.0e-2,
    )
    defaults = {
        "euler": {"step": 1.0e-5},
        "rk4": {"step": 1.0e-4},
        "rk45": {"rtol": 1.0e-6, "atol": 1.0e-8, "max_step": 1.0e-2},
        "qss1": {"quantum": default_quantum},
        "qss2": {"quantum": default_quantum},
    }
    method = normalise_solver_name(method)
    controls = merge_solver_options(options)
    limits = _armature_current_limits(parameters)

    def project_currents(state: Vector) -> Vector:
        return state[:6] + tuple(
            max(-limit, min(limit, current))
            for current, limit in zip(state[6:], limits)
        )

    def exceeds_current_limit(
        _start: float, _before: Vector, _time: float, state: Vector,
    ) -> bool:
        return any(abs(current) > limit for current, limit in zip(state[6:], limits))

    segments = []
    start, state = problem.t0, project_currents(problem.y0)
    timed_steps = method in {"euler", "rk4", "rk45", "liqss-bdf"}
    while start < problem.t_bound:
        segment = solve_ivp(
            replace(problem, t0=start, y0=state, _stop_after_step=exceeds_current_limit),
            method,
            options=controls,
            defaults=defaults,
        )
        start, state = segment.final_time, project_currents(segment.final_state)
        if state != segment.final_state:
            # Discard the quantizer/adaptive history of the unbounded endpoint.
            # The projected state initializes the very next accepted step.
            segment = replace(segment, states=(*segment.states[:-1], state))
        segments.append(segment)
        if start == problem.t_bound:
            break

        time_steps = len(segment.times) - 1 if timed_steps else 0
        for option, used in (
            ("max_steps", time_steps + segment.stats.rejected_steps),
            ("max_events", segment.stats.accepted_steps - time_steps),
        ):
            if used:
                controls[option] = controls.get(option, 1_000_000) - used
                if controls[option] <= 0:
                    raise IntegrationError(f"{method} exceeded {option}")
    return merge_integration_results(segments)

def c11_task_a(
    parameters: C11Parameters = _C11_DEFAULT_PARAMETERS,
) -> C11TaskAReport:
    """Describe the explicit first-order state-space formulation used here."""

    return C11TaskAReport(
        formulation="explicit-first-order-state-space",
        state_order=(
            "q1",
            "q2",
            "q3",
            "dq1",
            "dq2",
            "dq3",
            "I1",
            "I2",
            "I3",
        ),
        inertia_terms=c11_inertia_terms(parameters),
        state_dimension=9,
        algebraic_state_dimension=0,
    )


def c11_task_b(
    method: str = "rk45",
    *,
    parameters: C11Parameters = _C11_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C11_INITIAL_STATE,
    t_bound: float = 2.0,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Run the point-to-point PD-control experiment without collision avoidance."""

    return solve_c11(
        method,
        parameters=parameters,
        initial_state=initial_state,
        t_bound=t_bound,
        task="b",
        options=options,
    )


def c11_task_c(
    method: str = "rk45",
    *,
    parameters: C11Parameters = _C11_DEFAULT_PARAMETERS,
    initial_state: Sequence[float] = C11_INITIAL_STATE,
    t_bound: float = 2.0,
    options: Mapping[str, object] | None = None,
) -> C11CollisionStudy:
    """Run collision avoidance and expose the official diagnostic trajectories."""

    result = solve_c11(
        method,
        parameters=parameters,
        initial_state=initial_state,
        t_bound=t_bound,
        task="c",
        options=options,
    )
    x_tip = tuple(
        parameters.L1 * math.cos(state[0])
        + parameters.L2 * math.cos(state[0] + state[1])
        for state in result.states
    )
    vertical_clearance = tuple(
        state[2] - parameters.h_obs for state in result.states
    )
    obstacle_x = tuple(parameters.x_obs for _ in result.times)
    return C11CollisionStudy(
        result=result,
        x_tip=x_tip,
        vertical_clearance=vertical_clearance,
        obstacle_x=obstacle_x,
    )
