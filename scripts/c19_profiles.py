"""Print C19R task profiles as JSON and independently check homogeneous quadrature with SciPy."""

import argparse
import bisect
import json
import math
import sys
from pathlib import Path

from scipy.integrate import quad

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from argesim_benchmarks.ivp import IntegrationResult
from argesim_benchmarks.models.c19_groundwater import (
    c19_task_a,
    c19_task_b,
    c19_task_c,
    solve_c19,
)

DAY = 86400
TRANSVERSE = range(-20, 21)


def concentration(result: IntegrationResult, t: float, x: int, y: int) -> float:
    """Sample a node on the official 1 m grid, interpolating in time only."""
    idx = (y + 20) * 71 + x + 10
    i = bisect.bisect_left(result.times, t)
    if result.times[i] == t:
        return result.states[i][idx]
    lower, upper = result.times[i - 1], result.times[i]
    weight = (t - lower) / (upper - lower)
    return (1 - weight) * result.states[i - 1][idx] + weight * result.states[i][idx]


def infinite_plane(x: float, y: float, time: float) -> float:
    """Independent time integral of the advected 2D heat kernel, Table 1 units."""
    mass, thickness, porosity, velocity, alpha = 2.0, 10.0, .25, 1e-5, .05
    distance = velocity * time
    r = math.hypot(x, y)
    # z = (u*t - r)/(2*sqrt(alpha*u*t)). Separate the Gaussian so adaptive
    # quadrature still samples its peak when the travelled distance is large.
    upper = (distance - r) / (2 * math.sqrt(alpha * distance))
    if upper <= -28:
        return 0.0
    integral, _ = quad(lambda z: math.exp(-z*z)/math.sqrt(z*z + r/alpha),
                       -28, min(28, upper), points=[0] if upper > 0 else [],
                       epsrel=1e-12, epsabs=1e-15)
    return mass / (2*math.pi*alpha*thickness*porosity*velocity) * math.exp((x-r)/(2*alpha)) * integral


def mesh_study() -> list[dict]:
    """Repeat the archived Task A runs with fixed outer centers, not fixed faces."""
    end = 10 * DAY
    reference = infinite_plane(5, 0, end)
    rows = []
    for spacing, step in ((1., 7200.), (.5, 7200.), (.25, 7200.), (.5, 3600.)):
        nx, ny = round(16 / spacing) + 1, round(8 / spacing) + 1
        run = solve_c19("rk4", nx=nx, ny=ny, dx=spacing, dy=spacing,
                        x_offset=-4., y_offset=-4., t_bound=end, options={"step": step})
        value = run.final_state[round(4 / spacing) * nx + round(9 / spacing)]
        half = spacing / 2
        faces = [-4 - half, 12 + half, -4 - half, 4 + half]
        rows.append({"spacing_m": spacing, "step_s": step, "concentration": value,
                         "outer_faces_west_east_south_north_m": faces,
                         "point_source_m": [0, 0], "well_m": [5, 0], "time_s": end,
                         "infinite_plane": reference, "absolute_error": abs(value - reference)})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mesh-study", action="store_true",
                        help="compare three grids and a halved time step at (5 m, 0), day 10")
    if parser.parse_args().mesh_study:
        print(json.dumps(mesh_study(), indent=2, allow_nan=False))
        return
    spread = c19_task_a(profiles=True)
    for row in spread:
        reference = infinite_plane(50, row["y_m"], row["day"] * DAY)
        if not math.isclose(row["infinite_plane"], reference, rel_tol=1e-10, abs_tol=1e-12):
            raise ArithmeticError(f"C19 homogeneous quadrature mismatch at {row}")
    b = c19_task_b()
    continuous = [{"x_m": x, "y_m": y, "concentration": concentration(b, 100 * DAY, x, y)}
                  for x in (30, 40, 50) for y in TRANSVERSE]
    times = range(0, 150 * DAY + 1, 3600)
    station = [{"hours": t // 3600, "continuous": concentration(b, t, 50, 0)} for t in times]
    del b
    c = c19_task_c()
    for t, row in zip(times, station):
        row["scheduled"] = concentration(c, t, 50, 0)
    print(json.dumps({"concentration_unit": "mg/m^3", "grid_spacing_m": 1,
                      "A_x50": spread, "B_day100": continuous, "C_x50_y0": station},
                     allow_nan=False))


if __name__ == "__main__":
    main()
