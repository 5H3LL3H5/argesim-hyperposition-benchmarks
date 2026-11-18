#!/usr/bin/env python3
"""Accuracy-gated work comparison for CQSS1 and mixed LIQSS2-BDF."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks import InitialValueProblem, cqss1, liqss_bdf


def _timed(run, repeat: int, warmup: int):
    for _ in range(warmup):
        run()
    durations: list[int] = []
    result = None
    for _ in range(repeat):
        started = time.perf_counter_ns()
        result = run()
        durations.append(time.perf_counter_ns() - started)
    assert result is not None
    if len(durations) < 2:
        iqr = 0.0
    else:
        quartiles = statistics.quantiles(durations, n=4, method="inclusive")
        iqr = quartiles[2] - quartiles[0]
    return result, statistics.median(durations), iqr


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cqss-quantum", type=float, default=5.0e-2)
    parser.add_argument("--mixed-quantum", type=float, default=5.0e-4)
    parser.add_argument("--repeat", type=int, default=9)
    parser.add_argument("--warmup", type=int, default=1)
    arguments = parser.parse_args()
    if (
        arguments.cqss_quantum <= 0.0
        or not math.isfinite(arguments.cqss_quantum)
        or arguments.mixed_quantum <= 0.0
        or not math.isfinite(arguments.mixed_quantum)
    ):
        parser.error("quanta must be positive and finite")
    if arguments.repeat < 1 or arguments.warmup < 0:
        parser.error("repeat must be positive and warmup must be non-negative")

    oscillator = InitialValueProblem(
        lambda _time, state: (state[1], -state[0]),
        0.0,
        (1.0, 0.0),
        100.0,
        name="cqss-harmonic-oscillator",
        autonomous=True,
    )
    cqss_result, cqss_median, cqss_iqr = _timed(
        lambda: cqss1(oscillator, arguments.cqss_quantum),
        arguments.repeat,
        arguments.warmup,
    )
    energies = [
        0.5 * (state[0] ** 2 + state[1] ** 2)
        for state in cqss_result.states
    ]
    energy_span = max(energies) - min(energies)
    if energy_span > 2.0 * arguments.cqss_quantum**2:
        raise RuntimeError("CQSS1 failed the harmonic-energy gate")

    triangular = InitialValueProblem(
        lambda _time, state: (
            -state[0] + state[1],
            -10.0 * state[1],
        ),
        0.0,
        (0.0, 1.0),
        1.0,
        name="mixed-liqss-bdf-triangular",
        autonomous=True,
    )
    mixed_result, mixed_median, mixed_iqr = _timed(
        lambda: liqss_bdf(
            triangular,
            (arguments.mixed_quantum, 1.0e-6),
            bdf_partition=(1,),
            jacobian=lambda _time, _state: (
                (-1.0, 1.0),
                (0.0, -10.0),
            ),
            rtol=1.0e-4,
            atol=1.0e-7,
            max_step=0.05,
        ),
        arguments.repeat,
        arguments.warmup,
    )
    exact = (
        (math.exp(-1.0) - math.exp(-10.0)) / 9.0,
        math.exp(-10.0),
    )
    mixed_error = max(
        abs(actual - expected)
        for actual, expected in zip(mixed_result.final_state, exact)
    )
    if mixed_error > arguments.mixed_quantum:
        raise RuntimeError("LIQSS-BDF failed the endpoint-accuracy gate")

    print(
        json.dumps(
            {
                "benchmark": "cqss-and-liqss-bdf-reference-work",
                "cqss1": {
                    "problem": "x' = p, p' = -x; t_final = 100",
                    "quantum": arguments.cqss_quantum,
                    "energy_span": energy_span,
                    "events": cqss_result.stats.accepted_steps,
                    "rhs_evaluations": cqss_result.stats.rhs_evaluations,
                    "median_ns": cqss_median,
                    "iqr_ns": cqss_iqr,
                },
                "liqss-bdf": {
                    "problem": "x' = -x + z, z' = -10 z; BDF partition = z",
                    "quantum": arguments.mixed_quantum,
                    "endpoint_error": mixed_error,
                    "accepted_macro_steps_and_events": (
                        mixed_result.stats.accepted_steps
                    ),
                    "rejected_macro_steps": mixed_result.stats.rejected_steps,
                    "rhs_evaluations": mixed_result.stats.rhs_evaluations,
                    "median_ns": mixed_median,
                    "iqr_ns": mixed_iqr,
                },
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
