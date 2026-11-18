"""Optional second-solver probe for the two published C13R revisions.

Run with Python 3.12 and scipy==1.17.0. This reuses the project's model
equations, but integrates them with SciPy DOP853 at tighter tolerances. It is
an independent numerical integration, not an independent model derivation.
"""

from __future__ import annotations

import json
import math

from argesim_benchmarks.models.c13_crane import (
    C13_INITIAL_STATE,
    C13Parameters,
    c13_linear_rhs,
    c13_nonlinear_rhs,
)


def solve_case(load_damping: float, disturbance: float, *, nonlinear: bool) -> float:
    from scipy.integrate import solve_ivp

    parameters = C13Parameters(dl=load_damping)
    rhs_factory = c13_nonlinear_rhs if nonlinear else c13_linear_rhs
    state = C13_INITIAL_STATE
    for start, end, force_d, force_c in (
        (0.0, 4.0, 0.0, 160.0),
        (4.0, 7.0, disturbance, 160.0),
        (7.0, 15.0, 0.0, 160.0),
        (15.0, 2000.0, 0.0, 0.0),
    ):
        rhs = rhs_factory(parameters, fd=force_d, fc_desired=force_c)
        trajectory = solve_ivp(
            rhs, (start, end), state, method="DOP853",
            rtol=2e-13, atol=2e-14, max_step=1.0,
        )
        if not trajectory.success:
            raise RuntimeError(trajectory.message)
        state = trajectory.y[:, -1]
    angle = math.sin(state[2]) if nonlinear else state[2]
    return float(state[0] + parameters.r * angle)


def main() -> None:
    import scipy

    results = []
    for damping, revision in ((0.01, "2006"), (0.001, "2007")):
        for disturbance in (-750.0, -800.0, -850.0):
            results.append({
                "revision": revision,
                "load_damping_kg_s": damping,
                "disturbance_N": disturbance,
                "linear_load_position_m": solve_case(
                    damping, disturbance, nonlinear=False
                ),
                "nonlinear_load_position_m": solve_case(
                    damping, disturbance, nonlinear=True
                ),
                "net_impulse_Ns": 160.0 * 15.0 + disturbance * 3.0,
            })
    print(json.dumps({
        "method": "SciPy DOP853; same model RHS, second integration engine",
        "scipy": scipy.__version__,
        "rtol": 2e-13,
        "atol": 2e-14,
        "max_step_s": 1.0,
        "final_time_s": 2000.0,
        "results": results,
    }, indent=2, sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    main()
