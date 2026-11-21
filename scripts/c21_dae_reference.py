"""Compare the continuous residual RLC model to the switched C21 implementation."""

import json
import math
import sys
from pathlib import Path

import casadi as ca
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argesim_benchmarks import solve_dae
from argesim_benchmarks.models.c21_state_events import (
    C21RLCDiodeParameters,
    simulate_c21_rlc_diode,
)


def main():
    p = C21RLCDiodeParameters()

    def circuit(t, x, v, z):
        i, uc = x[0], x[1]
        ud = z[0]
        diode = ca.if_else(ud > 0, p.i_s * ca.expm1(ud / p.u_t), 0)
        return (
            1e6 * p.l * v[0] + p.r1 * i + ud + ca.sin(2 * math.pi * p.f * t * 1e-6),
            1e6 * p.c * v[1] - i - diode,
            ud - uc - p.r2 * (i + diode),
        )

    times = np.linspace(0, 500e-6, 25001)
    candidates = [
        simulate_c21_rlc_diode(algebraic_state=variable)
        for variable in ("voltage", "current")
    ]
    # Request native outputs directly. Linear interpolation of hybrid samples
    # introduces a separate error at the switching boundaries.
    microseconds = np.unique(
        np.concatenate(
            [times * 1e6, *(np.asarray(run.times) * 1e6 for run in candidates)]
        )
    )
    direct = solve_dae(
        circuit,
        times=microseconds,
        x0=(0, 0),
        xdot0=(0, 0),
        z0=(0,),
        rtol=1e-10,
        atol=1e-12,
    )
    ud = np.array(direct.algebraic)[:, 0]
    times = microseconds * 1e-6
    crossing = np.flatnonzero(ud[:-1] * ud[1:] < 0)
    hits = (
        times[crossing]
        - ud[crossing] * np.diff(times)[crossing] / np.diff(ud)[crossing]
    )
    states = np.array(direct.differential)
    rows = []
    for variable, hybrid in zip(("voltage", "current"), candidates):
        indices = np.searchsorted(microseconds, np.asarray(hybrid.times) * 1e6)
        candidate = np.column_stack(
            (hybrid.current, hybrid.capacitor_voltage, hybrid.diode_voltage)
        )
        err = np.abs(candidate - np.column_stack((states[indices], ud[indices]))).max(
            axis=0
        )
        events = np.array([float(e.time) for e in hybrid.events])
        event_error = (
            float(np.max(np.abs(events - hits))) if len(hits) == len(events) else None
        )
        rows.append(
            {
                "algebraic": variable,
                "max_abs_i_uc_ud": err.tolist(),
                "events": len(events),
                "max_switch_time_error_s": event_error,
                "passed": bool(
                    np.all(err <= [1e-7, 1e-5, 1e-5])
                    and event_error is not None
                    and event_error <= 2e-8
                ),
            }
        )
    report = {
        "casadi": ca.__version__,
        "duration_s": times[-1],
        "samples": len(times),
        "idas_events": len(hits),
        "max_residual": direct.max_residual,
        "comparisons": rows,
    }
    print(json.dumps(report, indent=2, allow_nan=False))
    return 0 if all(r["passed"] for r in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
