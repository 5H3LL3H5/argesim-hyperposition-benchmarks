"""C19R at the published teaching well: source width, boundaries, grid and RK4 step."""

from __future__ import annotations

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
    run()
