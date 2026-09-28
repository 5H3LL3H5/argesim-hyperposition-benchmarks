"""Isolated, repeatable task timing with strict result parity and artifacts."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from typing import Any

from .evidence import RuntimeEnvironment, _git_sha
from .ivp import IntegrationResult
from .runner import CONTRACTS, _suite_arguments, contract, to_jsonable


PERFORMANCE_SCHEMA_VERSION = 1


def _fingerprint(result: Any) -> str:
    encoded = json.dumps(to_jsonable(result), sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return sha256(encoded).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    descriptor, temporary = tempfile.mkstemp(prefix=".pending-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return sha256(data).hexdigest()


def _rss_peak() -> tuple[int | None, str | None, str | None]:
    try:
        import resource
        peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    except (ImportError, OSError):
        return None, None, "OS does not expose resource.ru_maxrss."
    if sys.platform.startswith("linux"):
        return int(peak) * 1024, "bytes (Linux ru_maxrss in KiB)", None
    if sys.platform == "darwin":
        return int(peak), "bytes (macOS ru_maxrss in bytes)", None
    return None, None, f"ru_maxrss unit is not established on {sys.platform}."


def measure_task(
    benchmark: str, task: str, *, profile: str, warmup: int, repetitions: int,
) -> dict[str, Any]:
    """Run in a fresh process. Exact output parity is an internal check only."""
    if warmup < 0 or repetitions < 9 or repetitions % 2 != 1:
        raise ValueError("warmup must be non-negative; repetitions odd and >= 9")
    definition = contract(benchmark)
    entry = definition.task(task)
    kwargs = _suite_arguments(profile).get((benchmark, task), {})
    import inspect
    bound = inspect.signature(entry.resolve()).bind(**kwargs)
    bound.apply_defaults()
    inputs = to_jsonable(bound.arguments)
    start = datetime.now(timezone.utc).isoformat()
    environment = RuntimeEnvironment.capture()
    raw: list[float] = []
    work_samples: list[dict[str, int | None]] = []
    outcome: dict[str, Any] = {
        "schema_version": PERFORMANCE_SCHEMA_VERSION,
        "benchmark": benchmark, "task": task, "profile": profile,
        "scope": "internal result parity and diagnostic timing",
        "official_performance": False,
        "entrypoint": entry.entrypoint,
        "implementation_git_sha": _git_sha(),
        "definition_source": definition.definition.primary_source,
        "definition_revision": None,
        "input_parameters": inputs,
        "seed": inputs.get("seed") if isinstance(inputs.get("seed"), int) else None,
        "solver": None,
        "solver_parameters": None,
        "started_at_utc": start,
        "environment": to_jsonable(environment),
        "status": "failed", "error": None,
        "validation": {"reference": None, "metric": None, "error": None,
                       "tolerance": None, "passed": None},
        "work": {"accepted_steps": None, "rejected_steps": None,
                 "events": None, "rhs_evaluations": None},
        "work_samples": None,
        "timing": {"warmup": warmup, "repetitions": repetitions,
                   "raw_seconds": raw, "median_seconds": None,
                   "iqr_seconds": None},
        "peak_python_allocation_bytes": None,
        "peak_rss_bytes": None, "peak_rss_unit": None,
        "peak_rss_scope": "fresh benchmark worker process; descendants excluded",
        "unavailable": {
            "definition_revision": "No immutable definition revision is registered.",
            "validation": "No independent reference is checked by this command.",
            "solver": "No uniform solver identifier is exposed by the task contract.",
            "work": "Only a direct IntegrationResult exposes standard counters.",
            "peak_python_allocation_bytes": "Untimed allocation probe did not complete.",
            "peak_rss_bytes": "Timed repetitions did not complete.",
        },
    }
    try:
        baseline = definition.run(task, kwargs)
        outcome["result_type"] = type(baseline).__name__
        reference_hash = _fingerprint(baseline)
        outcome["parity_reference_sha256"] = reference_hash
        for _ in range(warmup):
            if _fingerprint(definition.run(task, kwargs)) != reference_hash:
                raise ValueError("warm-up result differs from parity reference")
        for index in range(repetitions):
            started = time.perf_counter()
            result = definition.run(task, kwargs)
            raw.append(time.perf_counter() - started)
            if _fingerprint(result) != reference_hash:
                raise ValueError(f"timed repetition {index + 1} differs from reference")
            if isinstance(result, IntegrationResult):
                stats = result.stats
                work_samples.append({
                    "accepted_steps": stats.accepted_steps,
                    "rejected_steps": stats.rejected_steps,
                    "rhs_evaluations": stats.rhs_evaluations,
                    "events": None,
                })

        # Python tracing changes runtimes, so allocate a separate untimed probe.
        peak_rss, rss_unit, rss_reason = _rss_peak()
        outcome["peak_rss_bytes"] = peak_rss
        outcome["peak_rss_unit"] = rss_unit
        outcome["unavailable"]["peak_rss_bytes"] = rss_reason
        tracemalloc.start()
        try:
            probe = definition.run(task, kwargs)
            _, peak_python = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        if _fingerprint(probe) != reference_hash:
            raise ValueError("allocation probe differs from parity reference")
        outcome["peak_python_allocation_bytes"] = peak_python
        outcome["unavailable"]["peak_python_allocation_bytes"] = None
        if isinstance(result, IntegrationResult):
            outcome["work_samples"] = work_samples
            outcome["work"] = work_samples[-1]
            outcome["unavailable"]["work"] = (
                "Events are not provided by IntegrationResult.stats."
            )
        values = outcome["timing"]
        values["median_seconds"] = statistics.median(raw)
        q1, _, q3 = statistics.quantiles(raw, n=4, method="inclusive")
        values["iqr_seconds"] = q3 - q1
        outcome["status"] = "passed"
    except Exception as exc:
        outcome["error"] = f"{type(exc).__name__}: {exc}"
        outcome["unavailable"]["timing_summary"] = (
            "Parity or execution failed; raw durations are diagnostic only."
        )
    outcome["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
    return outcome


def run_performance(
    *, output_dir: Path, profile: str = "definition",
    benchmarks: tuple[str, ...] | None = None,
    tasks: tuple[str, ...] | None = None,
    warmup: int = 1, repetitions: int = 9,
    fail_fast: bool = False, timeout_s: float = 3600.0,
) -> dict[str, Any]:
    if warmup < 0 or repetitions < 9 or repetitions % 2 != 1:
        raise ValueError("warmup must be non-negative; repetitions odd and >= 9")
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("timeout_s must be finite and positive")
    _suite_arguments(profile)
    identifiers = tuple(CONTRACTS) if benchmarks is None else tuple(dict.fromkeys(benchmarks))
    selected = []
    for benchmark in identifiers:
        definition = contract(benchmark)
        for task in definition.tasks:
            if tasks is None or f"{benchmark}:{task}" in tasks:
                selected.append((benchmark, task))
    if tasks is not None and set(tasks) != {f"{b}:{t}" for b, t in selected}:
        raise ValueError("--task must name a registered selected benchmark:task")
    if not selected:
        raise ValueError("no benchmark tasks selected")
    output_dir = Path(output_dir)
    if output_dir.exists() and any(output_dir.iterdir()):
        raise ValueError("output_dir must be empty to avoid replacing earlier evidence")
    manifest: dict[str, Any] = {
        "schema_version": PERFORMANCE_SCHEMA_VERSION,
        "profile": profile,
        "scope": "internal result parity and diagnostic timing",
        "official_performance": False,
        "implementation_git_sha": _git_sha(),
        "environment": to_jsonable(RuntimeEnvironment.capture()),
        "warmup": warmup, "repetitions": repetitions,
        "timeout_s": timeout_s,
        "selected_total": len(selected), "completed": 0,
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": [], "passed": 0, "failed": 0,
    }
    for benchmark, task in selected:
        started_utc = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()
        try:
            worker = subprocess.run(
                (sys.executable, "-m", "argesim_benchmarks.performance", "_worker",
                 benchmark, task, profile, str(warmup), str(repetitions)),
                check=True, capture_output=True, text=True, timeout=timeout_s,
            )
            record = json.loads(worker.stdout)
        except (subprocess.SubprocessError, ValueError) as exc:
            detail = getattr(exc, "stderr", None)
            record = {
                "schema_version": PERFORMANCE_SCHEMA_VERSION,
                "benchmark": benchmark, "task": task, "profile": profile,
                "scope": "execution blocked", "official_performance": False,
                "implementation_git_sha": manifest["implementation_git_sha"],
                "environment": manifest["environment"],
                "started_at_utc": started_utc,
                "finished_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "failed", "error": f"{type(exc).__name__}: {exc}",
                "stderr_tail": detail[-2000:] if isinstance(detail, str) else None,
                "input_parameters": to_jsonable(
                    _suite_arguments(profile).get((benchmark, task), {})
                ),
                "definition_revision": None,
                "validation": {"reference": None, "metric": None,
                               "error": None, "tolerance": None, "passed": None},
                "work": {"accepted_steps": None, "rejected_steps": None,
                         "events": None, "rhs_evaluations": None},
                "work_samples": None,
                "timing": {"warmup": warmup, "repetitions": repetitions,
                           "raw_seconds": [], "median_seconds": None,
                           "iqr_seconds": None},
                "peak_python_allocation_bytes": None,
                "peak_rss_bytes": None, "peak_rss_unit": None,
                "peak_rss_scope": "fresh benchmark worker process; descendants excluded",
                "unavailable": {
                    "effective_defaults": "Worker failed before reporting its resolved inputs.",
                    "validation": "No independent reference is checked by this command.",
                    "work": "Worker failed before reporting counters.",
                    "memory": "Worker failed before reporting process memory.",
                },
                "duration_seconds": time.perf_counter() - started,
                "timeout_s": timeout_s,
            }
        name = f"{benchmark}-{task}.json"
        digest = _atomic_json(output_dir / name, record)
        manifest["artifacts"].append({
            "benchmark": benchmark, "task": task, "path": name,
            "sha256": digest, "status": record["status"],
        })
        manifest["passed" if record["status"] == "passed" else "failed"] += 1
        manifest["completed"] = len(manifest["artifacts"])
        manifest["status"] = (
            "complete" if manifest["completed"] == manifest["selected_total"]
            else "partial"
        )
        # A completed manifest is available even if the caller fails mid-suite.
        manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        _atomic_json(output_dir / "manifest.json", manifest)
        if fail_fast and record["status"] != "passed":
            break
    return manifest


def _main() -> int:
    if len(sys.argv) != 7 or sys.argv[1] != "_worker":
        raise SystemExit("performance worker is an internal entrypoint")
    _, _, benchmark, task, profile, warmup, repetitions = sys.argv
    print(json.dumps(measure_task(
        benchmark, task, profile=profile, warmup=int(warmup),
        repetitions=int(repetitions),
    ), sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
