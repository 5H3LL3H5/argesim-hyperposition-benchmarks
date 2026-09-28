"""Unified benchmark registry and lightweight task dispatcher."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from enum import Enum
import importlib
import inspect
import time
from typing import Any, Mapping

from .catalog import BENCHMARKS, benchmark as catalog_benchmark
from .evidence import ExperimentRecord, RuntimeEnvironment, TimingEvidence, _git_sha


class BenchmarkTaskError(RuntimeError):
    """Raised when a benchmark task cannot be resolved or executed."""


class BenchmarkTask:
    def __init__(self, name: str, entrypoint: str) -> None:
        self.name = name
        self.entrypoint = entrypoint

    def resolve(self):
        module_name, function_name = self.entrypoint.rsplit(":", 1)
        module = importlib.import_module(module_name)
        try:
            return getattr(module, function_name)
        except AttributeError as exc:
            raise BenchmarkTaskError(
                f"entrypoint {self.entrypoint!r} does not exist"
            ) from exc


class BenchmarkContract:
    def __init__(self, identifier: str, tasks: Mapping[str, str]) -> None:
        self.identifier = identifier
        self.tasks = {
            name: BenchmarkTask(name, entrypoint)
            for name, entrypoint in tasks.items()
        }

    @property
    def definition(self):
        return catalog_benchmark(self.identifier)

    def task(self, name: str) -> BenchmarkTask:
        try:
            return self.tasks[name]
        except KeyError as exc:
            raise BenchmarkTaskError(
                f"unknown task {name!r} for {self.identifier}"
            ) from exc

    def run(self, name: str, kwargs: Mapping[str, Any] | None = None) -> Any:
        function = self.task(name).resolve()
        arguments = dict(kwargs or {})
        try:
            inspect.signature(function).bind(**arguments)
        except TypeError as exc:
            raise BenchmarkTaskError(
                f"invalid arguments for {self.identifier}:{name}: {exc}"
            ) from exc
        return function(**arguments)


def _m(function: str) -> str:
    return f"argesim_benchmarks.models:{function}"


_TASKS: dict[str, dict[str, str]] = {
    "C01": {"A": _m("solve_c01"), "B": _m("c01_task_b"), "C": _m("c01_task_c")},
    "C02": {"main": _m("solve_c02")},
    "C03": {"A": _m("c03_task_a"), "B": _m("c03_task_b"), "C": _m("c03_task_c")},
    "C04": {"run": _m("run_c04"), "compare": _m("c04_compare_strategies")},
    "C05": {"simulate": _m("simulate_c05"), "validate": _m("c05_validate")},
    "C06": {
        "A": _m("solve_c06_task_a"),
        "B": _m("solve_c06_task_b"),
        "C": _m("solve_c06_task_c"),
    },
    "C07": {"A": _m("c07_task_a"), "B": _m("c07_task_b"), "C": _m("c07_task_c")},
    "C08": {"replication": _m("run_c08_replication"), "C": _m("c08_task_c")},
    "C09": {"run": _m("c09_run_benchmark"), "validate": _m("c09_validate")},
    "C10": {"A": _m("c10_task_a"), "B": _m("c10_task_b")},
    "C11": {
        "A": _m("c11_task_a"),
        "B": _m("c11_task_b"),
        "C": _m("c11_task_c"),
        "main": _m("solve_c11"),
    },
    "C12": {"A": _m("c12_task_a"), "B": _m("c12_task_b"), "C": _m("c12_task_c")},
    "C13": {
        "A": _m("c13_task_a"),
        "B": _m("c13_task_b_study"),
        "C": _m("c13_task_c_study"),
    },
    "C14": {
        "A1": _m("c14_task_a1"),
        "A2": _m("c14_task_a2"),
        "B1": _m("c14_task_b1"),
        "B2": _m("c14_task_b2"),
        "C1": _m("c14_task_c1"),
        "C2": _m("c14_task_c2"),
    },
    "C15": {"A": _m("c15_task_a"), "B": _m("c15_task_b"), "C": _m("c15_task_c")},
    "C16": {"A": _m("c16_task_a"), "B": _m("c16_task_b"), "C": _m("c16_task_c")},
    "C17R": {
        "task1": _m("c17_task1_parameter_study"),
        "compare": _m("c17_compare_ca_ode"),
        "ca": _m("simulate_c17_ca"),
        "ode": _m("simulate_c17_ode_intervention"),
    },
    "C18": {"all": _m("run_c18_tasks")},
    "C19R": {"A": _m("c19_task_a"), "B": _m("c19_task_b"), "C": _m("c19_task_c")},
    "C20": {
        "replication": _m("run_c20_replication"),
        "experiment": _m("run_c20_experiment"),
    },
    "C21": {
        "event-contact": _m("c21_event_contact_study"),
        "dynamic-contact": _m("c21_dynamic_contact_study"),
        "pendulum-basic": _m("c21_rotating_pendulum_basic_study"),
        "pendulum-kick": _m("c21_rotating_pendulum_kick_study"),
        "rlc-diode": _m("simulate_c21_rlc_diode"),
    },
    "C22": {
        "basic": _m("c22_basic"),
        "jockeying": _m("c22_jockeying"),
        "reneging": _m("c22_reneging"),
        "classing": _m("c22_classing"),
    },
    "CP1": {
        "A": _m("cp1_task_a_study"),
        "B": _m("cp1_task_b_compare_execution"),
        "B-validate": _m("cp1_task_b_validate"),
        "C": _m("cp1_task_c_solve"),
    },
    "CP2": {
        "1": _m("cp2_task1_monte_carlo"),
        "2": _m("cp2_task2_lid_driven_cavity"),
        "3": _m("cp2_task3_compare"),
    },
}


CONTRACTS: dict[str, BenchmarkContract] = {
    identifier: BenchmarkContract(identifier, tasks)
    for identifier, tasks in _TASKS.items()
}


def contract(identifier: str) -> BenchmarkContract:
    try:
        return CONTRACTS[identifier]
    except KeyError as exc:
        raise BenchmarkTaskError(f"unknown benchmark {identifier!r}") from exc


def to_jsonable(value: Any) -> Any:
    if is_dataclass(value):
        return {key: to_jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): to_jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [to_jsonable(item) for item in value]
    if isinstance(value, set):
        converted = [to_jsonable(item) for item in value]
        return sorted(converted, key=repr)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if hasattr(value, "__dict__"):
        return {
            key: to_jsonable(item)
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return repr(value)


def verify_registry_complete() -> None:
    catalog_ids = {entry.identifier for entry in BENCHMARKS}
    registry_ids = set(CONTRACTS)
    if registry_ids != catalog_ids:
        missing = sorted(catalog_ids - registry_ids)
        extra = sorted(registry_ids - catalog_ids)
        raise AssertionError(
            f"benchmark registry mismatch: missing={missing}, extra={extra}"
        )
    for identifier, benchmark_contract in CONTRACTS.items():
        if not benchmark_contract.tasks:
            raise AssertionError(f"{identifier} has no registered tasks")


def _suite_arguments(profile: str) -> dict[tuple[str, str], dict[str, Any]]:
    """Explicit inputs for mandatory arguments and bounded smoke workloads."""
    from .models.c17_sir_epidemic import C17Intervention

    required = {
        ("C02", "main"): {"num_pallets": 10},
        ("C04", "run"): {"strategy": "put-back"},
        ("C08", "replication"): {"eastmax": 3, "westmax": 3},
        ("C17R", "ode"): {
            "intervention": C17Intervention(threshold_fraction=0.1, soft_factor=0.5)
        },
        ("C20", "replication"): {
            "order_scenario": "OSc1", "plant_scenario": "PSc1"
        },
    }
    if profile == "definition":
        return required
    if profile != "smoke":
        raise ValueError("profile must be 'smoke' or 'definition'")
    bounded = {
        ("C04", "compare"): {"replications": 1},
        ("C08", "C"): {"duration": 600, "independent_replications": 2,
                         "paired_replications": 2, "starting_seeds": (42,)},
        ("C12", "C"): {"n_samples": 20},
        ("C14", "A2"): {"runs": 1},
        ("C14", "B2"): {"runs": 1},
        ("C14", "C1"): {"runs": 1},
        ("C14", "C2"): {"runs": 1},
        ("C15", "C"): {"iterations": 2},
        ("C16", "A"): {"runs": 1, "years": 6},
        ("C16", "B"): {"runs": 1, "years": 1, "tax_rates": (0.2,)},
        ("C16", "C"): {"runs": 1, "years": 1, "k_values": (4.0,)},
        ("C17R", "task1"): {"steps": 2, "replications": 1},
        ("C17R", "compare"): {"steps": 2, "replications": 1},
        ("C17R", "ca"): {"steps": 2},
        ("C17R", "ode"): {"t_bound": 2.0},
        ("C18", "all"): {"epochs": 2},
        ("C19R", "A"): {"nx": 3, "ny": 3},
        ("C19R", "B"): {"nx": 3, "ny": 3},
        ("C19R", "C"): {"nx": 3, "ny": 3},
        ("C20", "replication"): {"order_count": 10},
        ("C20", "experiment"): {"order_count": 10, "replications": 10},
        ("C21", "dynamic-contact"): {"t_bound": 0.2},
        ("CP1", "A"): {"samples": 2, "workers": 1, "t_bound": 0.1},
        ("CP1", "B"): {"t_bound": 0.1, "step": 0.05, "workers": 1},
        ("CP1", "C"): {"interior_points": 9, "t_bound": 0.1,
                        "step": 0.05, "output_step": 0.05},
        ("CP2", "1"): {"samples": 2, "workers": 1, "t_bound": 0.1},
        ("CP2", "2"): {"nx": 17, "iterations": 20},
    }
    for key, overrides in bounded.items():
        required.setdefault(key, {}).update(overrides)
    return required


def run_suite(
    *, profile: str = "smoke", benchmarks: tuple[str, ...] | None = None,
    tasks: tuple[str, ...] | None = None,
    fail_fast: bool = False,
) -> dict[str, Any]:
    """Execute each registered task once, reporting failures individually.

    Success establishes execution only. No reference validation or evidence
    status is inferred from these results. The definition profile may be very
    expensive (notably CP2's 350,000 LBM iterations).
    """
    verify_registry_complete()
    inputs = _suite_arguments(profile)
    identifiers = tuple(CONTRACTS) if benchmarks is None else tuple(benchmarks)
    for identifier in identifiers:
        contract(identifier)
    selected = set(tasks) if tasks is not None else None
    registered = {
        f"{identifier}:{name}"
        for identifier in identifiers for name in CONTRACTS[identifier].tasks
    }
    if selected is not None and not selected <= registered:
        raise BenchmarkTaskError(
            f"unknown selected tasks: {sorted(selected - registered)}"
        )
    repository_sha = _git_sha()
    environment = RuntimeEnvironment.capture()
    records: list[dict[str, Any]] = []
    for identifier in identifiers:
        for name in CONTRACTS[identifier].tasks:
            if selected is not None and f"{identifier}:{name}" not in selected:
                continue
            kwargs = inputs.get((identifier, name), {})
            task = CONTRACTS[identifier].task(name)
            effective_inputs = to_jsonable(kwargs)
            defaults_unavailable = None
            resolved_signature = False
            started_at_utc = datetime.now(timezone.utc).isoformat()
            started = time.perf_counter()
            record: dict[str, Any] = {
                "benchmark": identifier, "task": name,
                "arguments": to_jsonable(kwargs), "status": "passed",
            }
            try:
                signature = inspect.signature(task.resolve())
                bound = signature.bind(**kwargs)
                bound.apply_defaults()
                effective_inputs = to_jsonable(bound.arguments)
                resolved_signature = True
                result = contract(identifier).run(name, kwargs)
                record["result_type"] = type(result).__name__
            except Exception as exc:
                record["status"] = "failed"
                record["error"] = f"{type(exc).__name__}: {exc}"
                if not resolved_signature:
                    defaults_unavailable = (
                        "Entrypoint/signature resolution failed; "
                        "only supplied arguments were captured."
                    )
            finally:
                record["seconds"] = time.perf_counter() - started
            experiment = ExperimentRecord.capture(
                benchmark=identifier, task=name,
                input_parameters=effective_inputs,
                seed=(effective_inputs.get("seed")
                      if isinstance(effective_inputs.get("seed"), int) else None),
                timing=TimingEvidence(
                    warmup=0, samples=(record["seconds"],), unit="seconds",
                    median=record["seconds"], iqr=None,
                ),
                environment=environment,
                implementation_git_sha=repository_sha,
            ).to_dict()
            # A suite run establishes execution only. Missing measurements and
            # independent references must remain explicit, never synthetic zeroes.
            record["evidence"] = {
                "schema_version": 1,
                "profile": profile,
                "scope": "execution only",
                "started_at_utc": started_at_utc,
                "duration_seconds": record["seconds"],
                "status": record["status"],
                "error": record.get("error"),
                "entrypoint": task.entrypoint,
                "experiment": experiment,
                "unavailable": {
                    "repository_sha": (
                        "No clean Git commit could be identified for this source tree."
                        if repository_sha is None else None
                    ),
                    "benchmark_revision": (
                        "No immutable definition revision is registered."
                    ),
                    "validation": "No independent oracle is executed by run-suite.",
                    "work": (
                        "The task interface does not expose standardized solver counters."
                    ),
                    "peak_python_allocation_bytes": (
                        "Allocation tracing is not enabled for execution runs."
                    ),
                    "peak_rss": "Per-task peak RSS is not measured for execution runs.",
                    "solver": (
                        "No uniform solver identifier is exposed by the task contract."
                    ),
                    "seed": (
                        "A scalar seed is not in the effective inputs."
                        if experiment["seed"] is None else None
                    ),
                    "effective_defaults": defaults_unavailable,
                },
                "peak_python_allocation_bytes": None,
                "peak_rss": None,
                "peak_rss_unit": None,
            }
            records.append(record)
            if fail_fast and record["status"] == "failed":
                break
        if fail_fast and records and records[-1]["status"] == "failed":
            break
    return {
        "profile": profile, "scope": "execution only", "tasks": records,
        "passed": sum(row["status"] == "passed" for row in records),
        "failed": sum(row["status"] == "failed" for row in records),
        "total": len(records),
    }
