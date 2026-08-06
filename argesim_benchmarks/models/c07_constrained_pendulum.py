"""ARGESIM C07: Constrained Pendulum.

The equations, parameters, initial values and tasks follow the official
C07 definition. State order is ``(phi, phi_dot)``.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ..ivp import InitialValueProblem, IntegrationError, IntegrationResult, Rhs, SolverStats, Vector
from ..solvers import rk45


@dataclass(frozen=True)
class C07Parameters:
    """Parameters in the notation of the official C07 definition."""

    m: float = 1.02
    l: float = 1.0  # noqa: E741
    l_p: float = 0.7
    g: float = 9.81
    d: float = 0.2
    phi_p: float = -math.pi / 12.0
    linear: bool = False

    def __post_init__(self) -> None:
        if self.l_p >= self.l or self.l_p < 0.0:
            raise ValueError("l_p must be in [0, l)")
        if self.m <= 0.0 or self.l <= 0.0:
            raise ValueError("m and l must be positive")

    @property
    def l_s(self) -> float:
        return self.l - self.l_p


_C07_DEFAULT_PARAMETERS = C07Parameters()


def c07_rhs(parameters: C07Parameters = _C07_DEFAULT_PARAMETERS) -> Rhs:
    """Return the rate equations. Does not include event logic."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        phi, phi_dot = state
        if phi > parameters.phi_p or (phi == parameters.phi_p and phi_dot >= 0):
            l_eff = parameters.l
        else:
            l_eff = parameters.l_s

        # Damping is often specified as angular damping where M = d * phi_dot.
        # Original: m * l * phi'' = -m * g * sin(phi) - d * l * phi'
        # Division by (m * l) yields: phi'' = -(g/l) * sin(phi) - (d/m) * phi'
        # Which is exactly what the code below evaluates to.
        damping = parameters.d * l_eff * phi_dot
        if parameters.linear:
            gravity = parameters.m * parameters.g * phi
        else:
            gravity = parameters.m * parameters.g * math.sin(phi)

        phi_ddot = -(gravity + damping) / (parameters.m * l_eff)
        return (phi_dot, phi_ddot)

    return rhs


def c07_problem(
    *,
    parameters: C07Parameters = _C07_DEFAULT_PARAMETERS,
    initial_state: Sequence[float],
    t_bound: float = 10.0,
) -> InitialValueProblem:
    """Build the C07 initial-value problem."""

    return InitialValueProblem(
        c07_rhs(parameters),
        0.0,
        initial_state,
        t_bound,
        name="ARGESIM-C07-constrained-pendulum",
        autonomous=True,
    )


def solve_c07(
    *,
    parameters: C07Parameters = _C07_DEFAULT_PARAMETERS,
    initial_state: Sequence[float],
    t_bound: float = 10.0,
    max_step: float = 1.0e-2,
) -> IntegrationResult:
    """Solve C07 with rk45, handling state events explicitly."""

    t = 0.0
    state = tuple(float(x) for x in initial_state)

    times = [t]
    states = [state]

    accepted = 0
    rejected = 0
    evals = 0

    while t < t_bound:
        step_bound = min(t + max_step, t_bound)
        phi_current = state[0]

        prob = InitialValueProblem(
            c07_rhs(parameters),
            t,
            state,
            step_bound,
            autonomous=True
        )

        res = rk45(prob, max_step=max_step)

        accepted += res.stats.accepted_steps
        rejected += res.stats.rejected_steps
        evals += res.stats.rhs_evaluations

        cross_index = -1


        crossing_direction = 0 # -1 for down, 1 for up

        for i in range(1, len(res.times)):
            phi_next = res.states[i][0]
            if phi_current > parameters.phi_p >= phi_next:
                cross_index = i
                crossing_direction = -1
                break
            elif phi_current < parameters.phi_p <= phi_next:
                cross_index = i
                crossing_direction = 1
                break
            phi_current = phi_next

        if cross_index != -1:
            t_left = res.times[cross_index - 1]
            t_right = res.times[cross_index]
            y_left = res.states[cross_index - 1]
            y_right = res.states[cross_index]

            # Simple bisection for root
            for _ in range(30):
                t_mid = (t_left + t_right) / 2.0
                if t_mid == t_left or t_mid == t_right:
                    break

                # Check step size before calling rk45 to avoid IntegrationError min_step
                step_size = t_mid - t_left
                if step_size < 1e-13:
                    break

                prob_mid = InitialValueProblem(
                    c07_rhs(parameters),
                    t_left,
                    y_left,
                    t_mid,
                    autonomous=True
                )
                try:
                    res_mid = rk45(prob_mid, max_step=step_size)
                    y_mid = res_mid.final_state
                    accepted += res_mid.stats.accepted_steps
                    rejected += res_mid.stats.rejected_steps
                    evals += res_mid.stats.rhs_evaluations
                except IntegrationError:
                    # If it fails due to min step or whatever, we just assume root is here
                    break

                if (crossing_direction == -1 and y_mid[0] > parameters.phi_p) or \
                   (crossing_direction == 1 and y_mid[0] < parameters.phi_p):
                    t_left = t_mid
                    y_left = y_mid
                else:
                    t_right = t_mid
                    y_right = y_mid

            t_event = t_right

            # Append trajectory up to event
            if t_event > t:
                step_size = t_event - t
                if step_size > 1e-13:
                    prob_event = InitialValueProblem(
                        c07_rhs(parameters),
                        t,
                        state,
                        t_event,
                        autonomous=True
                    )
                    try:
                        res_event = rk45(prob_event, max_step=max_step)
                        accepted += res_event.stats.accepted_steps
                        rejected += res_event.stats.rejected_steps
                        evals += res_event.stats.rhs_evaluations

                        for i in range(1, len(res_event.times)):
                            times.append(res_event.times[i])
                            states.append(res_event.states[i])

                        phi, phi_dot = res_event.final_state
                    except IntegrationError:
                        phi, phi_dot = y_right
                else:
                    phi, phi_dot = y_right
            else:
                phi, phi_dot = y_right

            if crossing_direction == -1:
                # Hits the pin
                new_phi_dot = phi_dot * (parameters.l / parameters.l_s)
                new_phi = parameters.phi_p
            else:
                # Releases from the pin
                new_phi_dot = phi_dot * (parameters.l_s / parameters.l)
                new_phi = parameters.phi_p

            state = (new_phi, new_phi_dot)
            t = t_event

            times.append(t)
            states.append(state)

        else:
            for i in range(1, len(res.times)):
                times.append(res.times[i])
                states.append(res.states[i])
            t = res.final_time
            state = res.final_state

    return IntegrationResult(
        "rk45-hybrid",
        tuple(times),
        tuple(states),
        SolverStats(accepted, rejected, evals),
    )


def c07_task_a() -> dict[str, IntegrationResult]:
    """Simulate task A i and ii."""

    res_i = solve_c07(
        parameters=C07Parameters(d=0.2, phi_p=-math.pi/12.0),
        initial_state=(math.pi/6.0, 0.0),
        t_bound=10.0,
    )

    res_ii = solve_c07(
        parameters=C07Parameters(d=0.1, phi_p=-math.pi/12.0),
        initial_state=(-math.pi/6.0, 0.0),
        t_bound=10.0,
    )

    return {
        "task_a_i": res_i,
        "task_a_ii": res_ii,
    }


def c07_task_b() -> dict[str, IntegrationResult]:
    """Simulate task B, linear vs nonlinear."""

    params_nl = C07Parameters(d=0.2, phi_p=-math.pi/24.0, linear=False)
    params_l = C07Parameters(d=0.2, phi_p=-math.pi/24.0, linear=True)

    initial_state = (math.pi/12.0, 0.0)

    res_nl = solve_c07(
        parameters=params_nl,
        initial_state=initial_state,
        t_bound=10.0,
    )

    res_l = solve_c07(
        parameters=params_l,
        initial_state=initial_state,
        t_bound=10.0,
    )

    return {
        "task_b_nonlinear": res_nl,
        "task_b_linear": res_l,
    }


def c07_task_c() -> float:
    """Determine initial angular velocity for task C.

    Returns the initial angular velocity phi_dot_0 such that the maximum
    angle of the shortened pendulum reaches exactly -pi/2.
    """

    params = C07Parameters(d=0.2, phi_p=-math.pi/12.0)

    def simulate_max_angle(phi_dot_0: float) -> float:
        res = solve_c07(
            parameters=params,
            initial_state=(math.pi/6.0, phi_dot_0),
            t_bound=10.0,
        )
        return min(s[0] for s in res.states)

    v_left = -10.0
    v_right = 0.0

    tol = 1e-9
    for _ in range(100):
        if abs(v_right - v_left) < tol:
            break
        v_mid = (v_left + v_right) / 2.0
        min_phi = simulate_max_angle(v_mid)
        if min_phi > -math.pi/2.0:
            v_right = v_mid
        else:
            v_left = v_mid

    return (v_left + v_right) / 2.0
