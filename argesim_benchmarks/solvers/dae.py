"""Optional residual-form index-one DAE integration through SUNDIALS IDAS."""

from __future__ import annotations

import itertools
import math
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from ..ivp import IntegrationError, Vector, _finite_vector


@dataclass(frozen=True)
class DAEResult:
    times: tuple[float, ...]
    differential: tuple[Vector, ...]
    algebraic: tuple[Vector, ...]
    derivatives: tuple[Vector, ...]
    max_residual: float


def solve_dae(
    residual: Callable,
    *,
    times: Sequence[float],
    x0: Sequence[float],
    z0: Sequence[float],
    xdot0: Sequence[float],
    rtol: float = 1e-8,
    atol: float = 1e-10,
    initial_residual_tolerance: float = 1e-9,
    max_steps: int = 10000,
) -> DAEResult:
    """Solve F(t,x,xdot,z)=0. The supplied initial tuple must be consistent.

    The callback receives CasADi symbols and returns a column or a sequence
    with len(x0)+len(z0) residuals. Scale equations to comparable units.
    The Jacobian with respect to (z,xdot) must be nonsingular on the branch.
    times includes the initial time followed by strictly increasing outputs.
    """
    try:
        import casadi as ca
        import numpy as np
    except ImportError as exc:
        raise ImportError(
            "Install the optional DAE backend with pip install '.[dae]'"
        ) from exc
    grid = _finite_vector(times, name="times")
    x_init = _finite_vector(x0, name="x0")
    z_init = _finite_vector(z0, name="z0")
    v_init = _finite_vector(xdot0, name="xdot0")
    if len(grid) < 2 or any(a >= b for a, b in itertools.pairwise(grid)):
        raise ValueError("times must contain at least two strictly increasing entries")
    if len(x_init) != len(v_init):
        raise ValueError("x0 and xdot0 dimensions must match")
    if any(
        isinstance(v, bool) or not math.isfinite(v) or v <= 0
        for v in (rtol, atol, initial_residual_tolerance)
    ):
        raise ValueError("positive finite tolerances required")
    if type(max_steps) is not int or max_steps < 1:
        raise ValueError("max_steps must be a positive integer")

    nx, nz = len(x_init), len(z_init)
    t = ca.MX.sym("time")
    x = ca.MX.sym("x", nx)
    aux = ca.MX.sym("aux", nz + nx)
    z, v = aux[:nz], aux[nz:]
    equations = residual(t, x, v, z)
    if isinstance(equations, (list, tuple)):
        equations = ca.vertcat(*equations)
    if equations.shape != (nx + nz, 1):
        raise ValueError("residual must be a column with one equation per unknown")
    evaluate = ca.Function("residual", [t, x, aux], [equations])
    initial_aux = (*z_init, *v_init)
    initial_norm = float(np.max(np.abs(evaluate(grid[0], x_init, initial_aux).full())))
    if not math.isfinite(initial_norm) or initial_norm > initial_residual_tolerance:
        raise ValueError("initial tuple does not satisfy the residual tolerance")
    jac = ca.Function("initial_jacobian", [t, x, aux], [ca.jacobian(equations, aux)])
    matrix = jac(grid[0], x_init, initial_aux).full()
    if not np.isfinite(matrix).all() or np.linalg.slogdet(matrix)[0] == 0:
        raise ValueError("singular initial residual Jacobian in (z, xdot)")

    try:
        backend = ca.integrator(
            "dae",
            "idas",
            {"t": t, "x": x, "z": aux, "ode": v, "alg": equations},
            grid[0],
            list(grid[1:]),
            {
                "abstol": atol,
                "reltol": rtol,
                "calc_ic": True,
                "max_num_steps": max_steps,
            },
        )
        sol = backend(x0=x_init, z0=initial_aux)
    except RuntimeError as exc:
        raise IntegrationError(f"IDAS integration failed: {exc}") from exc
    states = (x_init, *(tuple(row) for row in sol["xf"].full().T.tolist()))
    auxiliary = (initial_aux, *(tuple(row) for row in sol["zf"].full().T.tolist()))
    maximum = initial_norm
    for time_value, state, values in zip(grid, states, auxiliary):
        residual_value = evaluate(time_value, state, values).full()
        if (
            not all(math.isfinite(y) for y in (*state, *values))
            or not np.isfinite(residual_value).all()
        ):
            raise IntegrationError("non-finite IDAS output or residual")
        maximum = max(maximum, float(np.max(np.abs(residual_value))))
    return DAEResult(
        grid,
        states,
        tuple(a[:nz] for a in auxiliary),
        tuple(a[nz:] for a in auxiliary),
        maximum,
    )
