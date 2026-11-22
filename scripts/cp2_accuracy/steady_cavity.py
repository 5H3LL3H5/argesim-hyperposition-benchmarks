"""Reproduce the long CP2 cavity reference and compare two signed centreline profiles."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path

import numpy as np

from argesim_benchmarks.models import cp2_parallel_and_distributed as cp2

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/lehrbuch/studienbuch/material/cp2_genauigkeit"
STOPS = {
    17: (1, 7, 16),
    65: (16, 17500, 35000, 70000, 80000, 85000, 87500),
    129: (16, 35000, 70000, 140000, 160000, 170000, 175000),
    257: (16, 500, 30000, 70000, 140000, 210000, 280000, 320000, 340000, 350000),
}
# Re=1000, Ghia/Ghia/Shin, JCP 48 (1982) Tables I and II, interior probes.
U = np.array(
    [
        [0.1719, -0.38289],
        [0.2813, -0.27805],
        [0.5, -0.06080],
        [0.6172, 0.05702],
        [0.7344, 0.18719],
        [0.9766, 0.65928],
    ]
)
V = np.array(
    [
        [0.2266, 0.33075],
        [0.2344, 0.32235],
        [0.5, 0.02526],
        [0.8047, -0.31966],
        [0.8594, -0.42665],
        [0.9063, -0.51500],
    ]
)


def read(raw, n, s):
    return np.fromfile(raw / f"n{n}_{s}.bin", dtype=np.float64).reshape(n, n, 3)


def compute(raw):
    exe = raw / "cavity_ref"
    subprocess.run(
        [
            "c++",
            "-std=c++17",
            "-O3",
            "-march=native",
            "-fopenmp-simd",
            str(Path(__file__).with_name("cavity_reference.cpp")),
            "-o",
            str(exe),
        ],
        check=True,
    )
    for n, stops in STOPS.items():
        subprocess.run(
            [str(exe), str(n), ".1", str(raw / f"n{n}_"), *map(str, stops)], check=True
        )


def summarize(raw, out):
    grid = cp2.cp2_lbm_initial_state(17)
    omega = cp2.cp2_lbm_relaxation(17)
    diffs = []
    for i in range(1, 17):
        grid = cp2.cp2_lbm_step(grid, 17, omega, 0.1)
        if i in STOPS[17]:
            pop = np.array(grid)
            rho = pop.sum(-1)
            uv = (
                np.einsum("...k,kd->...d", pop, cp2.CP2_LBM_VELOCITIES) / rho[..., None]
            )
            uv[-1] = [0.1, 0]
            diffs.append(float(abs(read(raw, 17, i) - np.dstack((rho, uv))).max()))
    if max(diffs) > 1e-11:
        raise ValueError("native/scalar mismatch")
    results = {
        "reference_doi": "10.1016/0021-9991(82)90058-4",
        "small_reference_max": max(diffs),
        "last_window_convective": 3.90625,
        "grids": [],
    }
    profiles = {"ghia_u": U, "ghia_v": V}
    for n, stops in STOPS.items():
        if n == 17:
            continue
        final = read(raw, n, stops[-1])
        prev = read(raw, n, stops[-2])
        vel = final[1:-1, 1:-1, 1:]
        z = np.linspace(0, 1, n)
        u = final[:, n // 2, 1] / 0.1
        v = final[n // 2, :, 2] / 0.1
        profiles[f"profile_{n}"] = np.stack((z, u, v))
        eu = np.interp(U[:, 0], z, u) - U[:, 1]
        ev = np.interp(V[:, 0], z, v) - V[:, 1]
        convergence = []
        for step in stops[1:]:
            q = read(raw, n, step)[1:-1, 1:-1, 1:]
            convergence.append(
                [step, float(np.linalg.norm(q - vel) / np.linalg.norm(vel))]
            )
        results["grids"].append(
            {
                "n": n,
                "steps": stops[-1],
                "t_convective": stops[-1] * 0.1 / (n - 1),
                "relative_last_window": float(
                    np.linalg.norm(vel - prev[1:-1, 1:-1, 1:]) / np.linalg.norm(vel)
                ),
                "u_rms": float(np.sqrt(np.mean(eu**2))),
                "v_rms": float(np.sqrt(np.mean(ev**2))),
                "u_max": float(abs(eu).max()),
                "v_max": float(abs(ev).max()),
                "mass_ratio": float(final[:, :, 0].mean()),
                "approach_to_last": convergence,
            }
        )
    np.savez_compressed(out / "kavitaet_profile.npz", **profiles)
    (out / "kavitaet_stationaer.json").write_text(
        json.dumps(results, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw", type=Path, help="read existing native snapshot directory"
    )
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    if args.raw:
        summarize(args.raw, args.out)
    else:
        with tempfile.TemporaryDirectory() as name:
            temp = Path(name)
            compute(temp)
            summarize(temp, args.out)
