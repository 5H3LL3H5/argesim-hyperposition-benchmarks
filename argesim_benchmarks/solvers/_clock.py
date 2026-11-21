"""Use a local clock for quantizer events and keep absolute times at the API."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
from functools import wraps

from ..ivp import InitialValueProblem, IntegrationResult, Vector


def _on_elapsed_clock(
    integrate: Callable[..., IntegrationResult],
) -> Callable[..., IntegrationResult]:
    @wraps(integrate)
    def solve(
        problem: InitialValueProblem, *args: object, **options: object,
    ) -> IntegrationResult:
        if not isinstance(problem, InitialValueProblem) or problem.t0 == 0.0:
            return integrate(problem, *args, **options)

        duration = problem.t_bound - problem.t0

        def absolute(time: float) -> float:
            return problem.t_bound if time == duration else problem.t0 + time

        def rhs(time: float, state: Sequence[float]) -> Sequence[float]:
            return problem.rhs(absolute(time), state)

        observer = problem._stop_after_step

        def stop(left: float, before: Vector, right: float, after: Vector) -> bool:
            return observer is not None and observer(
                absolute(left), before, absolute(right), after,
            )

        jacobian = options.get("jacobian")
        if callable(jacobian):
            def jacobian_at_absolute_time(time: float, state: Sequence[float]):
                return jacobian(absolute(time), state)

            options["jacobian"] = jacobian_at_absolute_time

        # Keep root tolerances, simultaneity and time accumulation independent
        # of the arbitrary start timestamp. Translate only at the boundaries.
        shifted = replace(
            problem, rhs=rhs, t0=0.0, t_bound=duration,
            _stop_after_step=stop if observer is not None else None,
        )
        result = integrate(shifted, *args, **options)
        return replace(result, times=tuple(absolute(time) for time in result.times))

    return solve
