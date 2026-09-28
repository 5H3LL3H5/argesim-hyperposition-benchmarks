"""ARGESIM C07: Constrained Pendulum.

The equations, parameters, initial values and tasks follow the official
C07 definition. State order is ``(phi, phi_dot)``.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..hybrid import HybridMode, StateEvent, simulate_hybrid
from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector


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
        values = (self.m, self.l, self.l_p, self.g, self.d, self.phi_p)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("C07 parameters must be finite")
        if self.l_p >= self.l or self.l_p < 0.0:
            raise ValueError("l_p must be in [0, l)")
        if self.m <= 0.0 or self.l <= 0.0 or self.g <= 0.0:
            raise ValueError("m, l, and g must be positive")
        if self.d < 0.0:
            raise ValueError("d must be non-negative")
        if not isinstance(self.linear, bool):
            raise TypeError("linear must be bool")

    @property
    def l_s(self) -> float:
        return self.l - self.l_p


_C07_DEFAULT_PARAMETERS = C07Parameters()


def c07_rhs(parameters: C07Parameters = _C07_DEFAULT_PARAMETERS) -> Rhs:
    """Return a pointwise branch evaluator, without transition/reset logic.

    Use :func:`solve_c07` for trajectories that can cross the pin. The hybrid
    solver keeps each branch fixed until the localized state event.
    """

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


def _c07_mode_rhs(parameters: C07Parameters, length: float) -> Rhs:
    """Return one fixed-constraint mode; event handling selects the length."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        phi, phi_dot = state
        angle = phi if parameters.linear else math.sin(phi)
        return (
            phi_dot,
            -(parameters.g / length) * angle - (parameters.d / parameters.m) * phi_dot,
        )

    return rhs


def c07_problem(
    *,
    parameters: C07Parameters = _C07_DEFAULT_PARAMETERS,
    initial_state: Sequence[float],
    t_bound: float = 10.0,
    mode: str | None = None,
) -> InitialValueProblem:
    """Build one fixed-mode C07 segment, stopping conceptually at its event."""

    state = tuple(float(value) for value in initial_state)
    if len(state) != 2:
        raise ValueError("C07 initial_state must contain phi and phi_dot")
    selected_mode = mode
    if selected_mode is None:
        selected_mode = (
            "long"
            if state[0] > parameters.phi_p
            or (state[0] == parameters.phi_p and state[1] >= 0.0)
            else "short"
        )
    if selected_mode not in {"long", "short"}:
        raise ValueError("C07 mode must be 'long' or 'short'")
    length = parameters.l if selected_mode == "long" else parameters.l_s

    return InitialValueProblem(
        _c07_mode_rhs(parameters, length),
        0.0,
        state,
        t_bound,
        name=f"ARGESIM-C07-constrained-pendulum-{selected_mode}",
        autonomous=True,
    )


def solve_c07(
    *,
    parameters: C07Parameters = _C07_DEFAULT_PARAMETERS,
    initial_state: Sequence[float],
    t_bound: float = 10.0,
    max_step: float = 1.0e-2,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Solve C07 through the shared hybrid runtime using RK or QSS backends."""

    state = tuple(float(value) for value in initial_state)
    if len(state) != 2:
        raise ValueError("C07 initial_state must contain phi and phi_dot")

    def pin_guard(_time: float, values: Sequence[float]) -> float:
        return float(values[0]) - parameters.phi_p

    def hit_pin(_time: float, values: Sequence[float]) -> Vector:
        return (parameters.phi_p, float(values[1]) * parameters.l / parameters.l_s)

    def release_pin(_time: float, values: Sequence[float]) -> Vector:
        return (parameters.phi_p, float(values[1]) * parameters.l_s / parameters.l)

    modes = {
        "long": HybridMode(
            "long",
            _c07_mode_rhs(parameters, parameters.l),
            (StateEvent("hit-pin", pin_guard, hit_pin, "short", -1),),
        ),
        "short": HybridMode(
            "short",
            _c07_mode_rhs(parameters, parameters.l_s),
            (StateEvent("release-pin", pin_guard, release_pin, "long", 1),),
        ),
    }
    initial_mode = (
        "long"
        if state[0] > parameters.phi_p
        or (state[0] == parameters.phi_p and state[1] >= 0.0)
        else "short"
    )
    defaults = {
        "euler": {"step": max_step},
        "rk4": {"step": max_step},
        "rk45": {"rtol": 1.0e-8, "atol": 1.0e-10, "max_step": max_step},
        "qss1": {"quantum": (1.0e-4, 1.0e-3)},
        "qss2": {"quantum": (1.0e-4, 1.0e-3)},
    }
    result = simulate_hybrid(
        modes,
        initial_mode=initial_mode,
        initial_state=state,
        t_bound=t_bound,
        method=method,
        solver_options=options,
        solver_defaults=defaults,
        max_events=10_000,
    )
    return IntegrationResult(result.method, result.times, result.states, result.stats)


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
        minimum = min(state[0] for state in res.states)
        # The turning point normally falls between solver samples. Interpolate
        # the zero of angular velocity on that smooth, fixed-mode segment.
        for (t0, s0), (t1, s1) in zip(
            zip(res.times, res.states), zip(res.times[1:], res.states[1:])
        ):
            if s0[1] >= 0.0 or s1[1] <= 0.0:
                continue
            dt = t1 - t0
            if dt <= 0.0:
                continue
            # Cubic Hermite position uses both endpoint angles and velocities.
            # Its derivative has opposite signs at the endpoints here.
            def slope(u: float) -> float:
                return ((6*u*u - 6*u) * (s0[0] - s1[0])
                        + (3*u*u - 4*u + 1) * dt * s0[1]
                        + (3*u*u - 2*u) * dt * s1[1])

            left, right = 0.0, 1.0
            for _ in range(40):
                middle = (left + right) / 2
                if slope(middle) < 0:
                    left = middle
                else:
                    right = middle
            u = (left + right) / 2
            angle = ((2*u**3 - 3*u*u + 1) * s0[0]
                     + (u**3 - 2*u*u + u) * dt * s0[1]
                     + (-2*u**3 + 3*u*u) * s1[0]
                     + (u**3 - u*u) * dt * s1[1])
            minimum = min(minimum, angle)
        return minimum

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
