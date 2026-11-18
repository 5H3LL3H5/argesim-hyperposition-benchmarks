"""ARGESIM C21: State Events and Structural-dynamic Systems.

The equations, parameters, and tasks follow the official C21 definition (SNE 26(2)).
"""

from __future__ import annotations

import itertools
import math
import time
from bisect import bisect_left
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from ..hybrid import (
    HybridMode,
    HybridReset,
    HybridResult,
    StateEvent,
    simulate_hybrid,
)
from ..ivp import IntegrationError, Rhs, Vector


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
    l: float = 25.3e-6
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
    l: float = 1.0
    g: float = 9.81

    def __post_init__(self) -> None:
        values = (self.m, self.k, self.l, self.g)
        if any(not math.isfinite(value) for value in values):
            raise ValueError("rotating-pendulum parameters must be finite")
        if self.m <= 0.0 or self.l <= 0.0 or self.g <= 0.0 or self.k < 0.0:
            raise ValueError("m, l, and g must be positive; k must be non-negative")


@dataclass(frozen=True)
class C21PendulumBasicStudy:
    """Basic run stopped at the first sufficiently small oscillation."""

    result: HybridResult
    stop_time: float
    published_stop_time: float = 7.5962714

    @property
    def absolute_error(self) -> float:
        return abs(self.stop_time - self.published_stop_time)


@dataclass(frozen=True)
class C21KickStudyEntry:
    """One externally validated kick-factor target."""

    label: str
    terminal_angle: float
    terminal_velocity: float
    required_velocity: float
    kick_factor: float
    published_kick_factor: float

    @property
    def absolute_error(self) -> float:
        return abs(self.kick_factor - self.published_kick_factor)


@dataclass(frozen=True)
class C21KickStudy:
    """Published three-case external-energy study."""

    pre_kick_velocity: float
    entries: tuple[C21KickStudyEntry, ...]


@dataclass(frozen=True)
class C21EventContactStudy:
    """Linear/nonlinear Zeno limits and velocity compensation."""

    linear_limit: float
    nonlinear_limit: float
    compensating_velocity: float
    published_nonlinear_limit: float = 25.589465
    published_compensating_velocity: float = 4.39563


@dataclass(frozen=True)
class C21DynamicContactStudy:
    """Contact/flight extrema with published reference sequences."""

    result: HybridResult
    maximum_heights: tuple[float, ...]
    maximum_deformations: tuple[float, ...]
    published_heights: tuple[float, ...]
    published_deformations: tuple[float, ...]

    @property
    def maximum_height_error(self) -> float:
        return max(
            (
                abs(value - reference)
                for value, reference in zip(
                    self.maximum_heights, self.published_heights
                )
            ),
            default=0.0,
        )

    @property
    def maximum_deformation_error(self) -> float:
        return max(
            (
                abs(value - reference)
                for value, reference in zip(
                    self.maximum_deformations, self.published_deformations
                )
            ),
            default=0.0,
        )


@dataclass(frozen=True)
class C21DynamicParameterRun:
    """One executable stiffness/damping/gravity parameter case."""

    label: str
    parameters: C21BouncingBallParameters
    result: HybridResult


def c21_bouncing_ball_event_contact(parameters: C21BouncingBallParameters) -> Rhs:
    """Return the RHS for the event contact bouncing ball model (free falling phase)."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        _x, v = state
        return (
            v,
            -parameters.g - parameters.beta * v * abs(v),
        )

    return rhs


def c21_bouncing_ball_dynamic_contact_flying(parameters: C21BouncingBallParameters) -> Rhs:
    """Return the RHS for the dynamic contact model (free falling phase)."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        _x, v, w = state
        return (
            v,
            -parameters.g - parameters.beta * v * abs(v),
            -(parameters.k / parameters.d) * w,
        )

    return rhs


def c21_bouncing_ball_dynamic_contact_contact(parameters: C21BouncingBallParameters) -> Rhs:
    """Return the RHS for the dynamic contact model (contact phase)."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        x, v, _w = state
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

        # Differentiate the index-1 algebraic constraint
        # u_d = R2 * (i + i_d(u_d)) + u_c.
        diode_conductance = (
            parameters.i_s * math.exp(exponent) / parameters.u_t
        )
        denominator = 1.0 - parameters.r2 * diode_conductance
        if abs(denominator) < 1.0e-12:
            raise IntegrationError("explicit Shockley reduction reached its fold")
        du_d = (parameters.r2 * di + du_c) / denominator

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
    del parameters
    return float(state[2])


def c21_rotating_pendulum_swinging(parameters: C21RotatingPendulumParameters) -> Rhs:
    """Return the RHS for the rotating pendulum in swinging phase."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        phi, dphi = state
        return (
            dphi,
            -(parameters.k / parameters.m) * dphi
            + (parameters.g / parameters.l) * math.sin(phi),
        )

    return rhs


def c21_rotating_pendulum_falling(parameters: C21RotatingPendulumParameters) -> Rhs:
    """Return the RHS for the rotating pendulum in free falling phase."""

    def rhs(_time: float, state: Sequence[float]) -> Vector:
        _x, dx, _y, dy = state
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
    y = parameters.l * math.cos(phi)
    dx = parameters.l * dphi * math.cos(phi)
    dy = -parameters.l * dphi * math.sin(phi)
    return (x, dx, y, dy)


def c21_rotating_pendulum_action_s(
    state: Sequence[float], parameters: C21RotatingPendulumParameters
) -> Vector:
    """Event action for Swinging event (convert cartesian to polar)."""
    x, dx, y, dy = state
    phi = math.atan2(x, y)
    dphi = (dx * math.cos(phi) - dy * math.sin(phi)) / parameters.l
    return (phi, dphi)


def c21_rotating_pendulum_bottom_angle(phi: float) -> float:
    """Return the angle from the lower equilibrium in ``[-pi, pi)``."""

    value = float(phi)
    if not math.isfinite(value):
        raise ValueError("phi must be finite")
    return (value % (2.0 * math.pi)) - math.pi


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
    if len(state) != 2 or any(not math.isfinite(value) for value in state) or state[0] < 0.0:
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


def c21_analytical_bounce_times(
    count: int,
    *,
    initial_height: float = 10.0,
    gravity: float = 9.81,
    restitution: float = 0.9,
) -> tuple[float, ...]:
    """Return Equation-15 impact times for the linear event-contact model."""

    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        raise ValueError("count must be a positive integer")
    if (
        not math.isfinite(initial_height)
        or not math.isfinite(gravity)
        or not math.isfinite(restitution)
        or initial_height <= 0.0
        or gravity <= 0.0
        or not 0.0 <= restitution < 1.0
    ):
        raise ValueError("invalid analytical bouncing-ball parameters")
    first = math.sqrt(2.0 * initial_height / gravity)
    geometric = 0.0
    result = []
    for index in range(count):
        geometric += restitution**index
        result.append(first * (-1.0 + 2.0 * geometric))
    return tuple(result)


def c21_last_bounce_time(
    *,
    initial_height: float = 10.0,
    gravity: float = 9.81,
    restitution: float = 0.9,
) -> float:
    """Return the finite Zeno limit from Equation 16."""

    c21_analytical_bounce_times(
        1,
        initial_height=initial_height,
        gravity=gravity,
        restitution=restitution,
    )
    return math.sqrt(2.0 * initial_height / gravity) * (
        (1.0 + restitution) / (1.0 - restitution)
    )


def c21_event_contact_limit_time(
    parameters: C21BouncingBallParameters = C21BouncingBallParameters(),
    *,
    initial_height: float = 10.0,
    initial_velocity: float = 0.0,
    tolerance: float = 1.0e-14,
) -> float:
    """Return the Zeno-time limit using exact free-flight segments.

    The nonlinear branch integrates the quadratic-drag ascent and descent in
    closed form, then sums rebound flights until their duration is negligible.
    Benchmark compensation uses a non-negative initial upward velocity.
    """

    values = (initial_height, initial_velocity, tolerance)
    if any(not math.isfinite(value) for value in values):
        raise ValueError("height, velocity, and tolerance must be finite")
    if initial_height <= 0.0 or initial_velocity < 0.0 or tolerance <= 0.0:
        raise ValueError(
            "height and tolerance must be positive; velocity must be non-negative"
        )
    if parameters.mu >= 1.0:
        raise ValueError("a finite bounce-time limit requires mu < 1")
    if parameters.beta == 0.0:
        impact_speed = math.sqrt(
            initial_velocity**2 + 2.0 * parameters.g * initial_height
        )
        first_impact = (initial_velocity + impact_speed) / parameters.g
        return first_impact + (
            2.0
            * parameters.mu
            * impact_speed
            / (parameters.g * (1.0 - parameters.mu))
        )

    beta = parameters.beta
    gravity = parameters.g
    velocity_scale = math.sqrt(gravity / beta)
    inverse_scale = math.sqrt(beta / gravity)
    rate = math.sqrt(gravity * beta)

    def ascent(velocity: float) -> tuple[float, float]:
        return (
            math.atan(velocity * inverse_scale) / rate,
            math.log1p(beta * velocity * velocity / gravity) / (2.0 * beta),
        )

    def descent(height: float) -> tuple[float, float]:
        ratio_squared = max(0.0, -math.expm1(-2.0 * beta * height))
        ratio = min(math.sqrt(ratio_squared), 1.0 - 1.0e-16)
        return math.atanh(ratio) / rate, velocity_scale * ratio

    up_time, added_height = ascent(initial_velocity)
    down_time, impact_speed = descent(initial_height + added_height)
    total = up_time + down_time
    for _ in range(10_000):
        rebound = parameters.mu * impact_speed
        up_time, added_height = ascent(rebound)
        down_time, impact_speed = descent(added_height)
        duration = up_time + down_time
        total += duration
        if duration <= tolerance:
            return total
    raise IntegrationError("bounce-time series did not converge")


def c21_event_contact_study() -> C21EventContactStudy:
    """Run the limit-time and nonlinear compensation benchmark tasks."""

    linear = c21_event_contact_limit_time(C21BouncingBallParameters(beta=0.0))
    nonlinear_parameters = C21BouncingBallParameters(beta=0.002)
    nonlinear = c21_event_contact_limit_time(nonlinear_parameters)
    low = 0.0
    high = 10.0
    for _ in range(60):
        middle = 0.5 * (low + high)
        if (
            c21_event_contact_limit_time(
                nonlinear_parameters,
                initial_velocity=middle,
            )
            < linear
        ):
            low = middle
        else:
            high = middle
    return C21EventContactStudy(linear, nonlinear, 0.5 * (low + high))


def c21_validate_bounce_times(count: int = 100) -> C21BounceValidation:
    """Compare the first ``count`` numerical and analytical impact times."""

    reference = c21_analytical_bounce_times(count)
    if count == 1:
        upper = 0.5 * (reference[0] + c21_last_bounce_time())
    else:
        next_time = c21_analytical_bounce_times(count + 1)[-1]
        upper = 0.5 * (reference[-1] + next_time)
    result = simulate_c21_bouncing_ball_event_contact(
        C21BouncingBallParameters(beta=0.0),
        t_bound=upper,
        max_bounces=count,
        method="rk45",
        options={"rtol": 1.0e-10, "atol": 1.0e-12, "max_step": 1.0e-2},
        settle_velocity=1.0e-15,
    )
    numerical = tuple(
        float(record.time.macro)
        for record in result.events
        if record.name == "bounce"
    )
    if len(numerical) != count:
        raise IntegrationError(
            f"expected {count} bounce events, observed {len(numerical)}"
        )
    errors = tuple(actual - expected for actual, expected in zip(numerical, reference))
    return C21BounceValidation(reference, numerical, errors)


def simulate_c21_bouncing_ball_dynamic_contact(
    parameters: C21BouncingBallParameters = C21BouncingBallParameters(),
    initial_state: Sequence[float] = (10.0, 0.0, 0.0),
    t_bound: float = 30.0,
    *,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
    settle_height: float = 1.0e-8,
    max_contacts: int = 1_000,
) -> HybridResult:
    """Run Equations 17--22 with finite contact phases and scattering guard."""

    state = tuple(float(value) for value in initial_state)
    if len(state) != 3 or any(not math.isfinite(value) for value in state):
        raise ValueError("dynamic-contact initial_state must contain finite x, v, w")
    if state[0] + state[2] < 0.0:
        raise ValueError("the initial deformed ball must not penetrate the ground")
    if not math.isfinite(settle_height) or settle_height <= 0.0:
        raise ValueError("settle_height must be positive and finite")
    if not isinstance(max_contacts, int) or isinstance(max_contacts, bool) or max_contacts <= 0:
        raise ValueError("max_contacts must be a positive integer")

    def contact_guard(_time: float, values: Sequence[float]) -> float:
        return values[0] + values[2]

    def flight_guard(_time: float, values: Sequence[float]) -> float:
        return -parameters.k * values[0] - parameters.d * values[1]

    def velocity_guard(_time: float, values: Sequence[float]) -> float:
        return float(values[1])

    def identity(_time: float, values: Sequence[float]) -> Vector:
        return tuple(values)

    def restart(_time: float, values: Sequence[float]) -> Vector | HybridReset:
        velocity = max(0.0, float(values[1]))
        predicted_height = velocity * velocity / (2.0 * parameters.g)
        if predicted_height <= settle_height:
            return HybridReset((0.0, 0.0, 0.0), mode="rest")
        return tuple(values)

    def rest(_time: float, _values: Sequence[float]) -> Vector:
        return (0.0, 0.0, 0.0)

    modes = {
        "flying": HybridMode(
            "flying",
            c21_bouncing_ball_dynamic_contact_flying(parameters),
            (
                StateEvent("contact", contact_guard, identity, "contact", -1),
                StateEvent("maximum-height", velocity_guard, identity, "descending", -1),
            ),
        ),
        "descending": HybridMode(
            "descending",
            c21_bouncing_ball_dynamic_contact_flying(parameters),
            (StateEvent("contact", contact_guard, identity, "contact", -1),),
        ),
        "contact": HybridMode(
            "contact",
            c21_bouncing_ball_dynamic_contact_contact(parameters),
            (
                StateEvent(
                    "maximum-deformation",
                    velocity_guard,
                    identity,
                    "contact-rebound",
                    1,
                ),
                StateEvent("fly", flight_guard, restart, "flying", -1),
            ),
        ),
        "contact-rebound": HybridMode(
            "contact-rebound",
            c21_bouncing_ball_dynamic_contact_contact(parameters),
            (StateEvent("fly", flight_guard, restart, "flying", -1),),
        ),
        "rest": HybridMode("rest", rest),
    }
    defaults = {
        "euler": {"step": 1.0e-5},
        "rk4": {"step": 1.0e-5},
        "rk45": {
            "rtol": 1.0e-8,
            "atol": 1.0e-10,
            "initial_step": 1.0e-5,
            "max_step": 1.0e-3,
        },
        "qss1": {"quantum": (1.0e-5, 1.0e-4, 1.0e-5)},
        "qss2": {"quantum": (1.0e-5, 1.0e-4, 1.0e-5)},
    }
    return simulate_hybrid(
        modes,
        initial_mode="flying",
        initial_state=state,
        t_bound=t_bound,
        method=method,
        solver_options=options,
        solver_defaults=defaults,
        max_events=4 * max_contacts + 2,
        segment_span=0.1,
    )


def c21_dynamic_contact_study(
    parameters: C21BouncingBallParameters = C21BouncingBallParameters(),
    *,
    t_bound: float = 5.0,
) -> C21DynamicContactStudy:
    """Run the detailed phase/extrema task and compare published first values."""

    result = simulate_c21_bouncing_ball_dynamic_contact(
        parameters,
        t_bound=t_bound,
        options={
            "rtol": 1.0e-10,
            "atol": 1.0e-12,
            "initial_step": 1.0e-6,
            "max_step": 1.0e-4,
        },
    )
    maximum_heights = (10.0,) + tuple(
        event.state_before[0]
        for event in result.events
        if event.name == "maximum-height"
    )
    maximum_deformations = tuple(
        event.state_before[2]
        for event in result.events
        if event.name == "maximum-deformation"
    )
    published_heights = (
        10.0,
        2.49475864884,
        0.63279737764,
        0.16059402954,
        0.04046743537,
        0.01002956662,
        0.00239944058,
        0.00053018975,
        0.00009492532,
        0.00000588511,
    )
    published_deformations = tuple(
        value * 1.0e-3
        for value in (
            9.87399975,
            4.97196356,
            2.51186760,
            1.26915027,
            0.64034298,
            0.32202875,
            0.16086111,
            0.07923061,
            0.03784056,
            0.01701582,
        )
    )
    return C21DynamicContactStudy(
        result,
        maximum_heights,
        maximum_deformations,
        published_heights,
        published_deformations,
    )


def c21_dynamic_contact_parameter_study(
    *,
    t_bound: float = 5.0,
) -> tuple[C21DynamicParameterRun, ...]:
    """Execute the official stiffness, damping, and Earth/Mars cases."""

    configurations = (
        ("k/100", C21BouncingBallParameters(k=1.0e4)),
        ("standard", C21BouncingBallParameters()),
        ("100k", C21BouncingBallParameters(k=1.0e8)),
        ("d/10", C21BouncingBallParameters(d=50.0)),
        ("10d", C21BouncingBallParameters(d=5_000.0)),
        (
            "matched-k100-d10",
            C21BouncingBallParameters(k=1.0e8, d=5_000.0),
        ),
        (
            "mars",
            C21BouncingBallParameters(g=3.69, beta=2.3e-4),
        ),
    )
    return tuple(
        C21DynamicParameterRun(
            label,
            case,
            simulate_c21_bouncing_ball_dynamic_contact(case, t_bound=t_bound),
        )
        for label, case in configurations
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
    amplitude_limit: float | None = None,
    kick_factor: float | None = None,
) -> HybridResult:
    """Run the structural-dynamic pendulum with optional external-energy kick.

    With ``amplitude_limit`` set, turning points are observed until the angle
    from the lower equilibrium no longer exceeds that limit. The run then
    terminates, unless ``kick_factor`` is supplied; in that case the angular
    velocity is multiplied at the next lower-equilibrium crossing.
    """

    state = tuple(float(value) for value in initial_state)
    if len(state) != 2 or any(not math.isfinite(value) for value in state):
        raise ValueError(
            "rotating-pendulum initial_state must contain finite phi and dphi"
        )
    if amplitude_limit is not None:
        amplitude_limit = float(amplitude_limit)
        if not math.isfinite(amplitude_limit) or not 0.0 < amplitude_limit < math.pi:
            raise ValueError("amplitude_limit must lie in (0, pi)")
    if kick_factor is not None:
        kick_factor = float(kick_factor)
        if not math.isfinite(kick_factor) or kick_factor == 0.0:
            raise ValueError("kick_factor must be finite and non-zero")
        if amplitude_limit is None:
            amplitude_limit = math.pi / 10.0

    def fall_guard(_time: float, values: Sequence[float]) -> float:
        return c21_rotating_pendulum_h_f(values, parameters)

    def swing_guard(_time: float, values: Sequence[float]) -> float:
        return c21_rotating_pendulum_h_s(values, parameters)

    def fall_reset(_time: float, values: Sequence[float]) -> Vector:
        return c21_rotating_pendulum_action_f(values, parameters)

    def swing_reset(_time: float, values: Sequence[float]) -> Vector:
        return c21_rotating_pendulum_action_s(values, parameters)

    def stop(_time: float, _values: Sequence[float]) -> Vector:
        return (0.0, 0.0)

    def turning_guard(_time: float, values: Sequence[float]) -> float:
        return float(values[1])

    def turning_reset(
        values: Sequence[float], alternate_mode: str
    ) -> HybridReset:
        assert amplitude_limit is not None
        angle = c21_rotating_pendulum_bottom_angle(values[0])
        if abs(angle) > amplitude_limit:
            return HybridReset(tuple(values), mode=alternate_mode)
        if kick_factor is None:
            return HybridReset(tuple(values), mode="stopped", terminate=True)
        return HybridReset(tuple(values), mode="armed")

    def turn_primary(_time: float, values: Sequence[float]) -> HybridReset:
        return turning_reset(values, "swinging_alternate")

    def turn_alternate(_time: float, values: Sequence[float]) -> HybridReset:
        return turning_reset(values, "swinging")

    def bottom_guard(_time: float, values: Sequence[float]) -> float:
        return math.sin(float(values[0]))

    def kick(_time: float, values: Sequence[float]) -> Vector:
        assert kick_factor is not None
        return (float(values[0]), kick_factor * float(values[1]))

    falling_event = StateEvent("fall", fall_guard, fall_reset, "falling", -1)
    falling_after_kick_event = StateEvent(
        "fall", fall_guard, fall_reset, "falling_after_kick", -1
    )
    catch_event = StateEvent("catch", swing_guard, swing_reset, "swinging", 1)
    catch_after_kick_event = StateEvent(
        "catch", swing_guard, swing_reset, "kicked", 1
    )

    modes = {
        "swinging": HybridMode(
            "swinging",
            c21_rotating_pendulum_swinging(parameters),
            (falling_event,),
        ),
        "falling": HybridMode(
            "falling",
            c21_rotating_pendulum_falling(parameters),
            (catch_event,),
        ),
    }
    if amplitude_limit is not None:
        modes["swinging"] = HybridMode(
            "swinging",
            c21_rotating_pendulum_swinging(parameters),
            (
                falling_event,
                StateEvent(
                    "turning-point",
                    turning_guard,
                    turn_primary,
                    "swinging_alternate",
                    0,
                ),
            ),
        )
        modes["swinging_alternate"] = HybridMode(
            "swinging_alternate",
            c21_rotating_pendulum_swinging(parameters),
            (
                falling_event,
                StateEvent(
                    "turning-point",
                    turning_guard,
                    turn_alternate,
                    "swinging",
                    0,
                ),
            ),
        )
        modes["stopped"] = HybridMode("stopped", stop)
    if kick_factor is not None:
        modes["armed"] = HybridMode(
            "armed",
            c21_rotating_pendulum_swinging(parameters),
            (
                falling_event,
                StateEvent("kick", bottom_guard, kick, "kicked", 0),
            ),
        )
        modes["kicked"] = HybridMode(
            "kicked",
            c21_rotating_pendulum_swinging(parameters),
            (falling_after_kick_event,),
        )
        modes["falling_after_kick"] = HybridMode(
            "falling_after_kick",
            c21_rotating_pendulum_falling(parameters),
            (catch_after_kick_event,),
        )
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


def c21_rotating_pendulum_basic_study() -> C21PendulumBasicStudy:
    """Run the published basic task and compare its stopping time."""

    result = simulate_c21_rotating_pendulum(
        t_bound=10.0,
        amplitude_limit=math.pi / 10.0,
        options={"rtol": 1.0e-10, "atol": 1.0e-12, "max_step": 1.0e-3},
    )
    if not result.events or result.events[-1].name != "turning-point":
        raise IntegrationError("pendulum did not reach the amplitude stop event")
    return C21PendulumBasicStudy(result, result.final_time)


def _c21_reverse_required_velocity(
    terminal_angle: float,
    terminal_velocity: float,
    parameters: C21RotatingPendulumParameters,
) -> float:
    """Integrate the damped pendulum backwards from a target to the bottom."""

    def reverse_rhs(_time: float, values: Sequence[float]) -> Vector:
        angle, velocity = values
        return (
            -velocity,
            (parameters.k / parameters.m) * velocity
            + (parameters.g / parameters.l) * math.sin(angle),
        )

    def bottom(_time: float, values: Sequence[float]) -> float:
        return float(values[0])

    def finish(_time: float, values: Sequence[float]) -> HybridReset:
        return HybridReset(tuple(values), mode="done", terminate=True)

    modes = {
        "reverse": HybridMode(
            "reverse",
            reverse_rhs,
            (StateEvent("bottom", bottom, finish, "done", -1),),
        ),
        "done": HybridMode("done", lambda _time, _values: (0.0, 0.0)),
    }
    result = simulate_hybrid(
        modes,
        initial_mode="reverse",
        initial_state=(terminal_angle, terminal_velocity),
        t_bound=3.0,
        method="rk45",
        solver_options={"rtol": 1.0e-11, "atol": 1.0e-13, "max_step": 1.0e-3},
    )
    if not result.events:
        raise IntegrationError("reverse pendulum did not reach the bottom")
    return result.events[-1].state_before[1]


def c21_rotating_pendulum_kick_study(
    parameters: C21RotatingPendulumParameters = C21RotatingPendulumParameters(),
) -> C21KickStudy:
    """Determine and externally validate all three published kick factors."""

    probe = simulate_c21_rotating_pendulum(
        parameters,
        t_bound=9.0,
        amplitude_limit=math.pi / 10.0,
        kick_factor=1.0,
        options={"rtol": 1.0e-10, "atol": 1.0e-12, "max_step": 1.0e-3},
    )
    kick_event = next((event for event in probe.events if event.name == "kick"), None)
    if kick_event is None:
        raise IntegrationError("pendulum did not reach the kick event")
    pre_kick_velocity = kick_event.state_before[1]
    targets = (
        ("same-movement", 5.0 * math.pi / 4.0, 15.0, -21.9911),
        ("fall-at-pi", math.pi, math.sqrt(parameters.g / parameters.l), -10.1501),
        (
            "two-rotations",
            3.0 * math.pi,
            math.sqrt(parameters.g / parameters.l),
            -14.1982,
        ),
    )
    entries = []
    for label, terminal_angle, terminal_velocity, published in targets:
        required = _c21_reverse_required_velocity(
            terminal_angle, terminal_velocity, parameters
        )
        entries.append(
            C21KickStudyEntry(
                label,
                terminal_angle,
                terminal_velocity,
                required,
                required / pre_kick_velocity,
                published,
            )
        )
    return C21KickStudy(pre_kick_velocity, tuple(entries))


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
    """Execute the full shortcut and Shockley comparison task."""

    shortcut = simulate_c21_rlc_diode(C21DiodeModel.SHORTCUT)
    shockley = simulate_c21_rlc_diode(C21DiodeModel.SHOCKLEY_DAE)
    return {
        "final_time": shockley.times[-1],
        "shortcut_events": float(len(shortcut.events)),
        "shockley_events": float(len(shockley.events)),
        "shockley_maximum_residual": shockley.maximum_algebraic_residual,
    }


class C21DiodeModel(str, Enum):
    SHORTCUT = "shortcut"
    SHOCKLEY_DAE = "shockley-dae"
    SHOCKLEY_INTERPOLATED = "shockley-interpolated"
    SHOCKLEY_EXPLICIT = "shockley-explicit"


@dataclass(frozen=True)
class C21RLCEvent:
    time: float
    source_mode: str
    target_mode: str


@dataclass(frozen=True)
class C21RLCResult:
    model: C21DiodeModel
    algebraic_state: str
    times: tuple[float, ...]
    current: tuple[float, ...]
    capacitor_voltage: tuple[float, ...]
    diode_voltage: tuple[float, ...]
    diode_current: tuple[float, ...]
    modes: tuple[str, ...]
    events: tuple[C21RLCEvent, ...]
    elapsed: float
    maximum_algebraic_residual: float


@dataclass(frozen=True)
class C21BounceValidation:
    analytical_times: tuple[float, ...]
    numerical_times: tuple[float, ...]
    errors: tuple[float, ...]

    @property
    def maximum_error(self) -> float:
        return max((abs(value) for value in self.errors), default=0.0)


@dataclass(frozen=True)
class C21DiodeStudyEntry:
    label: str
    model: C21DiodeModel
    algebraic_state: str
    interpolation_points: int | None
    elapsed: float
    events: int
    maximum_current_deviation: float
    maximum_capacitor_voltage_deviation: float
    maximum_algebraic_residual: float


@dataclass(frozen=True)
class C21DiodeStudy:
    t_bound: float
    entries: tuple[C21DiodeStudyEntry, ...]


def c21_rlc_input(time_value: float, frequency: float = 0.15e6) -> float:
    """Official sinusoidal source u0 = -sin(2*pi*f*t)."""

    return -math.sin(2.0 * math.pi * frequency * time_value)


def c21_shockley_breakpoints(
    points: int,
    parameters: C21RLCDiodeParameters = C21RLCDiodeParameters(),
) -> tuple[tuple[float, float], ...]:
    """Create 3/5/10-point piecewise-linear Shockley characteristics."""

    if not isinstance(points, int) or isinstance(points, bool) or points < 2:
        raise ValueError("points must be an integer >= 2")
    turning_voltage = parameters.u_t * math.log(
        parameters.u_t / (parameters.r2 * parameters.i_s)
    )
    maximum = 0.95 * turning_voltage
    return tuple(
        (
            maximum * index / (points - 1),
            parameters.i_s
            * (math.exp(maximum * index / ((points - 1) * parameters.u_t)) - 1.0),
        )
        for index in range(points)
    )


def c21_shockley_algebraic(
    current: float,
    capacitor_voltage: float,
    parameters: C21RLCDiodeParameters = C21RLCDiodeParameters(),
    *,
    interpolation_points: int | None = None,
) -> tuple[float, float, float]:
    """Solve the conducting-phase algebraic equation.

    Returns ``(u_D, i_D, residual)`` on the low-current physical branch.
    A non-positive open-circuit voltage is the locking solution.
    """

    base = parameters.r2 * current + capacitor_voltage
    if base <= 0.0:
        return base, 0.0, 0.0
    if interpolation_points is not None:
        breakpoints = c21_shockley_breakpoints(interpolation_points, parameters)
        candidate: tuple[float, float] | None = None
        for (left_u, left_i), (right_u, right_i) in itertools.pairwise(breakpoints):
            slope = (right_i - left_i) / (right_u - left_u)
            intercept = left_i - slope * left_u
            denominator = 1.0 - parameters.r2 * slope
            if abs(denominator) < 1.0e-14:
                continue
            voltage = (base + parameters.r2 * intercept) / denominator
            if left_u - 1.0e-14 <= voltage <= right_u + 1.0e-14:
                candidate = voltage, slope * voltage + intercept
                break
        if candidate is None:
            # Extrapolate the final stable segment; this keeps the model
            # defined while making extrapolation visible through the result.
            (left_u, left_i), (right_u, right_i) = breakpoints[-2:]
            slope = (right_i - left_i) / (right_u - left_u)
            intercept = left_i - slope * left_u
            denominator = 1.0 - parameters.r2 * slope
            if denominator <= 0.0:
                raise IntegrationError("interpolated Shockley branch is singular")
            voltage = (base + parameters.r2 * intercept) / denominator
            candidate = voltage, slope * voltage + intercept
        voltage, diode_current = candidate
        residual = voltage - parameters.r2 * (current + diode_current) - capacitor_voltage
        return voltage, diode_current, residual

    turning_voltage = parameters.u_t * math.log(
        parameters.u_t / (parameters.r2 * parameters.i_s)
    )

    def equation(voltage: float) -> float:
        diode_current = parameters.i_s * (math.exp(voltage / parameters.u_t) - 1.0)
        return voltage - parameters.r2 * (current + diode_current) - capacitor_voltage

    low = 0.0
    high = turning_voltage
    if equation(high) < 0.0:
        raise IntegrationError("Shockley algebraic equation has no low-current root")
    for _ in range(70):
        middle = 0.5 * (low + high)
        if equation(middle) >= 0.0:
            high = middle
        else:
            low = middle
    voltage = 0.5 * (low + high)
    diode_current = parameters.i_s * (math.exp(voltage / parameters.u_t) - 1.0)
    return voltage, diode_current, equation(voltage)


def c21_shockley_algebraic_current(
    current: float,
    capacitor_voltage: float,
    parameters: C21RLCDiodeParameters = C21RLCDiodeParameters(),
) -> tuple[float, float, float]:
    """Solve the same Shockley constraint with ``i_D`` as algebraic state."""

    base = parameters.r2 * current + capacitor_voltage
    if base <= 0.0:
        return base, 0.0, 0.0
    turning_voltage = parameters.u_t * math.log(
        parameters.u_t / (parameters.r2 * parameters.i_s)
    )
    high = (turning_voltage - base) / parameters.r2
    if high <= 0.0:
        raise IntegrationError("Shockley algebraic equation has no low-current root")

    def equation(diode_current: float) -> float:
        voltage = base + parameters.r2 * diode_current
        return diode_current - parameters.i_s * (
            math.exp(voltage / parameters.u_t) - 1.0
        )

    low = 0.0
    if equation(high) < 0.0:
        raise IntegrationError("Shockley algebraic equation has no low-current root")
    for _ in range(70):
        middle = 0.5 * (low + high)
        if equation(middle) >= 0.0:
            high = middle
        else:
            low = middle
    diode_current = 0.5 * (low + high)
    voltage = base + parameters.r2 * diode_current
    residual = voltage - parameters.r2 * (current + diode_current) - capacitor_voltage
    return voltage, diode_current, residual


def _c21_shockley_rhs(
    parameters: C21RLCDiodeParameters,
    source: Callable[[float], float],
    interpolation_points: int | None,
    algebraic_state: str,
) -> Rhs:
    def rhs(time_value: float, state: Sequence[float]) -> Vector:
        current, capacitor_voltage = state
        if algebraic_state == "current":
            _voltage, diode_current, _residual = c21_shockley_algebraic_current(
                current,
                capacitor_voltage,
                parameters,
            )
        else:
            _voltage, diode_current, _residual = c21_shockley_algebraic(
                current,
                capacitor_voltage,
                parameters,
                interpolation_points=interpolation_points,
            )
        return (
            -parameters.r1 / parameters.l * current
            - parameters.r2 / parameters.l * (current + diode_current)
            - capacitor_voltage / parameters.l
            + source(time_value) / parameters.l,
            (current + diode_current) / parameters.c,
        )

    return rhs


def simulate_c21_rlc_diode(
    model: C21DiodeModel | str = C21DiodeModel.SHOCKLEY_DAE,
    *,
    parameters: C21RLCDiodeParameters = C21RLCDiodeParameters(),
    initial_state: Sequence[float] = (0.0, 0.0),
    t_bound: float = 500.0e-6,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
    interpolation_points: int = 5,
    algebraic_state: str = "voltage",
    localize_events: bool = True,
) -> C21RLCResult:
    """Simulate all C21 diode formulations on the shared hybrid runtime."""

    selected = C21DiodeModel(model)
    if algebraic_state not in {"voltage", "current"}:
        raise ValueError("algebraic_state must be 'voltage' or 'current'")
    if (
        algebraic_state == "current"
        and selected is not C21DiodeModel.SHOCKLEY_DAE
    ):
        raise ValueError("current algebraic state is defined for shockley-dae")
    state = tuple(float(value) for value in initial_state)
    if len(state) != 2 or any(not math.isfinite(value) for value in state):
        raise ValueError("initial_state must contain finite i and u_C")
    if not math.isfinite(t_bound) or t_bound <= 0.0:
        raise ValueError("t_bound must be positive and finite")
    source = lambda value: c21_rlc_input(value, parameters.f)

    def conduct_guard(_time: float, values: Sequence[float]) -> float:
        return parameters.r2 * values[0] + values[1]

    def identity(_time: float, values: Sequence[float]) -> Vector:
        return tuple(values)

    locking = c21_rlc_diode_locking(parameters, source)
    if selected is C21DiodeModel.SHORTCUT:
        conducting = c21_rlc_diode_conducting_shortcut(parameters, source)

        def lock_guard(_time: float, values: Sequence[float]) -> float:
            return parameters.r2 * values[0] + values[1]

        conduct_reset = identity
        lock_reset = identity
    elif selected is C21DiodeModel.SHOCKLEY_EXPLICIT:
        conducting = c21_rlc_diode_conducting_explicit(parameters, source)

        def lock_guard(_time: float, values: Sequence[float]) -> float:
            return c21_rlc_diode_h_l_explicit(values, parameters)

        def conduct_reset(_time: float, values: Sequence[float]) -> Vector:
            return (values[0], values[1], 0.0)

        def lock_reset(_time: float, values: Sequence[float]) -> Vector:
            return (values[0], values[1])

    else:
        points = interpolation_points if selected is C21DiodeModel.SHOCKLEY_INTERPOLATED else None
        conducting = _c21_shockley_rhs(
            parameters,
            source,
            points,
            algebraic_state,
        )

        def lock_guard(_time: float, values: Sequence[float]) -> float:
            if algebraic_state == "current":
                voltage, _diode_current, _residual = c21_shockley_algebraic_current(
                    values[0], values[1], parameters
                )
            else:
                voltage, _diode_current, _residual = c21_shockley_algebraic(
                    values[0], values[1], parameters, interpolation_points=points
                )
            return voltage

        conduct_reset = identity
        lock_reset = identity

    modes = {
        "locking": HybridMode(
            "locking",
            locking,
            (StateEvent("conduct", conduct_guard, conduct_reset, "conducting", 1),),
            autonomous=False,
        ),
        "conducting": HybridMode(
            "conducting",
            conducting,
            (StateEvent("lock", lock_guard, lock_reset, "locking", -1),),
            autonomous=False,
        ),
    }
    defaults = {
        "euler": {"step": 2.0e-9},
        "rk4": {"step": 2.0e-9},
        "rk45": {
            "rtol": 1.0e-7,
            "atol": 1.0e-10,
            "initial_step": 1.0e-9,
            "max_step": 2.0e-8,
        },
        "qss1": {"quantum": (1.0e-7, 1.0e-5)},
        "qss2": {"quantum": (1.0e-7, 1.0e-5)},
    }
    started = time.perf_counter()
    hybrid = simulate_hybrid(
        modes,
        initial_mode="locking",
        initial_state=state,
        t_bound=t_bound,
        method=method,
        solver_options=options,
        solver_defaults=defaults,
        event_tolerance=1.0e-11,
        max_events=10_000,
        segment_span=1.0e-6,
        localize_events=localize_events,
    )
    elapsed = time.perf_counter() - started
    voltages = []
    diode_currents = []
    residuals = []
    for values, mode_name in zip(hybrid.states, hybrid.modes):
        current, capacitor_voltage = values[:2]
        if mode_name == "locking":
            voltage = parameters.r2 * current + capacitor_voltage
            diode_current = 0.0
        elif selected is C21DiodeModel.SHORTCUT:
            voltage = 0.0
            diode_current = -current - capacitor_voltage / parameters.r2
        elif selected is C21DiodeModel.SHOCKLEY_EXPLICIT:
            voltage = values[2]
            diode_current = parameters.i_s * (
                math.exp(min(700.0, voltage / parameters.u_t)) - 1.0
            )
        else:
            points = (
                interpolation_points
                if selected is C21DiodeModel.SHOCKLEY_INTERPOLATED
                else None
            )
            if algebraic_state == "current":
                voltage, diode_current, _ = c21_shockley_algebraic_current(
                    current, capacitor_voltage, parameters
                )
            else:
                voltage, diode_current, _ = c21_shockley_algebraic(
                    current, capacitor_voltage, parameters, interpolation_points=points
                )
        residual = voltage - parameters.r2 * (current + diode_current) - capacitor_voltage
        voltages.append(voltage)
        diode_currents.append(diode_current)
        residuals.append(abs(residual))
    return C21RLCResult(
        selected,
        (
            algebraic_state
            if selected is C21DiodeModel.SHOCKLEY_DAE
            else "explicit"
            if selected is C21DiodeModel.SHOCKLEY_EXPLICIT
            else "interpolated-voltage"
            if selected is C21DiodeModel.SHOCKLEY_INTERPOLATED
            else "shortcut"
        ),
        hybrid.times,
        tuple(values[0] for values in hybrid.states),
        tuple(values[1] for values in hybrid.states),
        tuple(voltages),
        tuple(diode_currents),
        hybrid.modes,
        tuple(
            C21RLCEvent(float(record.time.macro), record.source_mode, record.target_mode)
            for record in hybrid.events
        ),
        elapsed,
        max(residuals, default=0.0),
    )


def _c21_interpolate(
    times: Sequence[float], values: Sequence[float], time_value: float
) -> float:
    index = bisect_left(times, time_value)
    if index <= 0:
        return float(values[0])
    if index >= len(times):
        return float(values[-1])
    left_time = times[index - 1]
    right_time = times[index]
    if right_time == left_time:
        return float(values[index])
    fraction = (time_value - left_time) / (right_time - left_time)
    return float(values[index - 1]) + fraction * (
        float(values[index]) - float(values[index - 1])
    )


def c21_compare_diode_models(
    *,
    parameters: C21RLCDiodeParameters = C21RLCDiodeParameters(),
    t_bound: float | None = None,
    method: str = "rk45",
    options: Mapping[str, object] | None = None,
) -> C21DiodeStudy:
    """Run the shortcut, exact, 3/5/10-point, and explicit diode tasks."""

    final_time = 2.0 / parameters.f if t_bound is None else float(t_bound)
    configurations = (
        ("shortcut", C21DiodeModel.SHORTCUT, "voltage", None),
        ("shockley-uD", C21DiodeModel.SHOCKLEY_DAE, "voltage", None),
        ("shockley-iD", C21DiodeModel.SHOCKLEY_DAE, "current", None),
        ("interpolated-3", C21DiodeModel.SHOCKLEY_INTERPOLATED, "voltage", 3),
        ("interpolated-5", C21DiodeModel.SHOCKLEY_INTERPOLATED, "voltage", 5),
        ("interpolated-10", C21DiodeModel.SHOCKLEY_INTERPOLATED, "voltage", 10),
        ("shockley-explicit", C21DiodeModel.SHOCKLEY_EXPLICIT, "voltage", None),
    )
    runs: list[tuple[str, int | None, C21RLCResult]] = []
    for label, model, algebraic, points in configurations:
        runs.append(
            (
                label,
                points,
                simulate_c21_rlc_diode(
                    model,
                    parameters=parameters,
                    t_bound=final_time,
                    method=method,
                    options=options,
                    interpolation_points=points or 5,
                    algebraic_state=algebraic,
                ),
            )
        )
    reference = next(result for label, _points, result in runs if label == "shockley-uD")
    entries = []
    for label, points, result in runs:
        current_error = max(
            (
                abs(
                    candidate
                    - _c21_interpolate(
                        reference.times,
                        reference.current,
                        time_value,
                    )
                )
                for time_value, candidate in zip(result.times, result.current)
            ),
            default=0.0,
        )
        voltage_error = max(
            (
                abs(
                    candidate
                    - _c21_interpolate(
                        reference.times,
                        reference.capacitor_voltage,
                        time_value,
                    )
                )
                for time_value, candidate in zip(
                    result.times,
                    result.capacitor_voltage,
                )
            ),
            default=0.0,
        )
        entries.append(
            C21DiodeStudyEntry(
                label,
                result.model,
                result.algebraic_state,
                points,
                result.elapsed,
                len(result.events),
                current_error,
                voltage_error,
                result.maximum_algebraic_residual,
            )
        )
    return C21DiodeStudy(final_time, tuple(entries))


def c21_compare_diode_realtime(
    *,
    parameters: C21RLCDiodeParameters = C21RLCDiodeParameters(),
    t_bound: float | None = None,
    step: float = 2.0e-9,
) -> C21DiodeStudy:
    """Run the fixed-step/no-backtracking real-time comparison task."""

    final_time = 2.0 / parameters.f if t_bound is None else float(t_bound)
    if not math.isfinite(step) or step <= 0.0:
        raise ValueError("step must be positive and finite")
    reference = simulate_c21_rlc_diode(
        C21DiodeModel.SHOCKLEY_DAE,
        parameters=parameters,
        t_bound=final_time,
    )
    configurations = (
        ("realtime-shortcut", C21DiodeModel.SHORTCUT, 5),
        ("realtime-interpolated-10", C21DiodeModel.SHOCKLEY_INTERPOLATED, 10),
        ("realtime-explicit", C21DiodeModel.SHOCKLEY_EXPLICIT, 5),
    )
    entries = []
    for label, model, points in configurations:
        result = simulate_c21_rlc_diode(
            model,
            parameters=parameters,
            t_bound=final_time,
            method="rk4",
            options={"step": step},
            interpolation_points=points,
            localize_events=False,
        )
        current_error = max(
            (
                abs(
                    candidate
                    - _c21_interpolate(
                        reference.times,
                        reference.current,
                        time_value,
                    )
                )
                for time_value, candidate in zip(result.times, result.current)
            ),
            default=0.0,
        )
        voltage_error = max(
            (
                abs(
                    candidate
                    - _c21_interpolate(
                        reference.times,
                        reference.capacitor_voltage,
                        time_value,
                    )
                )
                for time_value, candidate in zip(
                    result.times,
                    result.capacitor_voltage,
                )
            ),
            default=0.0,
        )
        entries.append(
            C21DiodeStudyEntry(
                label,
                result.model,
                result.algebraic_state,
                points if model is C21DiodeModel.SHOCKLEY_INTERPOLATED else None,
                result.elapsed,
                len(result.events),
                current_error,
                voltage_error,
                result.maximum_algebraic_residual,
            )
        )
    return C21DiodeStudy(final_time, tuple(entries))
