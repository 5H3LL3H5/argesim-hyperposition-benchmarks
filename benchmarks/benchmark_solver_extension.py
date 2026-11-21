"""Reproduce the extended ARGESIM solver study (POSIX, NumPy and SciPy)."""

import argparse
import bisect
import csv
import math
import platform
import random
import signal
import statistics
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import scipy
from scipy.integrate import solve_ivp as scipy_ivp
from scipy.linalg import expm

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argesim_benchmarks import InitialValueProblem, IntegrationError, solve_ivp
from argesim_benchmarks.hybrid import (
    HybridMode,
    StateEvent,
    StateThreshold,
    simulate_hybrid,
)
from argesim_benchmarks.models import c05_two_state as c05
from argesim_benchmarks.models.c03_amplifier import C03Parameters, solve_c03
from argesim_benchmarks.models.c07_constrained_pendulum import solve_c07
from argesim_benchmarks.models.c09_fuzzy_tanks import c09_pfc_control, c09_plant_rhs
from argesim_benchmarks.models.c11_scara_robot import c11_problem, solve_c11
from argesim_benchmarks.models.c13_crane import c13_linear_rhs
from argesim_benchmarks.models.c21_state_events import (
    C21BouncingBallParameters,
    c21_analytical_bounce_times,
    simulate_c21_bouncing_ball_event_contact,
)
from argesim_benchmarks.runtime import merge_integration_results

METHODS = (
    "qss1",
    "qss2",
    "qss3",
    "qss4",
    "cqss1",
    *(
        f"{family}{order}"
        for family in ("liqss", "mliqss", "eliqss", "cheqss")
        for order in (1, 2, 3)
    ),
    "liqss-bdf",
    "euler",
    "rk4",
    "rk45",
)
LEVELS = (0.005, 0.001, 0.0002)


@dataclass
class Case:
    name: str
    end: float
    scales: tuple
    partition: tuple
    step: float
    run: object
    expected: tuple
    tolerances: tuple


def at(result, t):
    k = bisect.bisect_left(result.times, t)
    if k >= len(result.times) or abs(result.times[k] - t) > 1e-12 * max(1, abs(t)):
        raise ArithmeticError("missing prescribed output")
    return result.states[k]


def amplifier():
    state = np.zeros(4)
    expected = []
    for resistance in (5e6, 0.05):
        matrix = np.array(
            [
                [0, -1 / 79.9e-6, 0, 0, 5 / 79.9e-6],
                [1 / 17.9e-9, -1 / (17.9e-9 * resistance), -1 / 17.9e-9, 0, 0],
                [0, 1 / 232e-6, -52.4 / 232e-6, -1 / 232e-6, 0],
                [0, 0, 1 / 9.66e-9, 0, 0],
                [0] * 5,
            ]
        )
        state = (expm(5e-6 * matrix) @ np.r_[state, 1])[:4]
        expected.extend(state)

    def run(method, options):
        r = solve_c03(
            method, parameters=C03Parameters(trf=0.0), t_bound=1e-5, options=options
        )
        return r, (*at(r, 5e-6), *r.final_state)

    scales = (1.0, 10.0, 1.0, 10.0)
    return Case(
        "C03",
        1e-5,
        scales,
        (1,),
        1e-9,
        run,
        tuple(expected),
        tuple(x * 0.001 for x in scales) * 2,
    )


def switches():
    end = 3.5
    modes = {}
    for active, other in (
        (c05.C05_MODE_1, c05.C05_MODE_2),
        (c05.C05_MODE_2, c05.C05_MODE_1),
    ):

        def rhs(t, y, m=active):
            return c05.C05_C1 * (y[1] + m.c2 - y[0]), c05.C05_C3 * (m.c4 - y[1])

        event = StateEvent(
            "switch",
            StateThreshold(0, active.threshold),
            lambda t, y: y,
            other.name,
            active.direction,
        )
        modes[active.name] = HybridMode(active.name, rhs, (event,))
    ref = c05.simulate_c05(t_bound=end)

    def run(method, options):
        r = simulate_hybrid(
            modes,
            initial_mode=c05.C05_MODE_1.name,
            initial_state=c05.C05_INITIAL_STATE,
            t_bound=end,
            method=method,
            solver_options=options,
        )
        return r, (*[float(e.time.macro) for e in r.events], *r.final_state)

    expected = (*[e.time for e in ref.events], *ref.final_state)
    return Case(
        "C05",
        end,
        (6.0, 6.0),
        (0,),
        5e-7,
        run,
        expected,
        (0.001,) * len(ref.events) + (0.006, 0.006),
    )


def pendulum():
    t = 0.0
    state = (math.pi / 6, 0.0)
    short = False
    crossings = []
    end = 2.0
    while t < end:
        length = 0.3 if short else 1.0

        def guard(t, y):
            return y[0] + math.pi / 12

        guard.terminal = True
        guard.direction = 1 if short else -1
        ref = scipy_ivp(
            lambda t, y, length=length: (
                y[1],
                -9.81 / length * math.sin(y[0]) - 0.2 / 1.02 * y[1],
            ),
            (t, end),
            state,
            events=guard,
            method="DOP853",
            max_step=0.005,
            rtol=1e-12,
            atol=1e-13,
        )
        if not ref.success:
            raise RuntimeError(ref.message)
        t = ref.t[-1]
        state = ref.y[:, -1].copy()
        if t < end:
            crossings.append(t)
            state[1] *= 0.3 if short else 1 / 0.3
            short = not short

    def run(m, o):
        r = solve_c07(
            initial_state=(math.pi / 6, 0.0), t_bound=end, method=m, options=o
        )
        hits = [
            b
            for i, (a, b) in enumerate(zip(r.times, r.times[1:]))
            if a == b and r.states[i] != r.states[i + 1]
        ]
        return r, (*hits, *r.final_state)

    return Case(
        "C07",
        end,
        (1.0, 4.0),
        (1,),
        0.001,
        run,
        (*crossings, *state),
        (0.001,) * len(crossings) + (0.001, 0.004),
    )


def tanks():
    end = 16

    def integrate(method, options):
        state = (0.503, 0.30)
        outputs = []
        segments = []
        for t in range(end):
            control = min(0.3, max(0.0, c09_pfc_control(0.30 - state[1], state[1]))) + (
                0.1 if t >= 4 else 0.0
            )

            def rhs(time, y, u=control):
                return c09_plant_rhs(*y, u)

            if method is None:
                ref = scipy_ivp(
                    rhs, (t, t + 1), state, method="DOP853", rtol=1e-12, atol=1e-14
                )
                if not ref.success:
                    raise RuntimeError(ref.message)
                state = ref.y[:, -1]
            else:
                seg = solve_ivp(
                    InitialValueProblem(rhs, t, state, t + 1, autonomous=True),
                    method,
                    options=options,
                )
                segments.append(seg)
                state = seg.final_state
            outputs.extend(state)
        return merge_integration_results(segments) if segments else None, tuple(outputs)

    return Case(
        "C09",
        end,
        (0.5, 0.5),
        (1,),
        0.05,
        integrate,
        integrate(None, {})[1],
        (0.0005,) * (2 * end),
    )


def robot():
    end = 0.0001
    p = c11_problem(t_bound=end)
    ref = scipy_ivp(p.rhs, (0, end), p.y0, method="Radau", rtol=1e-11, atol=1e-14)
    if not ref.success:
        raise RuntimeError(ref.message)
    scales = (1.0, 1.0, 0.1, 1.0, 1.0, 0.1, 2.0, 2.0, 2.0)

    def run(m, o):
        r = solve_c11(m, t_bound=end, options=o)
        return r, r.final_state

    return Case(
        "C11",
        end,
        scales,
        (6, 7, 8),
        end / 100,
        run,
        tuple(ref.y[:, -1]),
        tuple(0.001 * x for x in scales),
    )


def spheres():
    # C12-A2, perfectly elastic, equal masses: transfer incident velocity to the next sphere.
    def contact(j):
        def reset(t, y):
            s = list(y)
            s[j] = 0.0
            s[j + 3], s[j + 4] = s[j + 4], s[j + 3]
            return s

        return StateEvent(f"contact-{j}", StateThreshold(j), reset, "flight", -1)

    mode = HybridMode(
        "flight",
        lambda t, y: (y[4] - y[3], y[5] - y[4], y[6] - y[5], 0.0, 0.0, 0.0, 0.0),
        tuple(contact(i) for i in range(3)),
    )

    def run(m, o):
        r = simulate_hybrid(
            {"flight": mode},
            initial_mode="flight",
            initial_state=(1, 1, 1, 1, 0, 0, 0),
            t_bound=4.0,
            method=m,
            solver_options=o,
        )
        if [e.name for e in r.events] != ["contact-0", "contact-1", "contact-2"]:
            return r, ()
        return r, (*[float(e.time.macro) for e in r.events], *r.final_state[3:])

    return Case(
        "C12",
        4.0,
        (1.0,) * 7,
        (3,),
        0.01,
        run,
        (1.0, 2.0, 3.0, 0.0, 0.0, 0.0, 1.0),
        (0.001,) * 7,
    )


def crane():
    # x=(cart, cart speed, angle, angle rate, drive force); augmented constant for affine forcing.
    stages = ((0, 4, 0), (4, 7, -800), (7, 15, 0))
    expected = []
    y = np.zeros(5)
    for a, b, force in stages:
        mat = np.array(
            [
                [0, 1, 0, 0, 0, 0],
                [0, -0.05, 98.1, 0, 0.1, 0],
                [0, 0, 0, 1, 0, 0],
                [0, (0.05 - 0.00001) / 5, -9.81 * 11 / 5, -0.00001, -0.02, force / 500],
                [0, 0, 0, 0, -4, 640],
                [0] * 6,
            ]
        )
        y = (expm((b - a) * mat) @ np.r_[y, 1])[:5]
        expected.extend(y)

    def run(m, o):
        segments = []
        y = (0.0,) * 5
        for a, b, force in stages:
            rhs = c13_linear_rhs(fc_desired=160.0, fd=force)
            seg = solve_ivp(
                InitialValueProblem(rhs, a, y, b, autonomous=True), m, options=o
            )
            segments.append(seg)
            y = seg.final_state
        return merge_integration_results(segments), tuple(
            v for seg in segments for v in seg.final_state
        )

    scales = (100.0, 10.0, 1.0, 2.0, 160.0)
    return Case(
        "C13",
        15.0,
        scales,
        (4,),
        0.005,
        run,
        tuple(expected),
        tuple(0.001 * x for x in scales) * 3,
    )


def bounce():
    def run(m, o):
        r = simulate_c21_bouncing_ball_event_contact(
            C21BouncingBallParameters(beta=0.0), t_bound=5.0, method=m, options=o
        )
        return r, tuple(float(e.time.macro) for e in r.events)

    return Case(
        "C21",
        5.0,
        (10.0, 14.0),
        (1,),
        0.005,
        run,
        c21_analytical_bounce_times(2),
        (0.001, 0.001),
    )


def options(case, method, factor):
    if method in {"rk4", "euler"}:
        return {"step": case.step, "max_steps": 40000}
    if method == "rk45":
        return {
            "rtol": 1e-8,
            "atol": tuple(s * 1e-10 for s in case.scales),
            "max_steps": 40000,
        }
    opts = {"quantum": tuple(factor * s for s in case.scales), "max_events": 40000}
    if method == "liqss-bdf":
        opts.update(
            bdf_partition=case.partition,
            max_step=case.end / 50,
            rtol=1e-5,
            atol=tuple(s * 1e-8 for s in case.scales),
            max_steps=40000,
        )
    return opts


def timeout_handler(signum, frame):
    raise TimeoutError("per-integration time limit")


def measure(case, method, factor, args, configure=options):
    row = {"case": case.name, "method": method, "quantum_factor": factor}
    elapsed = []
    try:
        for i in range(args.repeat + 1):
            opts = configure(case, method, factor)
            signal.setitimer(signal.ITIMER_REAL, args.timeout)
            try:
                start = time.perf_counter_ns()
                result, values = case.run(method, opts)
                duration = (time.perf_counter_ns() - start) / 1e6
            finally:
                signal.setitimer(signal.ITIMER_REAL, 0)
            if result.final_time != case.end:
                raise IntegrationError("incomplete interval")
            if not i:
                first = values
                stats = result.stats
                row.update(
                    accepted=stats.accepted_steps,
                    rejected=stats.rejected_steps,
                    rhs=stats.rhs_evaluations,
                )
                if hasattr(stats, "lu_factorizations"):
                    row["lu"] = stats.lu_factorizations
                if len(values) != len(case.expected):
                    row.update(
                        status="event_mismatch",
                        detail=f"{len(values)} of {len(case.expected)} observables",
                    )
                else:
                    ratios = [abs(x - y) / tol for x, y, tol in
                              zip(values, case.expected, case.tolerances, strict=True)]
                    if not all(math.isfinite(error) for error in ratios):
                        raise IntegrationError("nonfinite accuracy ratio")
                    ratio = max(ratios)
                    row.update(
                        status="pass" if ratio <= 1 else "accuracy_miss",
                        error_over_limit=ratio,
                    )
            else:
                if values != first or result.stats != stats:
                    raise RuntimeError("nonrepeatable solve")
                elapsed.append(duration)
        row.update(
            median_ms=statistics.median(elapsed),
            times_ms=" ".join(f"{t:.6f}" for t in elapsed),
        )
    except (IntegrationError, ArithmeticError, TimeoutError) as exc:
        row.update(
            status="timeout" if isinstance(exc, TimeoutError) else "solver_error",
            detail=str(exc),
        )
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument("--timeout", type=float, default=2.0)
    args = p.parse_args()
    if args.repeat < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        p.error("invalid repeat or timeout")
    print(platform.python_version(), np.__version__, scipy.__version__, flush=True)
    schedule = [
        (c, m, q)
        for c in (
            amplifier(),
            switches(),
            pendulum(),
            tanks(),
            robot(),
            spheres(),
            crane(),
            bounce(),
        )
        for m in METHODS
        for q in (LEVELS if m not in ("rk4", "rk45", "euler") else (None,))
    ]
    random.Random(71).shuffle(schedule)
    signal.signal(signal.SIGALRM, timeout_handler)
    fields = [
        "case",
        "method",
        "quantum_factor",
        "status",
        "error_over_limit",
        "accepted",
        "rejected",
        "rhs",
        "median_ms",
        "times_ms",
        "detail",
    ]
    with args.output.open("w", newline="", buffering=1) as out:
        writer = csv.DictWriter(out, fields, lineterminator="\n")
        writer.writeheader()
        for case, method, factor in schedule:
            writer.writerow(measure(case, method, factor, args))


if __name__ == "__main__":
    main()
