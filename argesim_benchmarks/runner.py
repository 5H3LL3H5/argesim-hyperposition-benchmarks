"""Unified benchmark registry and lightweight task dispatcher."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
import importlib
import inspect
from typing import Any, Mapping

from .catalog import BENCHMARKS, benchmark as catalog_benchmark


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
