"""Compare quantizers and time steppers at common observables on POSIX.

The eight ARGESIM cases reuse the earlier protocol. The five analytical
probes independently integrate from the original initial state to each
observation horizon. This avoids interpolating or forcing output restarts.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import random
import signal
from dataclasses import asdict, dataclass, replace
from pathlib import Path

from scipy.integrate import solve_ivp as scipy_ivp

if __package__:
    from . import benchmark_solver_extension as study
else:
    import benchmark_solver_extension as study

from argesim_benchmarks import InitialValueProblem, IntegrationError, solve_ivp
from argesim_benchmarks.evidence import RuntimeEnvironment
from argesim_benchmarks.models import c05_two_state as switch_model

QUANTIZED = tuple(m for m in study.METHODS if m not in ("euler", "rk4", "rk45"))
NEW = ("bqss1", "qss1-log", "qss2-log")
IMPLICIT = ("Radau", "BDF")
RTOLS = (1e-3, 1e-5, 1e-7)
STEPS = (1.0, 0.4, 0.1)
C05_REFINEMENT = (1e-4, 5e-5, 2.5e-5)


@dataclass(frozen=True)
class Work:
    accepted_steps: int
    rejected_steps: int | None
    rhs_evaluations: int
    lu_factorizations: int | None


@dataclass(frozen=True)
class Run:
    final_time: float
    stats: Work


def scipy_work(result):
    if not result.success:
        raise IntegrationError(result.message)
    count = len(result.t) - 1
    if count > 40000:
        raise IntegrationError("SciPy exceeded 40000 accepted steps")
    return Work(count, None, result.nfev, result.nlu)


def total_work(parts):
    return Work(
        sum(s.accepted_steps for s in parts),
        None
        if parts[0].rejected_steps is None
        else sum(s.rejected_steps for s in parts),
        sum(s.rhs_evaluations for s in parts),
        sum(s.lu_factorizations for s in parts) if isinstance(parts[0], Work) else None,
    )


def analytical_case(name, rhs, initial, exact, horizons, step, scales):
    expected = tuple(v for t in horizons for v in exact(t))
    limits = tuple(
        0.001 * s + 0.005 * abs(v)
        for t in horizons
        for s, v in zip(scales, exact(t), strict=True)
    )

    def run(method, opts):
        values, parts = [], []
        for end in horizons:
            if method in IMPLICIT:
                r = scipy_ivp(rhs, (0, end), initial, method=method, **opts)
                parts.append(scipy_work(r))
                if r.t[-1] != end:
                    raise IntegrationError("incomplete SciPy horizon")
                values.extend(r.y[:, -1])
            else:
                p = InitialValueProblem(rhs, 0, initial, end, autonomous=True)
                r = solve_ivp(p, method.removesuffix("-log"), options=opts)
                if r.final_time != end:
                    raise IntegrationError("incomplete ODE horizon")
                parts.append(r.stats)
                values.extend(r.final_state)
        return Run(horizons[-1], total_work(parts)), tuple(values)

    # One-dimensional mixed mode is necessarily the full BDF partition.
    return study.Case(
        name, horizons[-1], scales, (len(initial) - 1,), step, run, expected, limits
    )


def analytic_cases():
    def rotated(t):
        slow, fast = math.exp(-t), math.exp(-1000 * t)
        return (slow + fast) / 2, (slow - fast) / 2

    def tracking(t):
        slow = -2 / (100 + math.sqrt(9996))
        fast = 1 / slow
        b = (0.2 + 20.2 * slow) / (fast - slow)
        a = -20.2 - b
        return (
            a * math.expm1(slow * t) + b * math.expm1(fast * t),
            100 * (a * slow * math.exp(slow * t) + b * fast * math.exp(fast * t)),
        )

    return (
        analytical_case(
            "decay",
            lambda t, y: (-y[0],),
            (100.0,),
            lambda t: (100 * math.exp(-t),),
            (0.1, 2.0, 5.0, 8.0),
            0.5,
            (1.0,),
        ),
        analytical_case(
            "oscillator",
            lambda t, y: (y[1], -y[0]),
            (1.0, 0.0),
            lambda t: (math.cos(t), -math.sin(t)),
            (0.3, 3.1, 12.7, 25.0),
            0.5,
            (1.0, 1.0),
        ),
        analytical_case(
            "diagonal",
            lambda t, y: (-y[0], -1000 * y[1]),
            (1.0, 1.0),
            lambda t: (math.exp(-t), math.exp(-1000 * t)),
            (0.001, 0.01, 0.1, 1.0),
            0.005,
            (1.0, 1.0),
        ),
        analytical_case(
            "tracking",
            lambda t, y: (0.01 * y[1], -100 * y[0] - 100 * y[1] + 2020),
            (0.0, 20.0),
            tracking,
            (0.01, 5.0, 100.0, 500.0),
            0.05,
            (20.0, 20.0),
        ),
        analytical_case(
            "rotated",
            lambda t, y: (-500.5 * y[0] + 499.5 * y[1], 499.5 * y[0] - 500.5 * y[1]),
            (1.0, 0.0),
            rotated,
            (0.001, 0.01, 0.1, 1.0),
            0.005,
            (1.0, 1.0),
        ),
    )


def implicit_switches(end, method, opts):
    mode = switch_model.C05_MODE_1
    state = switch_model.C05_INITIAL_STATE
    t = 0.0
    events, parts = [], []
    while t < end:

        def rhs(t, y, mode=mode):
            return (
                switch_model.C05_C1 * (y[1] + mode.c2 - y[0]),
                switch_model.C05_C3 * (mode.c4 - y[1]),
            )

        def guard(t, y, mode=mode):
            return y[0] - mode.threshold

        guard.terminal = True
        guard.direction = mode.direction
        r = scipy_ivp(rhs, (t, end), state, method=method, events=guard, **opts)
        parts.append(scipy_work(r))
        if r.t[-1] <= t:
            raise IntegrationError("SciPy switch made no progress")
        t = r.t[-1]
        state = r.y[:, -1]
        if len(r.t_events[0]):
            events.append(t)
            if len(events) > 10000:
                raise IntegrationError("SciPy exceeded switch budget")
            mode = (
                switch_model.C05_MODE_2
                if mode == switch_model.C05_MODE_1
                else switch_model.C05_MODE_1
            )
    return Run(t, total_work(parts)), (*events, *state)


def argesim_case(case):
    def run(method, opts):
        if method in IMPLICIT:
            return implicit_switches(case.end, method, opts)
        return case.run(method.removesuffix("-log"), opts)

    return replace(case, run=run)


def configure(case, method, level):
    if method in IMPLICIT or (method == "rk45" and level is not None):
        rtol = RTOLS[level]
        opts = {"rtol": rtol, "atol": tuple(s * rtol * 0.01 for s in case.scales)}
        if method == "rk45":
            opts["max_steps"] = 40000
        return opts
    if method == "rk4" and level is not None:
        return {"step": case.step * STEPS[level], "max_steps": 40000}
    levels = (*study.LEVELS, *C05_REFINEMENT) if case.name == "C05" else study.LEVELS
    factor = levels[level] if level is not None else None
    opts = study.options(case, method.removesuffix("-log"), factor)
    if method.endswith("-log"):
        opts["relative_quantum"] = factor
    return opts


def schedule():
    rows = []
    for case in map(
        argesim_case,
        (
            study.amplifier(),
            study.switches(),
            study.pendulum(),
            study.tanks(),
            study.robot(),
            study.spheres(),
            study.crane(),
            study.bounce(),
        ),
    ):
        rows.extend(
            (case, m, level) for m in (*NEW, "qss1", "qss2") for level in range(3)
        )
        rows.extend((case, m, None) for m in ("rk4", "rk45"))
        if case.name == "C05":
            rows.extend((case, "bqss1", level) for level in range(3, 6))
            rows.extend((case, m, level) for m in IMPLICIT for level in range(3))
    for case in analytic_cases():
        rows.extend(
            (case, m, level)
            for m in (*QUANTIZED, *NEW, "rk4", "rk45", *IMPLICIT)
            for level in range(3)
        )
    random.Random(72).shuffle(rows)
    return rows


def source_digest():
    """Hash the Python sources actually used, also in a checkout without Git."""
    root = Path(__file__).resolve().parents[1]
    sources = [
        *root.joinpath("argesim_benchmarks").rglob("*.py"),
        *root.joinpath("nsa_devs").rglob("*.py"),
        Path(study.__file__).resolve(),
        Path(__file__).resolve(),
    ]
    digest = hashlib.sha256()
    for p in sorted(sources):
        digest.update(p.relative_to(root).as_posix().encode() + b"\0")
        digest.update(hashlib.sha256(p.read_bytes()).digest())
    return digest.hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--repeat", type=int, default=3)
    p.add_argument(
        "--timeout", type=float, default=2.0, help="seconds per timed solve bundle"
    )
    args = p.parse_args()
    if args.repeat < 1 or not math.isfinite(args.timeout) or args.timeout <= 0:
        p.error("repeat and timeout must be positive")
    signal.signal(signal.SIGALRM, study.timeout_handler)
    fields = (
        "case",
        "method",
        "level",
        "status",
        "error_over_limit",
        "accepted",
        "rejected",
        "rhs",
        "lu",
        "median_ms",
        "times_ms",
        "detail",
    )
    if args.output.suffix != ".csv":
        p.error("output must be a .csv file (the companion .json records provenance)")
    sources = source_digest()
    rows = schedule()
    with args.output.open("w", newline="", buffering=1) as f:
        writer = csv.DictWriter(f, fields, lineterminator="\n")
        writer.writeheader()
        for case, method, level in rows:
            row = study.measure(case, method, level, args, configure)
            row["level"] = row.pop("quantum_factor")
            writer.writerow(row)
    if sources != source_digest():
        raise RuntimeError("experiment sources changed during measurement")
    metadata = {
        "source_sha256": sources,
        "csv_sha256": hashlib.sha256(args.output.read_bytes()).hexdigest(),
        "configurations": len(rows),
        "seed": 72,
        "warmups": 1,
        "repetitions": args.repeat,
        "timeout_seconds": args.timeout,
        "environment": asdict(RuntimeEnvironment.capture()),
        "numpy": study.np.__version__,
        "scipy": study.scipy.__version__,
        "threads": {
            k: os.environ.get(k) for k in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS")
        },
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
