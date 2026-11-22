"""C19R at the published teaching well: source width, boundaries, grid and RK4 step."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import mpmath as mp
import numpy as np

from argesim_benchmarks.models.c19_groundwater import C19Parameters, c19_rhs

OUT = (
    Path(__file__).resolve().parents[2]
    / "docs/lehrbuch/studienbuch/material/cp2_genauigkeit"
)
p = C19Parameters()
END = 10 * 86400


def rhs(c, h, source):
    left = np.concatenate((c[:, :1], c[:, :-1]), axis=1)
    right = np.concatenate((c[:, 1:], c[:, -1:]), axis=1)
    up = np.concatenate((c[1:], c[-1:]), axis=0)
    down = np.concatenate((c[:1], c[:-1]), axis=0)
    dl = c - left
    dr = right - c
    slope = np.where(
        dl * dr > 0,
        np.sign(dl)
        * np.minimum(np.minimum(2 * abs(dl), 2 * abs(dr)), abs(dl + dr) / 2),
        0,
    )
    east = c + slope / 2
    west = np.concatenate((c[:, :1], east[:, :-1]), axis=1)
    return (
        -p.pore_velocity_x / h * (east - west)
        + p.dispersivity * p.pore_velocity_x / h**2 * (left + right + up + down - 4 * c)
        + source
    )


def advance(c, h, step, source):
    floor = 0.0
    for _ in range(round(END / step)):
        k1 = rhs(c, h, source)
        s2 = c + step / 2 * k1
        k2 = rhs(s2, h, source)
        s3 = c + step / 2 * k2
        k3 = rhs(s3, h, source)
        s4 = c + step * k3
        k4 = rhs(s4, h, source)
        c += step / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        floor = min(floor, s2.min(), s3.min(), s4.min(), c.min())
    return c, floor


def linear_weights(centers, point):
    """Distribute a point between the nearest two cell centers."""
    upper = np.searchsorted(centers, point, side="right")
    lower = upper - 1
    fraction = (point - centers[lower]) / (centers[upper] - centers[lower])
    weights = np.zeros(len(centers))
    weights[[lower, upper]] = [1 - fraction, fraction]
    return weights


def fixed_faces():
    west, east, south, north = -4.5, 12.5, -4.5, 4.5
    step = 7200
    rows = []
    for h in (1, 0.5, 0.25):
        x = west + h * (np.arange(round((east - west) / h)) + 0.5)
        y = south + h * (np.arange(round((north - south) / h)) + 0.5)
        faces = [x[0] - h / 2, x[-1] + h / 2, y[0] - h / 2, y[-1] + h / 2]
        np.testing.assert_array_equal(faces, [west, east, south, north])
        wx, wy = linear_weights(x, 0), linear_weights(y, 0)
        np.testing.assert_allclose([wx @ x, wy @ y], 0, atol=1e-15, rtol=0)
        volumes = p.porosity * p.thickness * h**2
        source = np.outer(wy, wx) * (p.mass_rate / volumes)
        mass_rate = source.sum() * volumes
        np.testing.assert_allclose(mass_rate, p.mass_rate, atol=1e-15, rtol=0)
        field, minimum = advance(np.zeros_like(source), h, step, source)
        rows.append(
            {
                "h_m": h,
                "shape_yx": list(field.shape),
                "faces_west_east_south_north_m": faces,
                "mass_rate_mg_s": mass_rate,
                "well_mg_m3": float(wy @ field @ linear_weights(x, 5)),
                "minimum_mg_m3": float(minimum),
            }
        )
    return {
        "step_s": step,
        "time_s": END,
        "source_m": [0, 0],
        "well_m": [5, 0],
        "source_and_well_weights": "bilinear in cell centers",
        "rows": rows,
    }


def study(h, step, expanded=False, wide=False):
    x0, y0 = -8 if expanded else -4, -8 if expanded else -4
    xmax, ymax = 16 if expanded else 12, 8 if expanded else 4
    shape = (round((ymax - y0) / h) + 1, round((xmax - x0) / h) + 1)
    c = np.zeros(shape)
    source = np.zeros_like(c)
    j, i = round(-y0 / h), round(-x0 / h)
    if wide:
        stencil = np.array([0.25, 0.5, 0.25])
        source[j - 1 : j + 2, i - 1 : i + 2] = np.outer(stencil, stencil)
    else:
        source[j, i] = 1
    source *= p.mass_rate / (p.thickness * p.porosity * h * h)
    c, floor = advance(c, h, step, source)
    return {
        "h": h,
        "dt": step,
        "expanded": expanded,
        "wide": wide,
        "minimum": float(floor),
        "concentration": float(c[j, round((5 - x0) / h)]),
        "mass_rate": float(source.sum() * p.porosity * p.thickness * h * h),
    }


def enclosure():
    # Trapezoids of a unimodal positive kernel. On each subinterval with monotone K
    # the error is <= width * variation; the same bound follows for general BV.
    iv = mp.iv
    iv.dps = 32
    x = iv.mpf(5)
    v = iv.mpf(".00001")
    D = iv.mpf(".0000005")

    def kernel(s):
        return (
            iv.mpf(".8")
            * iv.exp(-((x - v * s) ** 2) / (4 * D * s))
            / (4 * iv.pi * D * s)
        )

    a = x * x / (4 * D)
    b = v * v / (4 * D)
    peak = 2 * a / (1 + iv.sqrt(1 + 4 * a * b))
    n = 65536
    h = iv.mpf(END) / n
    summed = sum(kernel(i * h) for i in range(1, n)) + kernel(iv.mpf(END)) / 2
    delta = 2 * h * kernel(peak)
    return [
        math.nextafter(float((h * summed - delta).a), -math.inf),
        math.nextafter(float((h * summed + delta).b), math.inf),
    ]


def run():
    n = 9
    h = 0.5
    d = np.random.default_rng(185).uniform(size=(n, n))
    s = np.zeros_like(d)
    s[4, 4] = p.mass_rate / (p.porosity * p.thickness * h * h)
    reference = c19_rhs(p, n, n, h, h, -2, -2)(0, d.ravel())
    err = float(np.max(abs(rhs(d, h, s).ravel() - reference)))
    assert err < 1e-12
    rows = [study(h, 7200) for h in [1, 0.5, 0.25]]
    rows.extend(
        [
            study(0.25, 3600),
            study(0.25, 3600, True),
            study(0.25, 3600, True, True),
            study(0.125, 1800, True),
            study(0.125, 900, True),
        ]
    )
    report = {
        "implementation_max_difference": err,
        "reference_interval": enclosure(),
        "cases": rows,
    }
    (OUT / "transport.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixed-faces", action="store_true")
    if parser.parse_args().fixed_faces:
        print(json.dumps(fixed_faces(), indent=2, allow_nan=False))
    else:
        run()
