"""ARGESIM C09R: sampled fuzzy control of a nonlinear two-tank plant."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum


class C09Controller(str, Enum):
    IFC1 = "I-FC1"
    IFC2 = "I-FC2"
    PFC = "P-FC"


class C09DifferenceSignal(str, Enum):
    """Interpretation of the second I-FC input.

    The revised definition writes ``e(k) - e(k-1)``, while the published
    Simulink solution feeds the FIS variable named ``change-level``.  The
    latter is the physically damping convention used by the reference plots;
    the literal equation remains available for reproducibility.
    """

    REFERENCE_LEVEL_CHANGE = "reference-level-change"
    LITERAL_ERROR_DIFFERENCE = "literal-error-difference"


@dataclass(frozen=True)
class C09PlantParameters:
    v1: float = 0.4
    v2: float = 0.3
    c1: float = 0.067
    c2: float = 0.0605
    c3: float = 0.06624

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(value) or value <= 0.0
            for value in (self.v1, self.v2, self.c1, self.c2, self.c3)
        ):
            raise ValueError("C09 plant parameters must be positive and finite")


@dataclass(frozen=True)
class C09Surface:
    x: tuple[float, ...]
    y: tuple[float, ...]
    z: tuple[tuple[float, ...], ...]
    controller: C09Controller


@dataclass(frozen=True)
class C09Result:
    controller: C09Controller
    times: tuple[float, ...]
    h1: tuple[float, ...]
    h2: tuple[float, ...]
    control: tuple[float, ...]
    setpoint: tuple[float, ...]

    @property
    def final_error(self) -> float:
        return self.setpoint[-1] - self.h2[-1]


@dataclass(frozen=True)
class C09BenchmarkResult:
    surfaces: tuple[C09Surface, ...]
    transients: tuple[C09Result, ...]
    difference_signal: C09DifferenceSignal


@dataclass(frozen=True)
class C09Validation:
    ifc1_final_error: float
    ifc2_final_error: float
    pfc_final_error: float
    ifc1_second_setpoint_overshoot: float
    ifc2_second_setpoint_overshoot: float
    published_qualitative_behaviour: bool


def _triangle(value: float, left: float, peak: float, right: float) -> float:
    if value <= left or value >= right:
        return 0.0
    if value == peak:
        return 1.0
    if value < peak:
        return (value - left) / (peak - left)
    return (right - value) / (right - peak)


def _left_shoulder(value: float, full_until: float, zero_at: float) -> float:
    if value <= full_until:
        return 1.0
    if value >= zero_at:
        return 0.0
    return (zero_at - value) / (zero_at - full_until)


def _right_shoulder(value: float, zero_until: float, full_at: float) -> float:
    if value <= zero_until:
        return 0.0
    if value >= full_at:
        return 1.0
    return (value - zero_until) / (full_at - zero_until)


def _error_memberships(error_cm: float) -> tuple[float, float, float]:
    """Return (high, good, low) using Figure 4/5 breakpoints."""

    return (
        _left_shoulder(error_cm, -25.0, 0.0),
        _triangle(error_cm, -25.0, 0.0, 25.0),
        _right_shoulder(error_cm, 0.0, 25.0),
    )


def _pfc_error_memberships(error_cm: float) -> tuple[float, float, float]:
    """Return the wider Figure-5 (high, good, low) partition."""

    return (
        _left_shoulder(error_cm, -30.0, 0.0),
        _triangle(error_cm, -30.0, 0.0, 30.0),
        _right_shoulder(error_cm, 0.0, 30.0),
    )


def _sum_aggregate_centroid(
    strengths: tuple[float, ...],
    areas: tuple[float, ...],
    centroids: tuple[float, ...],
) -> float:
    """Exact COG for product implication and sum aggregation."""

    denominator = sum(weight * area for weight, area in zip(strengths, areas))
    if denominator == 0.0:
        return 0.0
    return sum(
        weight * area * centroid
        for weight, area, centroid in zip(strengths, areas, centroids)
    ) / denominator


def c09_ifc_increment(
    error: float,
    delta_error: float,
    controller: C09Controller | str = C09Controller.IFC1,
) -> float:
    """Evaluate either integral fuzzy controller.

    Both inputs are supplied in metres and scaled to the centimetre universes
    shown in Figure 4.  ``delta_error`` is the selected one-second difference
    signal (normally the measured-level change; see :class:`C09DifferenceSignal`).
    """

    selected = C09Controller(controller)
    if selected is C09Controller.PFC:
        raise ValueError("P-FC produces u directly, not an increment")
    high, good, low = _error_memberships(100.0 * error)
    difference_cm = 100.0 * delta_error
    falling = _left_shoulder(difference_cm, -0.025, 0.0)
    rising = _right_shoulder(difference_cm, 0.0, 0.025)
    strengths = (high, good * rising, good * falling, low)
    # Consequents: close-fast, close-slow, open-slow, open-fast.
    if selected is C09Controller.IFC2:
        singletons = (-2.0e-4, -1.0e-4, 1.0e-4, 2.0e-4)
        denominator = sum(strengths)
        return 0.0 if denominator == 0.0 else sum(
            weight * value for weight, value in zip(strengths, singletons)
        ) / denominator

    # Each consequent is piecewise linear.  With product implication and sum
    # aggregation, its area and first moment can be combined analytically.
    return _sum_aggregate_centroid(
        strengths,
        (1.25e-4, 2.5e-4, 2.5e-4, 1.25e-4),
        (-5.0e-4 / 1.2, -2.5e-4, 2.5e-4, 5.0e-4 / 1.2),
    )


def c09_pfc_control(error: float, h2: float) -> float:
    """Evaluate the proportional Mamdani controller in physical volts."""

    high_error, good_error, low_error = _pfc_error_memberships(100.0 * error)
    level_cm = 100.0 * h2
    low_level = _left_shoulder(level_cm, 30.0, 40.0)
    middle_level = _triangle(level_cm, 30.0, 40.0, 60.0)
    high_level = _right_shoulder(level_cm, 40.0, 60.0)
    strengths = (
        high_error,
        good_error * low_level,
        good_error * middle_level,
        good_error * high_level,
        low_error,
    )
    # Figure 5 is displayed in 10^-1 V.  The values below are its physical
    # breakpoints; exact areas/moments avoid a 301-point scan every second.
    p1_area = 0.12
    p1_centroid = (0.1 * 0.05 + 0.02 * (0.1 + 0.1 + 0.14) / 3.0) / p1_area
    p5_area = 0.07
    p5_centroid = (0.02 * (0.21 + 0.25 + 0.25) / 3.0 + 0.05 * 0.275) / p5_area
    return _sum_aggregate_centroid(
        strengths,
        (p1_area, 0.0375, 0.035, 0.0375, p5_area),
        (
            p1_centroid,
            (0.10 + 0.14 + 0.175) / 3.0,
            0.175,
            (0.175 + 0.21 + 0.25) / 3.0,
            p5_centroid,
        ),
    )


def c09_controller_surface(
    controller: C09Controller | str,
    *,
    points: int = 31,
) -> C09Surface:
    """Compute Task-A or Task-C fuzzy characteristic surfaces."""

    selected = C09Controller(controller)
    if not isinstance(points, int) or isinstance(points, bool) or points < 2:
        raise ValueError("points must be an integer >= 2")
    x_axis = tuple(-30.0 + 60.0 * index / (points - 1) for index in range(points))
    if selected is C09Controller.PFC:
        y_axis = tuple(100.0 * index / (points - 1) for index in range(points))
        values = tuple(
            tuple(c09_pfc_control(error / 100.0, level / 100.0) for error in x_axis)
            for level in y_axis
        )
    else:
        y_axis = tuple(-0.05 + 0.1 * index / (points - 1) for index in range(points))
        values = tuple(
            tuple(c09_ifc_increment(error / 100.0, delta, selected) for error in x_axis)
            for delta in y_axis
        )
    return C09Surface(x_axis, y_axis, values, selected)


def c09_plant_rhs(
    h1: float,
    h2: float,
    voltage: float,
    parameters: C09PlantParameters = C09PlantParameters(),
) -> tuple[float, float]:
    """Evaluate the revised nonlinear plant, including its h2 regime switch."""

    difference = h1 - h2
    coupling = (
        parameters.c3
        * parameters.v1
        * math.sqrt(abs(difference))
        * (1.0 if difference >= 0.0 else -1.0)
    )
    outlet_factor = 1.2 if h2 < 0.16 else 1.0
    outlet = (
        outlet_factor
        * parameters.c2
        * parameters.v2
        * math.sqrt(max(0.0, h2))
    )
    return parameters.c1 * voltage - coupling, coupling - outlet


def _c09_rk4_step(
    h1: float,
    h2: float,
    voltage: float,
    step: float,
    parameters: C09PlantParameters,
) -> tuple[float, float]:
    k1 = c09_plant_rhs(h1, h2, voltage, parameters)
    k2 = c09_plant_rhs(
        h1 + 0.5 * step * k1[0], h2 + 0.5 * step * k1[1], voltage, parameters
    )
    k3 = c09_plant_rhs(
        h1 + 0.5 * step * k2[0], h2 + 0.5 * step * k2[1], voltage, parameters
    )
    k4 = c09_plant_rhs(h1 + step * k3[0], h2 + step * k3[1], voltage, parameters)
    return (
        max(0.0, h1 + step * (k1[0] + 2.0 * k2[0] + 2.0 * k3[0] + k4[0]) / 6.0),
        max(0.0, h2 + step * (k1[1] + 2.0 * k2[1] + 2.0 * k3[1] + k4[1]) / 6.0),
    )


def c09_reference_setpoint(time_value: float) -> float:
    if time_value < 20_000.0:
        return 0.30
    if time_value < 40_000.0:
        return 0.60
    return 0.40


def simulate_c09(
    controller: C09Controller | str,
    *,
    t_bound: float = 60_000.0,
    sample_time: float = 1.0,
    output_step: float = 100.0,
    initial_state: tuple[float, float] = (0.503, 0.3),
    initial_control: float = 0.18,
    disturbance_time: float = 50_000.0,
    disturbance: float = 0.1,
    actuator_scale: float = 1.0,
    difference_signal: C09DifferenceSignal | str = (
        C09DifferenceSignal.REFERENCE_LEVEL_CHANGE
    ),
    parameters: C09PlantParameters = C09PlantParameters(),
) -> C09Result:
    """Run the complete changing-setpoint/disturbance experiment.

    The default follows the operational ``change-level`` signal in the
    published Simulink solution.  Select ``literal-error-difference`` to run
    the equation printed in the revised definition instead.
    """

    selected = C09Controller(controller)
    selected_difference = C09DifferenceSignal(difference_signal)
    if any(
        not math.isfinite(value)
        for value in (sample_time, output_step, t_bound, disturbance_time, disturbance)
    ) or sample_time <= 0.0 or output_step < sample_time or t_bound <= 0.0:
        raise ValueError("valid positive simulation and output steps are required")
    if not math.isfinite(actuator_scale) or actuator_scale <= 0.0:
        raise ValueError("actuator_scale must be positive and finite")
    steps = int(round(t_bound / sample_time))
    stride = int(round(output_step / sample_time))
    if not math.isclose(steps * sample_time, t_bound, abs_tol=1.0e-10):
        raise ValueError("t_bound must be an integer multiple of sample_time")
    if not math.isclose(stride * sample_time, output_step, abs_tol=1.0e-10):
        raise ValueError("output_step must be an integer multiple of sample_time")
    h1, h2 = (float(value) for value in initial_state)
    if not math.isfinite(h1) or not math.isfinite(h2) or h1 < 0.0 or h2 < 0.0:
        raise ValueError("tank levels must be non-negative")
    control = float(initial_control)
    if not math.isfinite(control):
        raise ValueError("initial_control must be finite")
    previous_error = c09_reference_setpoint(0.0) - h2
    previous_h2 = h2
    times = [0.0]
    h1_values = [h1]
    h2_values = [h2]
    controls = [control]
    setpoints = [c09_reference_setpoint(0.0)]

    for index in range(steps):
        time_value = index * sample_time
        setpoint = c09_reference_setpoint(time_value)
        error = setpoint - h2
        if selected is C09Controller.PFC:
            control = c09_pfc_control(error, h2)
        else:
            difference = (
                h2 - previous_h2
                if selected_difference
                is C09DifferenceSignal.REFERENCE_LEVEL_CHANGE
                else error - previous_error
            )
            control += c09_ifc_increment(error, difference, selected)
        control = min(0.3, max(0.0, control))
        previous_error = error
        previous_h2 = h2
        # The disturbance is specified independently as 0.1 V and therefore
        # must not be scaled together with the controller output.
        applied = actuator_scale * control + (
            disturbance if time_value >= disturbance_time else 0.0
        )
        h1, h2 = _c09_rk4_step(h1, h2, applied, sample_time, parameters)
        if (index + 1) % stride == 0 or index + 1 == steps:
            output_time = (index + 1) * sample_time
            times.append(output_time)
            h1_values.append(h1)
            h2_values.append(h2)
            controls.append(control)
            setpoints.append(c09_reference_setpoint(output_time))
    return C09Result(
        selected,
        tuple(times),
        tuple(h1_values),
        tuple(h2_values),
        tuple(controls),
        tuple(setpoints),
    )


def c09_run_benchmark(
    *,
    surface_points: int = 31,
    difference_signal: C09DifferenceSignal | str = (
        C09DifferenceSignal.REFERENCE_LEVEL_CHANGE
    ),
) -> C09BenchmarkResult:
    """Execute Tasks A--C for every controller in one reusable entry point."""

    selected_difference = C09DifferenceSignal(difference_signal)
    return C09BenchmarkResult(
        tuple(
            c09_controller_surface(controller, points=surface_points)
            for controller in C09Controller
        ),
        tuple(
            simulate_c09(controller, difference_signal=selected_difference)
            for controller in C09Controller
        ),
        selected_difference,
    )


def c09_validate() -> C09Validation:
    """Check the qualitative findings reported by the classic C09R solution."""

    results = {
        controller: simulate_c09(controller, output_step=10.0)
        for controller in C09Controller
    }
    ifc1 = results[C09Controller.IFC1]
    ifc2 = results[C09Controller.IFC2]
    pfc = results[C09Controller.PFC]

    def overshoot(result: C09Result) -> float:
        values = (
            value
            for time_value, value in zip(result.times, result.h2)
            if 20_000.0 <= time_value < 40_000.0
        )
        return max(0.0, max(values) - 0.6)

    ifc1_overshoot = overshoot(ifc1)
    ifc2_overshoot = overshoot(ifc2)
    qualitative = (
        abs(ifc1.final_error) < 1.0e-3
        and abs(ifc2.final_error) < 1.0e-3
        and abs(pfc.final_error) > 1.0e-2
        and ifc1_overshoot < 1.0e-3
        and ifc2_overshoot < 1.0e-3
    )
    if not qualitative:
        raise RuntimeError("C09 transient response differs from the published behaviour")
    return C09Validation(
        ifc1.final_error,
        ifc2.final_error,
        pfc.final_error,
        ifc1_overshoot,
        ifc2_overshoot,
        qualitative,
    )
