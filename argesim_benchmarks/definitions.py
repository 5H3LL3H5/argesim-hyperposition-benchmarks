"""Checkpointed definition-profile execution by ARGESIM benchmark group."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import inspect
import json
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

from .evidence import RuntimeEnvironment, _git_sha
from .performance import _atomic_json
from .runner import CONTRACTS, _suite_arguments, contract, to_jsonable


DEFINITION_GROUPS: dict[str, tuple[str, ...]] = {
    "C01-C06": ("C01", "C02", "C03", "C04", "C05", "C06"),
    "C07-C12": ("C07", "C08", "C09", "C10", "C11", "C12"),
    "C13-C18": ("C13", "C14", "C15", "C16", "C17R", "C18"),
    "C19R-C22": ("C19R", "C20", "C21", "C22"),
    "CP1": ("CP1",),
    "CP2": ("CP2",),
}

KNOWN_CONTRACT_GAPS = {
    "CP2:3": (
        "The registered comparison entry does not itself execute the complete "
        "corrected 499-unknown rope study; group success cannot certify CP2 "
        "Task 3 against its full definition."
    ),
}


def _artifact_sha(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _effective_inputs(benchmark: str, task: str) -> dict[str, Any]:
    arguments = _suite_arguments("definition").get((benchmark, task), {})
    bound = inspect.signature(contract(benchmark).task(task).resolve()).bind(
        **arguments
    )
    bound.apply_defaults()
    return to_jsonable(bound.arguments)


def run_definition_group(
    *, group: str, output_dir: Path, resume: bool = False,
    tasks: tuple[str, ...] | None = None, timeout_s: float = 3600.0,
    fail_fast: bool = False,
) -> dict[str, Any]:
    import math

    if group not in DEFINITION_GROUPS:
        raise ValueError(f"unknown definition group {group!r}")
    if not math.isfinite(timeout_s) or timeout_s <= 0:
        raise ValueError("timeout_s must be finite and positive")
    source_sha = _git_sha()
    if source_sha is None:
        raise ValueError(
            "definition evidence requires a clean Git commit or a verified "
            "ARGESIM_GIT_SHA source export"
        )
    all_tasks = tuple(
        (benchmark, task)
        for benchmark in DEFINITION_GROUPS[group]
        for task in CONTRACTS[benchmark].tasks
    )
    selection = set(tasks) if tasks is not None else None
    expected = {f"{benchmark}:{task}" for benchmark, task in all_tasks}
    if selection is not None and (not selection or not selection <= expected):
        raise ValueError(f"tasks must belong to {group}: {sorted(selection - expected)}")
    selected = tuple(
        (benchmark, task) for benchmark, task in all_tasks
        if selection is None or f"{benchmark}:{task}" in selection
    )
    directory = Path(output_dir) / group
    manifest_path = directory / "manifest.json"
    names = [f"{benchmark}:{task}" for benchmark, task in selected]
    if resume:
        if not manifest_path.exists():
            raise ValueError("resume requires an existing group manifest")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("schema_version") != 1 or
                manifest.get("repository_sha") != source_sha or
                manifest.get("selected_tasks") != names or
                manifest.get("profile") != "definition"):
            raise ValueError("manifest source, schema, profile or selection differs")
    else:
        if directory.exists() and any(directory.iterdir()):
            raise ValueError("group directory already contains evidence; use --resume")
        manifest = {
            "schema_version": 1,
            "repository_sha": source_sha,
            "group": group,
            "profile": "definition",
            "scope": "registered definition-profile execution only",
            "selection_covers_full_group": selection is None,
            "known_contract_gaps": {
                key: reason for key, reason in KNOWN_CONTRACT_GAPS.items()
                if key in {f"{b}:{t}" for b, t in all_tasks}
            },
            "selected_tasks": names,
            "registered_group_tasks": len(all_tasks),
            "timeout_s": timeout_s,
            "started_at_utc": datetime.now(timezone.utc).isoformat(),
            "environment": to_jsonable(RuntimeEnvironment.capture()),
            "artifacts": [],
            "completed": 0, "passed": 0, "failed": 0, "blocked": 0,
            "last_successful_task": None,
            "registered_tasks_complete": False,
        }
        _atomic_json(manifest_path, manifest)
    rows = {row["id"]: row for row in manifest["artifacts"]}
    manifest["timeout_s"] = timeout_s
    for benchmark, task in selected:
        identifier = f"{benchmark}:{task}"
        filename = f"{benchmark}-{task}.json"
        path = directory / filename
        prior = rows.get(identifier)
        if (prior is not None and prior["status"] == "passed" and
                path.is_file() and _artifact_sha(path) == prior["sha256"]):
            continue
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()
        inputs = _effective_inputs(benchmark, task)
        try:
            command = (
                sys.executable, "-m", "argesim_benchmarks", "run-suite",
                "--profile", "definition", "--benchmark", benchmark,
                "--task", identifier,
            )
            completed = subprocess.run(
                command, capture_output=True, text=True, timeout=timeout_s,
            )
            report = json.loads(completed.stdout)
            if (report["profile"] != "definition" or report["total"] != 1 or
                    report["tasks"][0]["benchmark"] != benchmark or
                    report["tasks"][0]["task"] != task):
                raise ValueError("child returned an unexpected task report")
            result = report["tasks"][0]
            if result["evidence"]["experiment"]["implementation_git_sha"] != source_sha:
                raise ValueError("child source SHA differs from group manifest")
            record = {
                "schema_version": 1,
                "group": group, "profile": "definition",
                "scope": "registered definition-profile execution only",
                "repository_sha": source_sha,
                "definition_source": contract(benchmark).definition.primary_source,
                "benchmark": benchmark, "task": task,
                "input_parameters": inputs,
                "started_at_utc": started_at,
                "duration_seconds": time.perf_counter() - started,
                "timeout_s": timeout_s,
                "status": result["status"],
                "error": result.get("error"),
                "result": result,
                "stderr_tail": completed.stderr[-2000:] or None,
            }
            if completed.returncode != 0 and record["status"] == "passed":
                raise ValueError("child exited with failure despite a passing task")
        except (subprocess.SubprocessError, ValueError, KeyError) as exc:
            record = {
                "schema_version": 1,
                "group": group, "profile": "definition",
                "scope": "execution blocked", "repository_sha": source_sha,
                "definition_source": contract(benchmark).definition.primary_source,
                "benchmark": benchmark, "task": task,
                "input_parameters": inputs,
                "started_at_utc": started_at,
                "duration_seconds": time.perf_counter() - started,
                "timeout_s": timeout_s,
                "status": "blocked",
                "error": f"{type(exc).__name__}: {exc}",
                "peak_rss_bytes": None,
                "unavailable": {
                    "result": "Child did not produce a valid, complete task report.",
                    "peak_rss_bytes": "Process memory was not sampled before termination.",
                },
            }
        digest = _atomic_json(path, record)
        rows[identifier] = {
            "id": identifier, "path": filename,
            "sha256": digest, "status": record["status"],
        }
        manifest["artifacts"] = [rows[name] for name in names if name in rows]
        manifest["completed"] = len(manifest["artifacts"])
        manifest["passed"] = sum(x["status"] == "passed" for x in rows.values())
        manifest["failed"] = sum(x["status"] == "failed" for x in rows.values())
        manifest["blocked"] = sum(x["status"] == "blocked" for x in rows.values())
        manifest["registered_tasks_complete"] = (
            manifest["selection_covers_full_group"] and
            manifest["completed"] == len(all_tasks) and
            manifest["passed"] == len(all_tasks)
        )
        manifest["last_successful_task"] = next(
            (name for name in reversed(names)
             if name in rows and rows[name]["status"] == "passed"), None
        )
        manifest["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        _atomic_json(manifest_path, manifest)
        if fail_fast and record["status"] != "passed":
            break
    return manifest
