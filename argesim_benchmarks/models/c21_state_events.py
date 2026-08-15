"""ARGESIM C21: State Events and Structural-dynamic Systems.

The equations, parameters, and tasks follow the official C21 definition (SNE 26(2)).
"""

from __future__ import annotations

import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from ..hybrid import (
    HybridMode,
    HybridReset,
    HybridResult,
    StateEvent,
    simulate_hybrid,
)
from ..ivp import Rhs, Vector


@dataclass(frozen=True)
class C21BouncingBallParameters:
    """Parameters for the bouncing ball case study."""

    mu: float = 0.9
    beta: float = 0.002
    g: float = 9.81
    k: float = 1.0e6
    d: float = 500.0

    def __post_init__(self) -> None:
        values = (self.mu, self.beta, self.g, self.k, self.d)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("bouncing-ball parameters must be finite")
        if not 0.0 <= self.mu <= 1.0:
            raise ValueError("mu must be in [0, 1]")
        if self.beta < 0.0 or self.g <= 0.0 or self.k <= 0.0 or self.d <= 0.0:
            raise ValueError("beta must be non-negative; g, k, and d must be positive")


@dataclass(frozen=True)
class C21RLCDiodeParameters:
    """Parameters for the RLC circuit with diode case study."""

    r1: float = 1.0e3
    r2: float = 2.0e1
    l: float = 25.3e-6  # noqa: E741
    c: float = 100.0e-9
    i_s: float = 1.0e-8
    u_t: float = 26.0e-3
    f: float = 0.15e6

    def __post_init__(self) -> None:
        values = (self.r1, self.r2, self.l, self.c, self.i_s, self.u_t, self.f)
        if any(not math.isfinite(value) or value <= 0.0 for value in values):
            raise ValueError("RLC-diode parameters must be positive and finite")


@dataclass(frozen=True)
class C21RotatingPendulumParameters:
    """Parameters for the rotating pendulum case study."""

    m: float = 1.5
    k: float = 0.9
    l: float = 1.0  # noqa: E741
    g: float = 9.81

    def __post_init__(self) -> None:
        values = (self.m, self.k, self.l, self.g)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("rotating-pendulum parameters must be finite")
        if self.m <= 0.0 or self.l <= 0.0 or self.g <= 0.0 or self.k < 0.0:
            raise ValueError("m, l, and g must be positive; k must be non-negative")


def c21_bouncing_ball_event_contact(parameters: C21BouncingBallParameters) -> Rhs:
    """Return the RHS for the event contact bouncing ball model (free falling phase)."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        x, v = state
        return (
            v,
            -parameters.g - parameters.beta * v * abs(v),
        )

    return rhs


def c21_bouncing_ball_dynamic_contact_flying(parameters: C21BouncingBallParameters) -> Rhs:
    """Return the RHS for the dynamic contact model (free falling phase)."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        x, v, w = state
        return (
            v,
            -parameters.g - parameters.beta * v * abs(v),
            -(parameters.k / parameters.d) * w,
        )

    return rhs


def c21_bouncing_ball_dynamic_contact_contact(parameters: C21BouncingBallParameters) -> Rhs:
    """Return the RHS for the dynamic contact model (contact phase)."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        x, v, w = state
        f_c = -parameters.k * x - parameters.d * v
        return (
            v,
            -parameters.g + f_c,
            -v,
        )

    return rhs


def c21_bouncing_ball_h_b(state: Sequence[float]) -> float:
    """Event function for Bounce event (crosses 0 negatively)."""
    return state[0]


def c21_bouncing_ball_action_b(
    state: Sequence[float], parameters: C21BouncingBallParameters
) -> Vector:
    """Event action for Bounce event."""
    return (state[0], -parameters.mu * state[1])


def c21_bouncing_ball_h_c(state: Sequence[float]) -> float:
    """Event function for Contact event (crosses 0 negatively)."""
    return state[0] + state[2]


def c21_bouncing_ball_h_f(
    state: Sequence[float], parameters: C21BouncingBallParameters
) -> float:
    """Event function for Fly Restart event (crosses 0 negatively)."""
    x, v, _ = state
    return -parameters.k * x - parameters.d * v


def c21_rlc_diode_locking(
    parameters: C21RLCDiodeParameters, u0: Callable[[float], float]
) -> Rhs:
    """Return the RHS for the RLC circuit in locking phase (diode acts as open circuit)."""

    def rhs(time: float, state: Sequence[float]) -> Vector:
        i, u_c = state
        return (
            -parameters.r1 / parameters.l * i
            - parameters.r2 / parameters.l * i
            - 1.0 / parameters.l * u_c
            + 1.0 / parameters.l * u0(time),
            1.0 / parameters.c * i,
        )

    return rhs


def c21_rlc_diode_conducting_shortcut(
    parameters: C21RLCDiodeParameters, u0: Callable[[float], float]
) -> Rhs:
    """Return the RHS for the RLC circuit in conducting phase with shortcut diode model."""

    def rhs(time: float, state: Sequence[float]) -> Vector:
        i, u_c = state
        return (
            -parameters.r1 / parameters.l * i + 1.0 / parameters.l * u0(time),
            -1.0 / (parameters.r2 * parameters.c) * u_c,
        )

    return rhs


def c21_rlc_diode_conducting_explicit(
    parameters: C21RLCDiodeParameters, u0: Callable[[float], float]
) -> Rhs:
    """Return the RHS for the RLC circuit in conducting phase with explicit Shockley diode model."""

    def rhs(time: float, state: Sequence[float]) -> Vector:
        i, u_c, u_d = state

        # Calculate diode current using Shockley equation
        exponent = min(u_d / parameters.u_t, 700.0)  # Bound to avoid overflow
        i_d = parameters.i_s * (math.exp(exponent) - 1.0)

        du_c = 1.0 / parameters.c * (i + i_d)
        di = (
            -parameters.r1 / parameters.l * i
            - parameters.r2 / parameters.l * (i + i_d)
            - 1.0 / parameters.l * u_c
            + 1.0 / parameters.l * u0(time)
        )

        # Index-1 explicit reduction for u_d
        du_d = -du_c * (
            parameters.i_s
            * parameters.r2
            * (math.exp(exponent) / parameters.u_t)
            + 1.0
        ) ** -1

        return (di, du_c, du_d)

    return rhs


def c21_rlc_diode_h_c(
    state: Sequence[float], parameters: C21RLCDiodeParameters
) -> float:
    """Event function for Conducting Phase Start (crosses 0 positively)."""
    i, u_c = state[:2]
    return parameters.r2 * i + u_c


def c21_rlc_diode_h_l_shortcut(
    state: Sequence[float], parameters: C21RLCDiodeParameters
) -> float:
    """Event function for Locking Phase Start for shortcut diode (crosses 0 negatively)."""
    i, u_c = state[:2]
    return -(parameters.r2 * i + u_c)


def c21_rlc_diode_h_l_explicit(
    state: Sequence[float], parameters: C21RLCDiodeParameters
) -> float:
    """Event function for Locking Phase Start for explicit Shockley diode (crosses 0 negatively)."""
    i, u_c, u_d = state
    exponent = min(u_d / parameters.u_t, 700.0)
    i_d = parameters.i_s * (math.exp(exponent) - 1.0)
    return parameters.r2 * (i + i_d) + u_c


def c21_rotating_pendulum_swinging(parameters: C21RotatingPendulumParameters) -> Rhs:
    """Return the RHS for the rotating pendulum in swinging phase."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        phi, dphi = state
        return (
            dphi,
            -(parameters.k / parameters.m) * dphi
            - (parameters.g / parameters.l) * math.sin(phi),
        )

    return rhs


def c21_rotating_pendulum_falling(parameters: C21RotatingPendulumParameters) -> Rhs:
    """Return the RHS for the rotating pendulum in free falling phase."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        x, dx, y, dy = state
        return (
            dx,
            -(parameters.k / parameters.m) * dx,
            dy,
            -parameters.g - (parameters.k / parameters.m) * dy,
        )

    return rhs


def c21_rotating_pendulum_h_f(
    state: Sequence[float], parameters: C21RotatingPendulumParameters
) -> float:
    """Event function for Falling event (crosses 0 negatively)."""
    phi, dphi = state
    return (
        -math.cos(phi) * parameters.m * parameters.g
        + parameters.m * parameters.l * dphi**2
    )


def c21_rotating_pendulum_h_s(
    state: Sequence[float], parameters: C21RotatingPendulumParameters
) -> float:
    """Event function for Swinging event (crosses 0 positively)."""
    x, _, y, _ = state
    return x**2 + y**2 - parameters.l**2


def c21_rotating_pendulum_action_f(
    state: Sequence[float], parameters: C21RotatingPendulumParameters
) -> Vector:
    """Event action for Falling event (convert polar to cartesian)."""
    phi, dphi = state
    x = parameters.l * math.sin(phi)
    y = -parameters.l * math.cos(phi)
    dx = parameters.l * dphi * math.cos(phi)
    dy = parameters.l * dphi * math.sin(phi)
    return (x, dx, y, dy)


def c21_rotating_pendulum_action_s(
    state: Sequence[float], parameters: C21RotatingPendulumParameters
) -> Vector:
    """Event action for Swinging event (convert cartesian to polar)."""
    x, dx, y, dy = state
    phi = math.atan2(x, -y)
    dphi = (dx * math.cos(phi) + dy * math.sin(phi)) / parameters.l
    return (phi, dphi)


def simulate_c21_bouncing_ball_event_contact(
    parameters: C21BouncingBallParameters = C21BouncingBallParameters(),
    initial_state: Sequence[float] = (10.0, 0.0),
    t_bound: float = 30.0,
    max_bounces: int = 100,
    *,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
    settle_velocity: float = 1.0e-3,
) -> HybridResult:
    """Run the event-contact ball with a classical or quantized backend."""

    if not isinstance(max_bounces, int) or isinstance(max_bounces, bool):
        raise TypeError("max_bounces must be an integer")
    if max_bounces <= 0:
        raise ValueError("max_bounces must be positive")
    if not math.isfinite(settle_velocity) or settle_velocity <= 0.0:
        raise ValueError("settle_velocity must be positive and finite")
    state = tuple(float(value) for value in initial_state)
    if len(state) != 2 or state[0] < 0.0:
        raise ValueError("initial_state must be a non-negative height and velocity")

    def height(_time: float, values: Sequence[float]) -> float:
        return float(values[0])

    def bounce(_time: float, values: Sequence[float]) -> Vector | HybridReset:
        rebound = -parameters.mu * float(values[1])
        if rebound <= settle_velocity:
            return HybridReset((0.0, 0.0), mode="rest")
        return (0.0, rebound)

    def rest(_time: float, _values: Sequence[float]) -> Vector:
        return (0.0, 0.0)

    modes = {
        "flight": HybridMode(
            "flight",
            c21_bouncing_ball_event_contact(parameters),
            (StateEvent("bounce", height, bounce, "flight", -1),),
        ),
        "rest": HybridMode("rest", rest),
    }
    defaults = {
        "euler": {"step": 1.0e-3},
        "rk4": {"step": 1.0e-3},
        "rk45": {"rtol": 1.0e-8, "atol": 1.0e-10, "max_step": 1.0e-2},
        "qss1": {"quantum": (1.0e-4, 1.0e-3)},
        "qss2": {"quantum": (1.0e-4, 1.0e-3)},
    }
    initial_mode = "rest" if state == (0.0, 0.0) else "flight"
    return simulate_hybrid(
        modes,
        initial_mode=initial_mode,
        initial_state=state,
        t_bound=t_bound,
        method=method,
        solver_options=options,
        solver_defaults=defaults,
        max_events=max_bounces,
    )


def solve_c21_bouncing_ball_event_contact(
    parameters: C21BouncingBallParameters = C21BouncingBallParameters(),
    initial_state: Sequence[float] = (10.0, 0.0),
    t_bound: float = 30.0,
    max_bounces: int = 100,
    *,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
) -> tuple[list[float], list[Vector]]:
    """Compatibility wrapper returning the shared hybrid trajectory arrays."""

    result = simulate_c21_bouncing_ball_event_contact(
        parameters,
        initial_state,
        t_bound,
        max_bounces,
        method=method,
        options=options,
    )
    return list(result.times), list(result.states)


def simulate_c21_rotating_pendulum(
    parameters: C21RotatingPendulumParameters = C21RotatingPendulumParameters(),
    initial_state: Sequence[float] = (math.pi / 4.0, 15.0),  # phi, dphi
    t_bound: float = 5.0,
    *,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
) -> HybridResult:
    """Run the structural-dynamic pendulum with dimension-changing events."""

    state = tuple(float(value) for value in initial_state)
    if len(state) != 2:
        raise ValueError("rotating-pendulum initial_state must contain phi and dphi")

    def fall_guard(_time: float, values: Sequence[float]) -> float:
        return c21_rotating_pendulum_h_f(values, parameters)

    def swing_guard(_time: float, values: Sequence[float]) -> float:
        return c21_rotating_pendulum_h_s(values, parameters)

    def fall_reset(_time: float, values: Sequence[float]) -> Vector:
        return c21_rotating_pendulum_action_f(values, parameters)

    def swing_reset(_time: float, values: Sequence[float]) -> Vector:
        return c21_rotating_pendulum_action_s(values, parameters)

    modes = {
        "swinging": HybridMode(
            "swinging",
            c21_rotating_pendulum_swinging(parameters),
            (StateEvent("fall", fall_guard, fall_reset, "falling", -1),),
        ),
        "falling": HybridMode(
            "falling",
            c21_rotating_pendulum_falling(parameters),
            (StateEvent("catch", swing_guard, swing_reset, "swinging", 1),),
        ),
    }
    defaults = {
        "euler": {"step": 1.0e-3},
        "rk4": {"step": 1.0e-3},
        "rk45": {"rtol": 1.0e-8, "atol": 1.0e-10, "max_step": 1.0e-3},
        "qss1": {"quantum": 1.0e-4},
        "qss2": {"quantum": 1.0e-4},
    }
    return simulate_hybrid(
        modes,
        initial_mode="swinging",
        initial_state=state,
        t_bound=t_bound,
        method=method,
        solver_options=options,
        solver_defaults=defaults,
        max_events=1_000,
    )


def solve_c21_rotating_pendulum(
    parameters: C21RotatingPendulumParameters = C21RotatingPendulumParameters(),
    initial_state: Sequence[float] = (math.pi / 4.0, 15.0),
    t_bound: float = 5.0,
    *,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
) -> tuple[list[float], list[Vector]]:
    """Compatibility wrapper returning the shared hybrid trajectory arrays."""

    result = simulate_c21_rotating_pendulum(
        parameters,
        initial_state,
        t_bound,
        method=method,
        options=options,
    )
    return list(result.times), list(result.states)


def c21_task_bouncing_ball() -> dict[str, float]:
    """Execute the bouncing ball task and return final time to indicate success."""
    times, _states = solve_c21_bouncing_ball_event_contact()
    return {"final_time": times[-1]}


def c21_task_qss1_bouncing_ball() -> dict[str, float]:
    """Execute the bouncing ball with QSS1 and the same state-event layer."""

    result = simulate_c21_bouncing_ball_event_contact(
        t_bound=2.0,
        method="qss1",
        options={"quantum": (1.0e-3, 1.0e-3)},
    )
    return {"final_time": result.final_time, "events": float(len(result.events))}


def c21_task_qss2_bouncing_ball() -> dict[str, float]:
    """Execute the bouncing ball with QSS2 and shared event localization."""

    result = simulate_c21_bouncing_ball_event_contact(
        t_bound=2.0,
        method="qss2",
        options={"quantum": (1.0e-3, 1.0e-3)},
    )
    return {"final_time": result.final_time, "events": float(len(result.events))}


def c21_task_rotating_pendulum() -> dict[str, float]:
    """Execute the rotating pendulum task and return final time to indicate success."""
    times, _states = solve_c21_rotating_pendulum()
    return {"final_time": times[-1]}


def c21_task_rlc_diode() -> dict[str, float]:
    """Refuse to report success for the not-yet-complete RLC/DAE task."""

    raise NotImplementedError("C21 RLC-diode task requires the complete DAE modes")
