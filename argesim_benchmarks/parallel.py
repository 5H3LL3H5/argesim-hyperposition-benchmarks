"""Reusable execution and timing support for the ARGESIM CP benchmarks.

The timing layer deliberately keeps model code separate from execution policy.
It preserves input order, uses the same callable and inputs for serial and
parallel runs, and verifies that both paths produce equivalent results.
"""

from __future__ import annotations

import math
import os
import statistics
import time
from collections.abc import Callable, Iterable, Sequence
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from dataclasses import dataclass
from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class OrderedExecutor:
    """Reusable ordered executor; create worker processes/threads only once."""

    def __init__(self, workers: int | None = None, *, backend: str = "thread") -> None:
        worker_count = workers if workers is not None else min(32, os.cpu_count() or 1)
        self.workers = _positive_integer(worker_count, name="workers")
        if backend not in {"serial", "thread", "process"}:
            raise ValueError("backend must be 'serial', 'thread', or 'process'")
        self.backend = backend
        self._executor: ThreadPoolExecutor | ProcessPoolExecutor | None = None

    def __enter__(self) -> OrderedExecutor:
        if self.backend == "thread" and self.workers > 1:
            self._executor = ThreadPoolExecutor(max_workers=self.workers)
        elif self.backend == "process" and self.workers > 1:
            self._executor = ProcessPoolExecutor(max_workers=self.workers)
        return self

    def map(
        self,
        function: Callable[[InputT], OutputT],
        inputs: Iterable[InputT],
    ) -> tuple[OutputT, ...]:
        items = tuple(inputs)
        if self._executor is None:
            return tuple(function(item) for item in items)
        return tuple(self._executor.map(function, items))

    def __exit__(self, _type: object, _value: object, _traceback: object) -> None:
        if self._executor is not None:
            self._executor.shutdown(wait=True)
            self._executor = None


@dataclass(frozen=True)
class TimingSummary:
    """Robust wall-clock summary for repeated executions."""

    samples: tuple[float, ...]

    def __post_init__(self) -> None:
        values = tuple(float(value) for value in self.samples)
        if not values or any(not math.isfinite(value) or value < 0.0 for value in values):
            raise ValueError("timing samples must be non-negative finite values")
        object.__setattr__(self, "samples", values)

    @property
    def median(self) -> float:
        return float(statistics.median(self.samples))

    @property
    def minimum(self) -> float:
        return min(self.samples)

    @property
    def maximum(self) -> float:
        return max(self.samples)


@dataclass(frozen=True)
class ParallelRun(Generic[OutputT]):
    """Results and timings from equivalent serial and parallel workloads."""

    serial_values: tuple[OutputT, ...]
    parallel_values: tuple[OutputT, ...]
    serial_timing: TimingSummary
    parallel_timing: TimingSummary
    workers: int
    backend: str
    maximum_error: float

    @property
    def speedup(self) -> float:
        parallel = self.parallel_timing.median
        return math.inf if parallel == 0.0 else self.serial_timing.median / parallel

    @property
    def efficiency(self) -> float:
        return self.speedup / self.workers


def _positive_integer(value: int, *, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _default_error(left: object, right: object) -> float:
    """Return a recursive maximum absolute error for numeric structures."""

    if isinstance(left, (int, float)) and not isinstance(left, bool):
        if not isinstance(right, (int, float)) or isinstance(right, bool):
            return math.inf
        return abs(float(left) - float(right))
    if isinstance(left, Sequence) and not isinstance(left, (str, bytes)):
        if not isinstance(right, Sequence) or isinstance(right, (str, bytes)):
            return math.inf
        if len(left) != len(right):
            return math.inf
        return max(
            (_default_error(a, b) for a, b in zip(left, right)), default=0.0
        )
    return 0.0 if left == right else math.inf


def ordered_map(
    function: Callable[[InputT], OutputT],
    inputs: Iterable[InputT],
    *,
    workers: int | None = None,
    backend: str = "thread",
) -> tuple[OutputT, ...]:
    """Evaluate a workload concurrently while preserving input order."""

    items = tuple(inputs)
    worker_count = workers if workers is not None else min(32, os.cpu_count() or 1)
    worker_count = _positive_integer(worker_count, name="workers")
    if backend == "serial" or worker_count == 1:
        return tuple(function(item) for item in items)
    executors = {
        "thread": ThreadPoolExecutor,
        "process": ProcessPoolExecutor,
    }
    try:
        executor_type = executors[backend]
    except KeyError as exc:
        raise ValueError("backend must be 'serial', 'thread', or 'process'") from exc
    with executor_type(max_workers=worker_count) as executor:
        return tuple(executor.map(function, items))


def benchmark_ordered_map(
    function: Callable[[InputT], OutputT],
    inputs: Iterable[InputT],
    *,
    workers: int | None = None,
    backend: str = "thread",
    warmups: int = 1,
    repeats: int = 3,
    error: Callable[[OutputT, OutputT], float] | None = None,
    tolerance: float = 0.0,
) -> ParallelRun[OutputT]:
    """Time and validate serial and parallel executions of one workload.

    Timing is intentionally reported, never asserted to be faster: speedup is
    hardware-, interpreter-, and workload-dependent.
    """

    items = tuple(inputs)
    worker_count = workers if workers is not None else min(32, os.cpu_count() or 1)
    worker_count = _positive_integer(worker_count, name="workers")
    if not isinstance(warmups, int) or isinstance(warmups, bool):
        raise TypeError("warmups must be an integer")
    if warmups < 0:
        raise ValueError("warmups must be non-negative")
    warmup_count = warmups
    repeat_count = _positive_integer(repeats, name="repeats")
    if isinstance(tolerance, bool):
        raise TypeError("tolerance must be a real number")
    tolerance = float(tolerance)
    if not math.isfinite(tolerance) or tolerance < 0.0:
        raise ValueError("tolerance must be non-negative and finite")
    if error is not None and not callable(error):
        raise TypeError("error must be callable")
    error_function = error or _default_error

    serial_samples: list[float] = []
    parallel_samples: list[float] = []
    serial_values: tuple[OutputT, ...] = ()
    parallel_values: tuple[OutputT, ...] = ()
    # Keep one pool alive for all warm-ups and measurements.  This measures
    # the reusable execution path rather than repeatedly charging process or
    # thread creation to the simulated workload.
    with OrderedExecutor(worker_count, backend=backend) as executor:
        for _ in range(warmup_count):
            tuple(function(item) for item in items)
            executor.map(function, items)

        for _ in range(repeat_count):
            started = time.perf_counter()
            serial_values = tuple(function(item) for item in items)
            serial_samples.append(time.perf_counter() - started)

            started = time.perf_counter()
            parallel_values = executor.map(function, items)
            parallel_samples.append(time.perf_counter() - started)

    errors = tuple(
        float(error_function(a, b))
        for a, b in zip(serial_values, parallel_values)
    )
    if any(not math.isfinite(value) or value < 0.0 for value in errors):
        raise ValueError("error metric must return non-negative finite values")
    maximum_error = max(errors, default=0.0)
    if len(serial_values) != len(parallel_values) or maximum_error > tolerance:
        raise ValueError(
            "serial and parallel results differ: "
            f"maximum error {maximum_error!r} exceeds {tolerance!r}"
        )
    return ParallelRun(
        serial_values,
        parallel_values,
        TimingSummary(tuple(serial_samples)),
        TimingSummary(tuple(parallel_samples)),
        worker_count,
        backend,
        maximum_error,
    )
