"""Reusable dispatch for the repository's independent ODE solver backends."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from .ivp import InitialValueProblem, IntegrationResult, SolverStats
from .solvers import euler, qss1, qss2, rk4, rk45

SolverOptions = Mapping[str, object]

_ALLOWED_OPTIONS: dict[str, frozenset[str]] = {
    "euler": frozenset({"step", "max_steps"}),
    "rk4": frozenset({"step", "max_steps"}),
    "rk45": frozenset(
        {"initial_step", "rtol", "atol", "min_step", "max_step", "max_steps"}
    ),
    "qss1": frozenset({"quantum", "max_events", "simultaneous_tolerance"}),
    "qss2": frozenset({"quantum", "max_events", "simultaneous_tolerance"}),
}


def normalise_solver_name(method: str) -> str:
    """Return a canonical solver name and reject ambiguous values."""

    if not isinstance(method, str):
        raise TypeError("solver method must be a string")
    name = method.strip().lower()
    if name not in _ALLOWED_OPTIONS:
        supported = ", ".join(_ALLOWED_OPTIONS)
        raise ValueError(f"unsupported solver {method!r}; choose one of: {supported}")
    return name


def _configured_options(
    method: str,
    options: SolverOptions | None,
    defaults: Mapping[str, SolverOptions] | None,
) -> dict[str, object]:
    configured: dict[str, object] = {}
    if defaults is not None:
        configured.update(defaults.get(method, {}))
    if options is not None:
        if not isinstance(options, Mapping):
            raise TypeError("solver options must be a mapping")
        configured.update(options)
    unknown = sorted(set(configured) - _ALLOWED_OPTIONS[method])
    if unknown:
        names = ", ".join(unknown)
        raise TypeError(f"unsupported {method} option(s): {names}")
    return configured


def solve_ivp(
    problem: InitialValueProblem,
    method: str = "rk45",
    *,
    options: SolverOptions | None = None,
    defaults: Mapping[str, SolverOptions] | None = None,
) -> IntegrationResult:
    """Solve an IVP through one explicitly selected backend.

    Model modules can supply method-specific defaults without duplicating dispatch
    logic. User options override those defaults, and misspelled options are rejected
    instead of being silently ignored.
    """

    if not isinstance(problem, InitialValueProblem):
        raise TypeError("problem must be InitialValueProblem")
    name = normalise_solver_name(method)
    configured = _configured_options(name, options, defaults)

    if name in {"euler", "rk4"}:
        if "step" not in configured:
            raise ValueError(f"{name} requires a step option")
        step = configured.pop("step")
        solver = euler if name == "euler" else rk4
        return solver(problem, step, **configured)  # type: ignore[arg-type]
    if name == "rk45":
        return rk45(problem, **configured)  # type: ignore[arg-type]

    if "quantum" not in configured:
        raise ValueError(f"{name} requires a quantum option")
    quantum = configured.pop("quantum")
    solver = qss1 if name == "qss1" else qss2
    return solver(problem, quantum, **configured)  # type: ignore[arg-type]


def merge_solver_options(
    *option_sets: SolverOptions | None,
) -> dict[str, object]:
    """Merge reusable solver option layers from least to most specific."""

    merged: dict[str, object] = {}
    for option_set in option_sets:
        if option_set is None:
            continue
        if not isinstance(option_set, Mapping):
            raise TypeError("solver options must be mappings")
        merged.update(option_set)
    return merged


def merge_integration_results(
    segments: Sequence[IntegrationResult],
    *,
    method: str | None = None,
) -> IntegrationResult:
    """Join contiguous solver segments without duplicating boundary samples."""

    results = tuple(segments)
    if not results:
        raise ValueError("at least one integration segment is required")
    if any(not isinstance(result, IntegrationResult) for result in results):
        raise TypeError("segments must contain IntegrationResult values")
    if method is None:
        names = {result.method for result in results}
        if len(names) != 1:
            raise ValueError("mixed segment methods require an explicit result method")
        result_method = results[0].method
    else:
        result_method = normalise_solver_name(method)

    times = list(results[0].times)
    states = list(results[0].states)
    accepted = results[0].stats.accepted_steps
    rejected = results[0].stats.rejected_steps
    evaluations = results[0].stats.rhs_evaluations
    for previous, current in zip(results, results[1:]):
        if previous.final_time != current.times[0]:
            raise ValueError("integration segments must be contiguous")
        if previous.final_state != current.states[0]:
            raise ValueError("integration segment boundary states must agree")
        times.extend(current.times[1:])
        states.extend(current.states[1:])
        accepted += current.stats.accepted_steps
        rejected += current.stats.rejected_steps
        evaluations += current.stats.rhs_evaluations
    return IntegrationResult(
        result_method,
        tuple(times),
        tuple(states),
        SolverStats(accepted, rejected, evaluations),
    )


__all__ = [
    "SolverOptions",
    "merge_integration_results",
    "merge_solver_options",
    "normalise_solver_name",
    "solve_ivp",
]
