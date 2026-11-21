"""ARGESIM C13: Crane and Embedded Control.

SNE 16(1), 2006, 27-29. https://www.sne-journal.org/benchmarks/c13/definition/c13-crane-and-embedded-control-revised-definition
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, SolverStats, Vector
from ..runtime import solve_ivp

C13_INITIAL_STATE: Vector = (0.0, 0.0, 0.0, 0.0, 0.0)


@dataclass(frozen=True)
class C13Parameters:
    mc: float = 10.0
    ml: float = 100.0
    r: float = 5.0
    g: float = 9.81
    dc: float = 0.5
    dcBrake: float = 100000.0
    dl: float = 0.001

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(value) or value <= 0.0
            for value in (self.mc, self.ml, self.r, self.g, self.dc, self.dcBrake, self.dl)
        ):
            raise ValueError("C13 parameters must be positive and finite")


_C13_DEFAULT_PARAMETERS = C13Parameters()


@dataclass(frozen=True)
class C13ControlledStudy:
    """Controlled C13 trajectory including all quantities requested by the tasks."""

    result: IntegrationResult
    load_position: tuple[float, ...]
    brake_active: tuple[bool, ...]
    emergency_stop: tuple[bool, ...]


def c13_linear_rhs(
    parameters: C13Parameters = _C13_DEFAULT_PARAMETERS,
    fc_desired: float = 0.0,
    fd: float = 0.0,
) -> Rhs:
    """Return the explicit continuous rate equations for the linear model."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        _xc, xc_dot, alpha, alpha_dot, current_fc = state

        fc_dot = -4.0 * (current_fc - fc_desired)

        xc_ddot = (
            (current_fc / parameters.mc)
            + (parameters.g * parameters.ml * alpha / parameters.mc)
            - (parameters.dc * xc_dot / parameters.mc)
        )

        alpha_ddot = (
            -parameters.g * (1.0 + parameters.ml / parameters.mc) * alpha
            + (parameters.dc / parameters.mc - parameters.dl / parameters.ml) * xc_dot
            - parameters.r * (parameters.dl / parameters.ml) * alpha_dot
            - (current_fc / parameters.mc)
            + (fd / parameters.ml)
        ) / parameters.r

        return (xc_dot, xc_ddot, alpha_dot, alpha_ddot, fc_dot)

    return rhs


def c13_nonlinear_rhs(
    parameters: C13Parameters = _C13_DEFAULT_PARAMETERS,
    fc_desired: float = 0.0,
    fd: float = 0.0,
    dc_current: float | None = None,
) -> Rhs:
    """Return the explicit continuous rate equations for the nonlinear model."""

    dc = dc_current if dc_current is not None else parameters.dc

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        _xc, xc_dot, alpha, alpha_dot, current_fc = state

        fc_dot = -4.0 * (current_fc - fc_desired)

        sin_a = math.sin(alpha)
        cos_a = math.cos(alpha)
        sin_a2 = sin_a**2

        M_xc = parameters.mc + parameters.ml * sin_a2

        xc_ddot = (
            -dc * xc_dot
            + current_fc
            + fd * sin_a2
            + parameters.ml
            * sin_a
            * (parameters.r * alpha_dot**2 + parameters.g * cos_a)
            - parameters.dl * xc_dot * sin_a2
        ) / M_xc

        M_alpha = (parameters.r**2) * (parameters.mc + parameters.ml * sin_a2)

        alpha_ddot = (
            (fd * parameters.mc / parameters.ml - current_fc + dc * xc_dot)
            * parameters.r
            * cos_a
            - (
                parameters.g * (parameters.mc + parameters.ml)
                + parameters.ml * parameters.r * (alpha_dot**2) * cos_a
            )
            * parameters.r
            * sin_a
            - parameters.dl
            * (
                parameters.mc
                / parameters.ml
                * (xc_dot * parameters.r * cos_a + (parameters.r**2) * alpha_dot)
                + (parameters.r**2) * alpha_dot * sin_a2
            )
        ) / M_alpha

        return (xc_dot, xc_ddot, alpha_dot, alpha_ddot, fc_dot)

    return rhs


def solve_c13_task_a(fd_dist: float) -> dict[str, float]:
    """Solve task A, returning the steady state position of the load."""

    if not math.isfinite(float(fd_dist)):
        raise ValueError("fd_dist must be finite")

    def get_segments():
        return [
            (0.0, 4.0, 0.0, 160.0),
            (4.0, 7.0, fd_dist, 160.0),
            (7.0, 15.0, 0.0, 160.0),
            # Instead of a hardcoded 2000s integration, we should ideally use a root finder
            # to determine the steady state (dx/dt == 0). Here we integrate up to 2000
            # or until steady state is reached.
            (15.0, 2000.0, 0.0, 0.0),
        ]

    def integrate_model(rhs_func) -> Vector:
        state = C13_INITIAL_STATE
        for t0, t1, fd, fc_desired in get_segments():
            prob = InitialValueProblem(
                rhs_func(_C13_DEFAULT_PARAMETERS, fd=fd, fc_desired=fc_desired),
                t0,
                state,
                t1,
                name="ARGESIM-C13-task-a",
            )
            res = solve_ivp(prob, "rk45", options={"max_step": 1.0})
            state = res.final_state
        return state

    lin_state = integrate_model(c13_linear_rhs)
    nonlin_state = integrate_model(c13_nonlinear_rhs)

    return {
        "linear": lin_state[0] + _C13_DEFAULT_PARAMETERS.r * lin_state[2],
        "nonlinear": nonlin_state[0]
        + _C13_DEFAULT_PARAMETERS.r * math.sin(nonlin_state[2]),
    }


def c13_task_a() -> dict[float, dict[str, float]]:
    """Compute the steady-state load position for three disturbance values."""
    return {dist: solve_c13_task_a(dist) for dist in (-750.0, -800.0, -850.0)}


def _vec_add(v1: Sequence[float], v2: Sequence[float]) -> tuple[float, ...]:
    return tuple(x + y for x, y in zip(v1, v2))


def _scalar_mul(s: float, v: Sequence[float]) -> tuple[float, ...]:
    return tuple(s * x for x in v)


def _dot_prod(v1: Sequence[float], v2: Sequence[float]) -> float:
    return sum(x * y for x, y in zip(v1, v2))


def _mat_vec(m: Sequence[Sequence[float]], v: Sequence[float]) -> tuple[float, ...]:
    return tuple(sum(row[j] * v[j] for j in range(len(v))) for row in m)


class C13Controller:
    """Discrete controller for C13 with 100 ms cycle time."""

    def __init__(self, with_diagnosis: bool = False):
        if not isinstance(with_diagnosis, bool):
            raise TypeError("with_diagnosis must be bool")
        self.with_diagnosis = with_diagnosis
        self.q = (0.0, 0.0, 0.0, 0.0, 0.0)
        self.fc_desired = 0.0
        self.brake_active = False
        self.emergency_mode = False
        self._small_force_cycles = 0

        self.V = 109.5
        self.ForceMax = 160.0
        self.BrakeCondition = 0.01
        self.dt = 0.1
        self.MaxPos = 5.0
        self.MinPos = -5.0
        self.BrakeTimeout = 3.0

        self.M = (
            (0.96, 0, 0, 0, 0),
            (0, 1, 0.01, 0, 0),
            (0.001, 0, 0.9995, 0.981, 0),
            (0, 0, 0, 1, 0),
            (-0.0002, 0, 0.0001, -0.2158, 1),
        )
        self.POS_C = (0, 1, 0, 0, 0)
        self.POS_D = (34.5724, 0.2395, 2.0322, 0.0164, -0.1979)
        self.POS_B = (0.04, 0, 0, 0, 0)
        self.POS_H = (2.9, 109.5, 286.0, 1790.6, 44.5)

        self.OBS_MAT = tuple(
            tuple(self.M[i][j] - self.POS_D[i] * self.POS_C[j] for j in range(5))
            for i in range(5)
        )

    @property
    def time_fc_small(self) -> float:
        return self._small_force_cycles * self.dt

    def step(self, pos_car: float, pos_desired: float, *, initial_sample: bool = False) -> None:
        """Update after one cycle, or at t=0 before any interval has elapsed."""
        if self.with_diagnosis and not self.MinPos <= pos_car <= self.MaxPos:
            self.emergency_mode = True
        if self.emergency_mode:
            self.brake_active = True
            self.fc_desired = 0.0
            return

        self.q = _vec_add(
            _vec_add(_mat_vec(self.OBS_MAT, self.q), _scalar_mul(pos_car, self.POS_D)),
            _scalar_mul(self.fc_desired, self.POS_B),
        )
        request = self.V * pos_desired - _dot_prod(self.POS_H, self.q)
        request = max(-self.ForceMax, min(request, self.ForceMax))
        # Count completed low-force intervals. A fresh demand releases the
        # holding brake even though the actuator was applying zero force.
        if (not initial_sample and abs(self.fc_desired) < self.BrakeCondition
                and abs(request) < self.BrakeCondition):
            self._small_force_cycles += 1
        else:
            self._small_force_cycles = 0
        self.brake_active = self.time_fc_small > self.BrakeTimeout
        self.fc_desired = 0.0 if self.brake_active else request


def solve_c13_task_b_c(
    with_diagnosis: bool = False,
    options: Mapping[str, object] | None = None,
) -> tuple[IntegrationResult, tuple[float, ...], tuple[bool, ...]]:
    """Compatibility adapter returning the historical Task-B/C tuple."""

    study = c13_controlled_study(
        with_diagnosis=with_diagnosis,
        options=options,
    )
    return study.result, study.load_position, study.brake_active


def _c13_disturbance_force(time: float, *, with_diagnosis: bool) -> float:
    """Return the revised C13 Task-B/C disturbance scenario."""

    if 42.0 <= time < 43.0:
        return -200.0
    if with_diagnosis and 46.0 <= time < 47.0:
        return 200.0
    return 0.0


def c13_controlled_study(
    *,
    with_diagnosis: bool,
    options: Mapping[str, object] | None = None,
) -> C13ControlledStudy:
    """Run Task B/C and retain the complete documented output surface."""

    controller = C13Controller(with_diagnosis=with_diagnosis)
    t_end = 60.0
    dt = controller.dt
    state = C13_INITIAL_STATE
    times = [0.0]
    states = [state]
    xl_traj = [state[0] + _C13_DEFAULT_PARAMETERS.r * math.sin(state[2])]
    brake_traj = []
    emergency_traj = []
    evals = accepted = rejected = 0

    for cycle in range(round(t_end / dt)):
        t = cycle * dt
        next_t = (cycle + 1) * dt
        if t >= 36.0:
            pos_desired = 3.8
        elif t >= 16.0:
            pos_desired = -0.5
        else:
            pos_desired = 3.0

        fd = _c13_disturbance_force(t, with_diagnosis=with_diagnosis)

        controller.step(state[0], pos_desired, initial_sample=(cycle == 0))
        brake_traj.append(controller.brake_active)
        emergency_traj.append(controller.emergency_mode)
        dc_val = (
            _C13_DEFAULT_PARAMETERS.dcBrake
            if controller.brake_active
            else _C13_DEFAULT_PARAMETERS.dc
        )
        rhs = c13_nonlinear_rhs(
            _C13_DEFAULT_PARAMETERS,
            fd=fd,
            fc_desired=controller.fc_desired,
            dc_current=dc_val,
        )
        prob = InitialValueProblem(
            rhs,
            t,
            state,
            next_t,
            name="ARGESIM-C13-controlled",
        )
        res = solve_ivp(
            prob,
            "rk45",
            options=options,
            defaults={
                "rk45": {
                    "max_step": min(0.01, dt),
                    "rtol": 1.0e-6,
                    "atol": 1.0e-9,
                }
            },
        )
        state = res.final_state
        evals += res.stats.rhs_evaluations
        accepted += res.stats.accepted_steps
        rejected += res.stats.rejected_steps
        times.append(next_t)
        states.append(state)
        xl_traj.append(state[0] + _C13_DEFAULT_PARAMETERS.r * math.sin(state[2]))

    # At the terminal observation the last actuator setting is still applied.
    brake_traj.append(controller.brake_active)
    emergency_traj.append(controller.emergency_mode)
    result = IntegrationResult(
        method="rk45-dormand-prince-5(4)",
        times=tuple(times),
        states=tuple(states),
        stats=SolverStats(accepted, rejected, evals),
    )
    return C13ControlledStudy(
        result=result,
        load_position=tuple(xl_traj),
        brake_active=tuple(brake_traj),
        emergency_stop=tuple(emergency_traj),
    )


def c13_task_b_study(
    options: Mapping[str, object] | None = None,
) -> C13ControlledStudy:
    """Run the complete controlled-system Task B output surface."""

    return c13_controlled_study(
        with_diagnosis=False,
        options=options,
    )


def c13_task_c_study(
    options: Mapping[str, object] | None = None,
) -> C13ControlledStudy:
    """Run the complete diagnosis Task C output surface."""

    return c13_controlled_study(
        with_diagnosis=True,
        options=options,
    )


def c13_task_b() -> IntegrationResult:
    """Run task B and return the historical integration-result API."""
    return c13_controlled_study(with_diagnosis=False).result


def c13_task_c() -> IntegrationResult:
    """Run task C and return the historical integration-result API."""
    return c13_controlled_study(with_diagnosis=True).result
