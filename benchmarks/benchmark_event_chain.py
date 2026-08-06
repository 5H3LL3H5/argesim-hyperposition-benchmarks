#!/usr/bin/env python3
"""Workload-equivalent representation benchmark for a finite relay chain."""

from __future__ import annotations

import argparse
import heapq
import json
import statistics
import sys
import time
from fractions import Fraction
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nsa_devs import run_relay_chain


def run_tuple_chain(length: int, initial_payload: int = 0) -> tuple[int, int, int]:
    """Raw-tuple baseline with the same queue and payload work."""

    queue = [((Fraction(0), 0), 0, initial_payload)]
    checksum = 0
    processed = 0
    final_payload = initial_payload

    while queue:
        (macro, micro), component, payload = heapq.heappop(queue)
        output_time = (macro, micro + 1)
        output_payload = payload + 1
        checksum = (
            checksum * 1_000_003
            + component * 97
            + output_time[1] * 31
            + output_payload
        ) % 2_147_483_647
        processed += 1
        final_payload = output_payload
        if component + 1 < length:
            heapq.heappush(
                queue,
                (output_time, component + 1, output_payload),
            )

    return final_payload, processed, checksum


def _typed_observable(length: int) -> tuple[int, int, int]:
    result = run_relay_chain(length)
    return result.final_payload, len(result.trace), result.checksum


def _measure(function, length: int, repeat: int, warmup: int) -> list[int]:
    for _ in range(warmup):
        function(length)

    durations = []
    for _ in range(repeat):
        start = time.perf_counter_ns()
        function(length)
        durations.append(time.perf_counter_ns() - start)
    return durations


def _summary(durations: list[int], events: int) -> dict[str, object]:
    ordered = sorted(durations)
    quartiles = statistics.quantiles(ordered, n=4, method="inclusive")
    median_ns = statistics.median(ordered)
    return {
        "durations_ns": durations,
        "median_ns": median_ns,
        "q1_ns": quartiles[0],
        "q3_ns": quartiles[2],
        "iqr_ns": quartiles[2] - quartiles[0],
        "median_events_per_second": events / (median_ns * 1e-9),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--length", type=int, default=1000)
    parser.add_argument("--repeat", type=int, default=21)
    parser.add_argument("--warmup", type=int, default=3)
    args = parser.parse_args()

    if args.length <= 0:
        parser.error("--length must be positive")
    if args.repeat < 5:
        parser.error("--repeat must be at least five")
    if args.warmup < 0:
        parser.error("--warmup must be non-negative")

    typed_observable = _typed_observable(args.length)
    tuple_observable = run_tuple_chain(args.length)
    if typed_observable != tuple_observable:
        raise RuntimeError(
            f"result mismatch: typed={typed_observable}, tuple={tuple_observable}"
        )

    typed_times = _measure(_typed_observable, args.length, args.repeat, args.warmup)
    tuple_times = _measure(run_tuple_chain, args.length, args.repeat, args.warmup)
    typed_summary = _summary(typed_times, args.length)
    tuple_summary = _summary(tuple_times, args.length)

    report = {
        "experiment": "finite_nsa_devs_relay_representation_overhead",
        "length": args.length,
        "repeat": args.repeat,
        "warmup": args.warmup,
        "observable": {
            "final_payload": typed_observable[0],
            "processed_events": typed_observable[1],
            "trace_checksum": typed_observable[2],
        },
        "typed_hypertime": typed_summary,
        "raw_tuple": tuple_summary,
        "typed_to_tuple_median_ratio": (
            typed_summary["median_ns"] / tuple_summary["median_ns"]
        ),
        "interpretation": "Representation overhead only; not a solver speedup claim.",
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()


