"""Reproducible building blocks for the official ARGESIM benchmark suite."""

from .catalog import BENCHMARKS, BenchmarkDefinition, BenchmarkStatus, ModelClass
from .ivp import InitialValueProblem, IntegrationResult, SolverStats
from .models import (
    C01_INITIAL_STATE,
    C01_LOG_LOSS_VALUES,
    C01Parameters,
    C13_INITIAL_STATE,
    C13Parameters,
    c01_problem,
    c01_rhs,
    c01_steady_state,
    c01_task_b,
    c01_task_c,
    c13_linear_rhs,
    c13_nonlinear_rhs,
    c13_task_a,
    c13_task_b,
    c13_task_c,
    solve_c01,
)
from .pde import heat_1d_ivp, heat_sine_exact, heat_sine_initial, wave_1d_ivp
from .solvers import euler, qss1, rk4, rk45

__all__ = [
    "BENCHMARKS",
    "C01_INITIAL_STATE",
    "C01_LOG_LOSS_VALUES",
    "C13_INITIAL_STATE",
    "BenchmarkDefinition",
    "BenchmarkStatus",
    "C01Parameters",
    "C13Parameters",
    "InitialValueProblem",
    "IntegrationResult",
    "ModelClass",
    "SolverStats",
    "c01_problem",
    "c01_rhs",
    "c01_steady_state",
    "c01_task_b",
    "c01_task_c",
    "c13_linear_rhs",
    "c13_nonlinear_rhs",
    "c13_task_a",
    "c13_task_b",
    "c13_task_c",
    "euler",
    "heat_1d_ivp",
    "heat_sine_exact",
    "heat_sine_initial",
    "qss1",
    "rk4",
    "rk45",
    "solve_c01",
    "wave_1d_ivp",
]
