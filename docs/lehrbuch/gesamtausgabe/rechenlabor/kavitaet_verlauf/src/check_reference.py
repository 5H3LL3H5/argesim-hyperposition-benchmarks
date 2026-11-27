"""Independent NumPy collision/streaming plus seven archived macroscopic fields."""

import argparse
import json
from pathlib import Path

import numpy as np
from design import LID, ORIGINAL, N
from fields import raw_field

C = np.array(
    [(0, 0), (1, 0), (0, 1), (-1, 0), (0, -1), (1, 1), (-1, 1), (-1, -1), (1, -1)]
)
W = np.array([4 / 9, 1 / 9, 1 / 9, 1 / 9, 1 / 9, 1 / 36, 1 / 36, 1 / 36, 1 / 36])
OPPOSITE = (0, 3, 4, 1, 2, 7, 8, 5, 6)


def microcheck(n, re, ticks, raw):
    w = W[:, None, None]
    cx, cy = C.T[:, :, None, None]
    f = np.broadcast_to(w, (9, n, n)).copy()
    wall = np.ones((n, n), dtype=bool)
    wall[1:-1, 1:-1] = False
    rate = 1 / (0.5 + 3 * (n - 1) * LID / re)

    def macro(f):
        rho = f.sum(axis=0)
        return rho, (f * cx).sum(axis=0) / rho, (f * cy).sum(axis=0) / rho

    answers = {}
    for k in range(1, max(ticks) + 1):
        rho, u, v = macro(f)
        dot = cx * u + cy * v
        eq = w * rho * (1 + 3 * dot + 4.5 * dot**2 - 1.5 * (u**2 + v**2))
        post = f + rate * (eq - f)
        post[:, wall] = f[list(OPPOSITE)][:, wall]
        topdot = cx[:, :, 0] * LID
        post[:, -1, :] = (
            W[:, None]
            * rho[None, -1, :]
            * (1 + 3 * topdot + 4.5 * topdot**2 - 1.5 * LID**2)
        )
        f = post.copy()
        for j, (dx, dy) in enumerate(C):
            y = slice(max(dy, 0), min(n + dy, n))
            x = slice(max(dx, 0), min(n + dx, n))
            sy = slice(max(-dy, 0), min(n - dy, n))
            sx = slice(max(-dx, 0), min(n - dx, n))
            f[j, y, x] = post[j, sy, sx]
        if k in ticks:
            rho, u, v = macro(f)
            actual = np.stack((rho, u / LID, v / LID))
            ref = np.fromfile(
                raw / f"n{n}_re{re}" / f"feld_{k}.bin", dtype="f8"
            ).reshape(3, n, n)
            answers[k] = np.max(np.abs(actual - ref), axis=(1, 2)).tolist()
    return answers


def verify(inputs, raw, results):
    with np.load(inputs / "daten/testreferenzen.npz") as archive:
        assert tuple(archive["steps"]) == ORIGINAL
        velocities, densities = archive["lbm"], archive["rho"]
        book = {}
        for i, k in enumerate(ORIGINAL):
            uv = raw_field(raw, N, 1000, k)
            density = np.fromfile(
                raw / "n257_re1000" / f"feld_{k}.bin", dtype="f8", count=N * N
            ).reshape(N, N)
            book[k] = [
                float(np.max(np.abs(uv - velocities[i]))),
                float(np.max(np.abs(density - densities[i]))),
            ]
    checked = microcheck(N, 1000, (4, 16, 32, 64), raw)
    checked65 = microcheck(65, 1000, (1, 4, 8, 16), raw)
    out = {
        "archived_velocity_and_density": book,
        "numpy_rho_u_v_fine": checked,
        "numpy_rho_u_v_coarse": checked65,
    }
    assert max(max(row) for table in out.values() for row in table.values()) < 1e-9
    (results / "reference_check.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps(out))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "raw", "results"):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    verify(a.inputs, a.raw, a.results)
