"""Reproducible experiment evidence records for ARGESIM benchmark runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1


def _git_sha() -> str | None:
    for key in ("ARGESIM_GIT_SHA", "GITHUB_SHA"):
        value = os.environ.get(key)
        if value:
            return value
    try:
        completed = subprocess.run(
            ("git", "rev-parse", "HEAD"),
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    value = completed.stdout.strip()
    return value or None


def _cpu_model() -> str | None:
    proc = Path("/proc/cpuinfo")
    try:
        for line in proc.read_text(encoding="utf-8", errors="replace").splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            if key.strip() in {"model name", "Hardware", "Processor"} and value.strip():
                return value.strip()
    except OSError:
        pass
    value = platform.processor().strip()
    return value or None


def _cpu_affinity() -> tuple[int, ...] | None:
    get_affinity = getattr(os, "sched_getaffinity", None)
    if get_affinity is None:
        return None
    try:
        return tuple(sorted(int(cpu) for cpu in get_affinity(0)))
    except OSError:
        return None


def _linux_governors() -> tuple[str, ...] | None:
    root = Path("/sys/devices/system/cpu")
    governors: set[str] = set()
    try:
        for path in root.glob("cpu[0-9]*/cpufreq/scaling_governor"):
            try:
                value = path.read_text(encoding="ascii").strip()
            except OSError:
                continue
            if value:
                governors.add(value)
    except OSError:
        return None
    return tuple(sorted(governors)) or None


@dataclass(frozen=True)
class RuntimeEnvironment:
    python: str
    implementation: str
    os: str
    kernel: str
    machine: str
    cpu_model: str | None
    logical_cpus: int | None
    cpu_affinity: tuple[int, ...] | None
    cpu_governors: tuple[str, ...] | None

    @classmethod
    def capture(cls) -> "RuntimeEnvironment":
        return cls(
            python=platform.python_version(),
            implementation=platform.python_implementation(),
            os=platform.system(),
            kernel=platform.release(),
            machine=platform.machine(),
            cpu_model=_cpu_model(),
            logical_cpus=os.cpu_count(),
            cpu_affinity=_cpu_affinity(),
            cpu_governors=_linux_governors(),
        )


@dataclass(frozen=True)
class ValidationEvidence:
    reference: str | None = None
    reference_sha256: str | None = None
    metric: str | None = None
    error: float | None = None
    tolerance: float | None = None
    passed: bool | None = None


@dataclass(frozen=True)
class WorkEvidence:
    rhs_evaluations: int | None = None
    events: int | None = None
    accepted_steps: int | None = None
    rejected_steps: int | None = None


@dataclass(frozen=True)
class TimingEvidence:
    warmup: int
    samples: tuple[float, ...]
    median: float | None
    iqr: float | None

    @classmethod
    def from_samples(
        cls, samples: Sequence[float], *, warmup: int = 0
    ) -> "TimingEvidence":
        if warmup < 0:
            raise ValueError("warmup must be non-negative")
        values = tuple(float(value) for value in samples)
        if any(value < 0.0 for value in values):
            raise ValueError("timing samples must be non-negative")
        if not values:
            return cls(warmup=warmup, samples=(), median=None, iqr=None)
        median = statistics.median(values)
        if len(values) < 2:
            iqr = 0.0
        else:
            quartiles = statistics.quantiles(values, n=4, method="inclusive")
            iqr = quartiles[2] - quartiles[0]
        return cls(warmup=warmup, samples=values, median=median, iqr=iqr)


@dataclass(frozen=True)
class ExperimentRecord:
    benchmark: str
    task: str
    solver: str | None
    solver_parameters: Mapping[str, Any] = field(default_factory=dict)
    input_parameters: Mapping[str, Any] = field(default_factory=dict)
    seed: int | None = None
    benchmark_revision: str | None = None
    implementation_git_sha: str | None = None
    environment: RuntimeEnvironment = field(
        default_factory=RuntimeEnvironment.capture
    )
    validation: ValidationEvidence = field(default_factory=ValidationEvidence)
    work: WorkEvidence = field(default_factory=WorkEvidence)
    timing: TimingEvidence = field(
        default_factory=lambda: TimingEvidence.from_samples(())
    )
    schema_version: int = SCHEMA_VERSION

    @classmethod
    def capture(
        cls,
        *,
        benchmark: str,
        task: str,
        solver: str | None = None,
        solver_parameters: Mapping[str, Any] | None = None,
        input_parameters: Mapping[str, Any] | None = None,
        seed: int | None = None,
        benchmark_revision: str | None = None,
        validation: ValidationEvidence | None = None,
        work: WorkEvidence | None = None,
        timing: TimingEvidence | None = None,
    ) -> "ExperimentRecord":
        return cls(
            benchmark=benchmark,
            task=task,
            solver=solver,
            solver_parameters=dict(solver_parameters or {}),
            input_parameters=dict(input_parameters or {}),
            seed=seed,
            benchmark_revision=benchmark_revision,
            implementation_git_sha=_git_sha(),
            validation=validation or ValidationEvidence(),
            work=work or WorkEvidence(),
            timing=timing or TimingEvidence.from_samples(()),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)
