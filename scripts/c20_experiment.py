#!/usr/bin/env python3
"""Reproducible C20 study: fixed generated books, independent failure seeds.

Checkpoints are content-fingerprinted and can be resumed. They retain each
order's throughput time for pooled Task B statistics. The compact report
contains all run metrics and deterministic result hashes; timings are metadata.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import platform
import statistics
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from argesim_benchmarks.experiments.c20_audit import audit_flow, audit_result
from argesim_benchmarks.models.c20_production import C20Production


def source_hashes() -> dict[str, str]:
    paths = [
        *sorted((ROOT / "argesim_benchmarks/models").glob("c20_*.py")),
        ROOT / "argesim_benchmarks/experiments/c20_audit.py",
        Path(__file__),
    ]
    return {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in paths
    }


def encoded(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode()


def run_one(spec: dict, fingerprint: str, checkpoint_dir: str) -> dict:
    path = Path(checkpoint_dir) / (
        f"{spec['order_scenario']}-{spec['plant_scenario']}-"
        f"book{spec['order_seed']}-seed{spec['seed']}.json.gz"
    )
    if path.exists():
        with gzip.open(path, "rt") as stream:
            saved = json.load(stream)
        if saved["fingerprint"] != fingerprint or saved["spec"] != spec:
            raise ValueError(f"stale checkpoint; choose a new directory: {path}")
        return saved
    started = time.perf_counter()
    simulation = C20Production(**spec)
    orders = [job.order for job in simulation.jobs.values()]
    result = simulation.run()
    audit_result(result, orders)
    audit = (
        audit_flow(
            simulation.flow.layout,
            simulation.flow.trace,
            simulation.flow.failures,
            simulation.flow.completed_trips,
        )
        if spec["trace"]
        else None
    )
    data = asdict(result)
    digest = hashlib.sha256(encoded(data)).hexdigest()
    data.pop("orders")
    saved = {
        "fingerprint": fingerprint,
        "spec": spec,
        "metrics": data,
        "result_sha256": digest,
        "order_book_sha256": hashlib.sha256(
            encoded([asdict(o) for o in orders])
        ).hexdigest(),
        "result_audit": "passed",
        "flow_audit": audit,
        "maximum_wip": simulation.maximum_wip,
        "maximum_buffer_reservations": simulation.maximum_buffer_reservations,
        "elapsed_seconds": time.perf_counter() - started,
        "throughput_times": [row.throughput_time for row in result.orders],
    }
    temporary = path.with_suffix(".tmp")
    with gzip.open(temporary, "wt") as stream:
        json.dump(saved, stream, allow_nan=False)
    temporary.replace(path)
    return saved


def distribution(values: list[float]) -> dict[str, float]:
    quartiles = statistics.quantiles(values, n=4, method="inclusive")
    return {
        "median": statistics.median(values),
        "q1": quartiles[0],
        "q3": quartiles[2],
        "iqr": quartiles[2] - quartiles[0],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--orders", type=int, default=5000)
    parser.add_argument("--replications", type=int, default=10)
    parser.add_argument("--book-seeds", type=int, nargs="+", default=[20, 21, 22])
    parser.add_argument("--failure-seed", type=int, default=1000)
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if min(args.orders, args.workers) < 1 or args.replications < 2:
        parser.error("orders/workers must be positive; at least two replications")
    if len(set(args.book_seeds)) != len(args.book_seeds):
        parser.error("order-book seeds must be distinct")
    sources = source_hashes()
    protocol = {
        "order_count": args.orders,
        "replications_per_book": args.replications,
        "book_seeds": args.book_seeds,
        "first_failure_seed": args.failure_seed,
        "flow_trace_scope": "first replication of each book/scenario",
    }
    fingerprint = hashlib.sha256(
        encoded({"sources": sources, "protocol": protocol})
    ).hexdigest()
    args.checkpoints.mkdir(parents=True, exist_ok=True)
    specs = [
        {
            "order_scenario": f"OSc{osc}",
            "plant_scenario": f"PSc{psc}",
            "seed": args.failure_seed + replication,
            "order_seed": book,
            "order_count": args.orders,
            "trace": replication == 0,
        }
        for book in args.book_seeds
        for osc in range(1, 4)
        for psc in range(1, 5)
        for replication in range(args.replications)
    ]
    runs = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(run_one, spec, fingerprint, str(args.checkpoints))
            for spec in specs
        ]
        for future in as_completed(futures):
            run = future.result()
            runs.append(run)
            print(f"{len(runs)}/{len(specs)} {run['spec']} passed", flush=True)
    runs.sort(
        key=lambda r: (
            r["spec"]["order_seed"],
            r["spec"]["order_scenario"],
            r["spec"]["plant_scenario"],
            r["spec"]["seed"],
        )
    )
    summaries = []
    for book in args.book_seeds:
        for osc in range(1, 4):
            for psc in range(1, 5):
                selected = [
                    r
                    for r in runs
                    if r["spec"]["order_seed"] == book
                    and r["spec"]["order_scenario"] == f"OSc{osc}"
                    and r["spec"]["plant_scenario"] == f"PSc{psc}"
                ]
                # Repeated simulations must use byte-identical order books.
                if len({r["order_book_sha256"] for r in selected}) != 1:
                    raise ValueError("order book changed between replications")
                metrics = {
                    key: distribution([r["metrics"][key] for r in selected])
                    for key in (
                        "makespan",
                        "median_throughput_time",
                        "tardy_orders",
                        "total_tardiness",
                        "weighted_tardiness",
                        "max_nok_parts",
                        "max_ok_parts",
                    )
                }
                metrics["pooled_throughput_time"] = distribution(
                    [t for r in selected for t in r["throughput_times"]]
                )
                summaries.append(
                    {
                        "order_seed": book,
                        "order_scenario": f"OSc{osc}",
                        "plant_scenario": f"PSc{psc}",
                        "metrics": metrics,
                    }
                )
    for run in runs:
        del run["throughput_times"]
    report = {
        "benchmark": "C20",
        "model": "physical",
        "protocol": protocol,
        "fingerprint": fingerprint,
        "source_sha256": sources,
        "python": platform.python_version(),
        "runs": runs,
        "summaries": summaries,
        "scope": "generated order books; result recomputation and internal trace replay",
        "external_validation": False,
        "limitations": [
            "Not the unavailable original OB1000/OB1001/OB1002 files.",
            "Controller differs from the published FlexSim solution.",
            "Replay uses the same transcribed layout; it cannot certify its geometry.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(".tmp")
    temporary.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    temporary.replace(args.output)
    print(f"Saved {len(runs)} runs to {args.output}")


if __name__ == "__main__":
    main()
