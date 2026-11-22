"""RATTLE solves the Cartesian C07 position and velocity constraints at every step."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

OUT = (
    Path(__file__).resolve().parents[2]
    / "docs/lehrbuch/studienbuch/material/cp2_genauigkeit"
)
RAY = np.array([np.sin(-np.pi / 12), -np.cos(-np.pi / 12)])
NORMAL = np.array([-RAY[1], RAY[0]])
GRAVITY = np.array([0.0, -9.81])


def advance(q, v, h, length):
    pivot = (1 - length) * RAY
    n = (q - pivot) / np.linalg.norm(q - pivot)
    damp = np.exp(-0.2 / 1.02 * h / 2)
    trial = q - pivot + h * (damp * v + h * GRAVITY / 2)
    transverse = trial - (trial @ n) * n
    rad = length**2 - transverse @ transverse
    if rad <= 0:
        raise ValueError("step too long for continuous constraint root")
    s = transverse + np.sqrt(rad) * n
    half = (pivot + s - q) / h
    tentative = half + h * GRAVITY / 2
    return pivot + s, damp * (tentative - s * (tentative @ s) / length**2)


def solve(dt):
    q = np.array([0.5, -np.cos(np.pi / 6)])
    v = np.zeros(2)
    t = 0.0
    length = 1.0
    events = []
    le = tan = 0.0
    while t < 10 - 1e-13:
        h = min(dt, 10 - t)
        pivot = (1 - length) * RAY
        sign = -1 if length == 1 else 1
        q1, v1 = advance(q, v, h, length)
        if (
            sign * (NORMAL @ (q - pivot)) <= 1e-12
            and sign * (NORMAL @ (q1 - pivot)) > 0
        ):
            lo, hi = 0.0, h
            for _ in range(44):
                mid = (lo + hi) / 2
                probe, _ = advance(q, v, mid, length)
                if sign * (NORMAL @ (probe - pivot)) > 0:
                    hi = mid
                else:
                    lo = mid
            h = (lo + hi) / 2
            q1, v1 = advance(q, v, h, length)
            length = 0.3 if length == 1 else 1.0
            pivot = (1 - length) * RAY
            events.append(t + h)
        q, v, t = q1, v1, t + h
        s = q - pivot
        le = max(le, abs(np.linalg.norm(s) - length))
        tan = max(tan, abs(s @ v))
    return events, le, tan


if __name__ == "__main__":
    expected = np.array(
        [
            z["time"]
            for z in json.loads((OUT / "kapitel.json").read_text())["cartesian"]["hits"]
        ]
    )
    rows = []
    for step in [0.01, 0.005, 0.0025]:
        events, le, tan = solve(step)
        assert len(events) == len(expected)
        rows.append(
            {
                "step": step,
                "events": events,
                "max_time_error": float(abs(expected - events).max()),
                "length_error": float(le),
                "tangency": float(tan),
            }
        )
    (OUT / "rattle.json").write_text(json.dumps(rows, indent=2) + "\n")
