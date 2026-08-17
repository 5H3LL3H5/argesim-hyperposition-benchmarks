"""ARGESIM C15: Clearance Identification.

The equations, parameters, initial values and tasks follow the official
C15 definition. State order is ``(x1, x2)``.
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ..ivp import InitialValueProblem, IntegrationResult, Rhs, Vector
from ..runtime import (
    merge_integration_results,
    normalise_solver_name,
    solve_ivp,
)

C15_INITIAL_STATE: Vector = (0.0, 0.0)

C15_MEASUREMENTS_TIME: tuple[float, ...] = (
    5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0, 40.0, 45.0, 50.0, 55.0, 60.0,
    75.0, 90.0, 105.0, 120.0, 150.0, 180.0, 240.0
)
C15_MEASUREMENTS_CONC: tuple[float, ...] = (
    276.0, 227.0, 203.0, 190.0, 184.0, 174.0, 176.0, 171.0, 167.0, 163.0,
    151.0, 155.0, 150.0, 142.0, 141.0, 135.0, 128.0, 120.0, 111.0
)


@dataclass(frozen=True)
class C15Parameters:
    """Parameters in the notation of the official C15 definition."""

    k01: float = 0.0041
    k21: float = 0.0498
    k12: float = 0.0585
    v1: float = 7.3

    def __post_init__(self) -> None:
        if any(
            not math.isfinite(value) or value <= 0.0
            for value in (self.k01, self.k21, self.k12, self.v1)
        ):
            raise ValueError("C15 parameters must be positive and finite")


_C15_DEFAULT_PARAMETERS = C15Parameters()


@dataclass(frozen=True)
class C15Bolus:
    """Input bolus configuration."""

    d: float
    tau: float

    def __post_init__(self) -> None:
        if not math.isfinite(self.d) or self.d < 0.0:
            raise ValueError("bolus dose must be non-negative and finite")
        if not math.isfinite(self.tau) or self.tau <= 0.0:
            raise ValueError("bolus duration must be positive and finite")


def c15_rhs(
    parameters: C15Parameters = _C15_DEFAULT_PARAMETERS,
    bolus: C15Bolus = C15Bolus(2500.0, 0.5),
) -> Rhs:
    """Return the official two-state linear rate equations."""

    def rhs(time: float, state: Sequence[float]) -> Vector:
        x1, x2 = state
        f_t = bolus.d / bolus.tau if 0.0 <= time < bolus.tau else 0.0
        return (
            f_t - (parameters.k01 + parameters.k21) * x1 + parameters.k12 * x2,
            parameters.k21 * x1 - parameters.k12 * x2,
        )

    return rhs


def c15_problem(
    *,
    parameters: C15Parameters = _C15_DEFAULT_PARAMETERS,
    bolus: C15Bolus = C15Bolus(2500.0, 0.5),
    initial_state: Sequence[float] = C15_INITIAL_STATE,
    t_bound: float = 240.0,
) -> InitialValueProblem:
    """Build the C15 initial-value problem."""

    return InitialValueProblem(
        c15_rhs(parameters, bolus),
        0.0,
        initial_state,
        t_bound,
        name="ARGESIM-C15-clearance",
        autonomous=False,
    )


def solve_c15(
    method: str = "rk45",
    *,
    parameters: C15Parameters = _C15_DEFAULT_PARAMETERS,
    bolus: C15Bolus = C15Bolus(2500.0, 0.5),
    initial_state: Sequence[float] = C15_INITIAL_STATE,
    t_bound: float = 240.0,
    options: Mapping[str, object] | None = None,
) -> IntegrationResult:
    """Solve C15 with an explicitly selected backend."""

    problem = c15_problem(
        parameters=parameters,
        bolus=bolus,
        initial_state=initial_state,
        t_bound=t_bound,
    )
    normalised = normalise_solver_name(method)
    defaults = {
        "euler": {"step": 1.0e-2},
        "rk4": {"step": 1.0e-2},
        "rk45": {"rtol": 1.0e-8, "atol": 1.0e-11, "max_step": 1.0},
        "qss1": {"quantum": (1.0, 1.0)},
        "qss2": {"quantum": (1.0, 1.0)},
    }
    quantized_methods = {
        "qss1",
        "qss2",
        "qss3",
        "qss4",
        "liqss1",
        "liqss2",
        "liqss3",
        "eliqss1",
        "eliqss2",
        "eliqss3",
        "cheqss1",
        "cheqss2",
        "cheqss3",
        "mliqss1",
        "mliqss2",
        "mliqss3",
    }
    if normalised not in quantized_methods:
        return solve_ivp(problem, normalised, options=options, defaults=defaults)

    # QSS requires autonomous ODEs, so expose the bolus switch as two segments.
    def rhs_phase1(_time: float, state: Sequence[float]) -> Vector:
            x1, x2 = state
            f_t = bolus.d / bolus.tau
            return (
                f_t - (parameters.k01 + parameters.k21) * x1 + parameters.k12 * x2,
                parameters.k21 * x1 - parameters.k12 * x2,
            )

    def rhs_phase2(_time: float, state: Sequence[float]) -> Vector:
            x1, x2 = state
            return (
                -(parameters.k01 + parameters.k21) * x1 + parameters.k12 * x2,
                parameters.k21 * x1 - parameters.k12 * x2,
            )

    first_end = min(bolus.tau, t_bound)
    first_problem = InitialValueProblem(
        rhs_phase1,
        0.0,
        initial_state,
        first_end,
        name="ARGESIM-C15-bolus-on",
        autonomous=True,
    )
    first = solve_ivp(
        first_problem,
        normalised,
        options=options,
        defaults=defaults,
    )
    if t_bound <= bolus.tau:
        return first

    second_problem = InitialValueProblem(
        rhs_phase2,
        bolus.tau,
        first.final_state,
        t_bound,
        name="ARGESIM-C15-bolus-off",
        autonomous=True,
    )
    second = solve_ivp(
        second_problem,
        normalised,
        options=options,
        defaults=defaults,
    )
    return merge_integration_results((first, second), method=normalised)


def c15_analytical(
    time: float,
    parameters: C15Parameters = _C15_DEFAULT_PARAMETERS,
    bolus: C15Bolus = C15Bolus(2500.0, 0.5),
) -> Vector:
    """Return the exact analytical solution for the C15 state."""

    a = parameters.k01 + parameters.k21
    b = parameters.k12
    c = parameters.k21

    trace = -(a + b)
    det = b * parameters.k01
    discriminant = math.sqrt(trace * trace - 4.0 * det)

    l1 = 0.5 * (trace + discriminant)
    l2 = 0.5 * (trace - discriminant)

    v1_2 = (l1 + a) / b
    v2_2 = (l2 + a) / b

    xs1 = (bolus.d / bolus.tau) / parameters.k01
    xs2 = xs1 * c / b

    c1 = (xs1 * v2_2 - xs2) / (v1_2 - v2_2)
    c2 = -xs1 - c1

    if time < bolus.tau:
        x1 = c1 * math.exp(l1 * time) + c2 * math.exp(l2 * time) + xs1
        x2 = c1 * v1_2 * math.exp(l1 * time) + c2 * v2_2 * math.exp(l2 * time) + xs2
        return (x1, x2)

    x1_tau = c1 * math.exp(l1 * bolus.tau) + c2 * math.exp(l2 * bolus.tau) + xs1
    x2_tau = c1 * v1_2 * math.exp(l1 * bolus.tau) + c2 * v2_2 * math.exp(l2 * bolus.tau) + xs2

    d1 = (x2_tau - x1_tau * v2_2) / (v1_2 - v2_2)
    d2 = x1_tau - d1

    dt = time - bolus.tau
    x1 = d1 * math.exp(l1 * dt) + d2 * math.exp(l2 * dt)
    x2 = d1 * v1_2 * math.exp(l1 * dt) + d2 * v2_2 * math.exp(l2 * dt)
    return (x1, x2)


def c15_task_a() -> dict[str, IntegrationResult]:
    """Simulate the system with three different bolus durations."""

    boluses = {
        "tau_0_5": C15Bolus(2500.0, 0.5),
        "tau_3_0": C15Bolus(2500.0, 3.0),
        "tau_240": C15Bolus(2500.0, 240.0),
    }
    return {
        name: solve_c15("rk45", bolus=b, options={"max_step": 0.1})
        for name, b in boluses.items()
    }


def _solve_linear_system(a_matrix: list[list[float]], b_vector: list[float]) -> list[float]:
    """Solve a square linear system Ax = b using Gaussian elimination."""

    n = len(a_matrix)
    m = [row[:] + [b_vector[i]] for i, row in enumerate(a_matrix)]
    for i in range(n):
        max_row = max(range(i, n), key=lambda r: abs(m[r][i]))
        m[i], m[max_row] = m[max_row], m[i]
        pivot = m[i][i]
        if abs(pivot) < 1.0e-14:
            raise ValueError("singular matrix")
        for j in range(i, n + 1):
            m[i][j] /= pivot
        for r in range(n):
            if r != i:
                factor = m[r][i]
                for j in range(i, n + 1):
                    m[r][j] -= factor * m[i][j]
    return [m[i][n] for i in range(n)]


def _levenberg_marquardt(
    residual_fn,
    p0: Sequence[float],
    tol: float = 1.0e-8,
    max_iter: int = 200,
    min_bound: float = 1.0e-6,
) -> tuple[float, ...]:
    """Minimise sum of squared residuals using Levenberg-Marquardt.

    The min_bound prevents the parameters (which represent biological
    rates and volumes) from becoming zero or negative during the search.
    """

    p = list(p0)
    n = len(p)
    lamb = 0.001

    def jacobian(curr_p):
        j = []
        f0 = residual_fn(curr_p)
        for i in range(n):
            dp = list(curr_p)
            eps = max(abs(dp[i]) * 1.0e-5, 1.0e-8)
            dp[i] += eps
            f1 = residual_fn(dp)
            j.append([(f1_k - f0_k) / eps for f0_k, f1_k in zip(f0, f1)])
        return [[j[col][row] for col in range(n)] for row in range(len(f0))], f0

    for _ in range(max_iter):
        j, f = jacobian(p)
        cost = sum(x * x for x in f)

        jt = [[j[row][col] for row in range(len(j))] for col in range(n)]
        jtj = [
            [sum(jt[r][k] * j[k][c] for k in range(len(j))) for c in range(n)]
            for r in range(n)
        ]
        jtf = [sum(jt[r][k] * f[k] for k in range(len(j))) for r in range(n)]

        if all(abs(g) < tol for g in jtf):
            break

        for _inner in range(10):
            a_matrix = [[jtj[r][c] for c in range(n)] for r in range(n)]
            for i in range(n):
                a_matrix[i][i] += lamb * a_matrix[i][i] + lamb

            try:
                dp = _solve_linear_system(a_matrix, jtf)
            except ValueError:
                dp = [0.0] * n

            p_new = [p[i] - dp[i] for i in range(n)]
            p_new = [max(min_bound, val) for val in p_new]

            f_new = residual_fn(p_new)
            cost_new = sum(x * x for x in f_new)

            if cost_new < cost:
                lamb /= 10.0
                p = p_new
                break
            else:
                lamb *= 10.0
        else:
            break

    return tuple(p)


def c15_task_b(
    measurements_time: Sequence[float] = C15_MEASUREMENTS_TIME,
    measurements_conc: Sequence[float] = C15_MEASUREMENTS_CONC,
    bolus: C15Bolus = C15Bolus(2500.0, 0.5),
) -> dict[str, float]:
    """Fit the model parameters to experimental data."""

    if len(measurements_time) != len(measurements_conc):
        raise ValueError("measurement times and concentrations must have equal length")
    if len(measurements_time) < 5:
        raise ValueError("parameter identification requires at least five measurements")
    if any(not math.isfinite(float(t)) or float(t) < 0.0 for t in measurements_time):
        raise ValueError("measurement times must be non-negative and finite")
    if any(not math.isfinite(float(c)) for c in measurements_conc):
        raise ValueError("measurement concentrations must be finite")

    def residual(p_list):
        k01, k21, k12, v1 = p_list
        params = C15Parameters(k01=k01, k21=k21, k12=k12, v1=v1)
        res = []
        for t, c_exp in zip(measurements_time, measurements_conc):
            x1, _ = c15_analytical(t, params, bolus)
            res.append((x1 / v1) - c_exp)
        return res

    p0 = [0.0041, 0.0498, 0.0585, 7.3]
    p_opt = _levenberg_marquardt(residual, p0)

    k01, k21, k12, v1 = p_opt
    params = C15Parameters(k01=k01, k21=k21, k12=k12, v1=v1)

    # Find exact maximum concentration using bisection on the derivative.
    # The peak must occur after the bolus ends (t >= tau) since x1 is strictly increasing during injection.
    def dx1_dt(t_val: float) -> float:
        x1, x2 = c15_analytical(t_val, params, bolus)
        return -(params.k01 + params.k21) * x1 + params.k12 * x2

    t_low = bolus.tau
    t_high = 240.0
    for _ in range(50):
        t_mid = 0.5 * (t_low + t_high)
        if dx1_dt(t_mid) < 0.0:
            t_high = t_mid
        else:
            t_low = t_mid

    x1_max, _ = c15_analytical(t_low, params, bolus)
    max_c = x1_max / v1

    res_final = residual(p_opt)
    residuum = sum(x * x for x in res_final)

    return {
        "k01": k01,
        "k21": k21,
        "k12": k12,
        "v1": v1,
        "clearance": k01 * v1,
        "maximum_concentration": max_c,
        "residuum": residuum,
    }


def c15_task_c(
    measurements_time: Sequence[float] = C15_MEASUREMENTS_TIME,
    measurements_conc: Sequence[float] = C15_MEASUREMENTS_CONC,
    bolus: C15Bolus = C15Bolus(2500.0, 0.5),
    iterations: int = 1000,
    seed: int = 42,
) -> dict[str, dict[str, float]]:
    """Estimate parameter error using a Monte Carlo method on artificial data."""

    if iterations < 2:
        raise ValueError("Monte Carlo analysis requires at least two iterations")
    if len(measurements_time) != len(measurements_conc):
        raise ValueError("measurement times and concentrations must have equal length")
    if len(measurements_time) <= 4:
        raise ValueError("Monte Carlo residual variance requires more than four measurements")

    base_res = c15_task_b(measurements_time, measurements_conc, bolus)
    e = base_res["residuum"]
    n = len(measurements_time)
    np_params = 4
    s = math.sqrt(e / (n - np_params))

    rng = random.Random(seed)

    def residual(p_list, art_conc):
        k01, k21, k12, v1 = p_list
        params = C15Parameters(k01=k01, k21=k21, k12=k12, v1=v1)
        res = []
        for t, c_exp in zip(measurements_time, art_conc):
            x1, _ = c15_analytical(t, params, bolus)
            res.append((x1 / v1) - c_exp)
        return res

    p0 = [base_res["k01"], base_res["k21"], base_res["k12"], base_res["v1"]]
    results = {"k01": [], "k21": [], "k12": [], "v1": []}

    for _ in range(iterations):
        art_conc = [c + rng.gauss(0.0, s) for c in measurements_conc]

        def res_fn(p):
            return residual(p, art_conc)

        p_opt = _levenberg_marquardt(res_fn, p0, max_iter=50)
        results["k01"].append(p_opt[0])
        results["k21"].append(p_opt[1])
        results["k12"].append(p_opt[2])
        results["v1"].append(p_opt[3])

    stats = {}
    for key, values in results.items():
        mean = sum(values) / len(values)
        variance = (
            sum((v - mean) ** 2 for v in values) / (len(values) - 1)
            if len(values) > 1
            else 0.0
        )
        stats[key] = {"mean": mean, "deviation": math.sqrt(variance)}

    return stats
