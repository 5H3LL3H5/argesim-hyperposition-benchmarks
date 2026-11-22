"""Train and verify CP2's time-conditioned linear Fourier layer on unseen plucks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from neuralop.layers.spectral_convolution import SpectralConv

from argesim_benchmarks.experiments import (
    cp2_accuracy as a,
)
from argesim_benchmarks.experiments import (
    cp2_fields as f,
)
from argesim_benchmarks.experiments import (
    cp2_operators as old,
)

MAT = Path(__file__).resolve().parents[2] / "docs/lehrbuch/studienbuch/material"
OUT = MAT / "cp2_genauigkeit"


def stats(p, y):
    p, y = np.atleast_2d(p), np.atleast_2d(y)
    err = np.sqrt(np.mean((p - y) ** 2, axis=-1))
    norm = np.sqrt(np.mean(y**2, axis=-1))
    ratio = np.divide(
        err, norm, out=np.full_like(err, np.nan), where=norm > 1e-10 * f.ROPE.h
    )
    return [
        {
            "abs_rms_m": float(e),
            "reference_rms_m": float(s),
            "relative": float(r) if np.isfinite(r) else None,
        }
        for e, s, r in zip(err, norm, ratio)
    ]


def upstream(profile, multipliers):
    """The same trained real multipliers in the upstream Fourier convolution."""
    k = min(len(multipliers), len(profile) - 2)
    layer = SpectralConv(1, 1, (2 * k,), bias=False)
    with torch.inference_mode():
        layer.weight.tensor.zero_()
        layer.weight.tensor[0, 0, 1 : k + 1] = torch.tensor(
            multipliers[:k], dtype=torch.cfloat
        )
        periodic = np.r_[profile, -profile[-2:0:-1]].astype("float32")
        return layer(torch.from_numpy(periodic)[None, None])[
            0, 0, : len(profile)
        ].numpy()


def run(out):
    torch.set_num_threads(1)
    t, k = a.rope_fit()
    np.savez_compressed(out / "saite.npz", times=t, kernels=k)
    _, baseline = old.load_weights(MAT / "cp2_feldlabor/rope/rope-weights.npz")
    tx, ty = f.rope_samples(
        24, np.random.default_rng(np.random.SeedSequence(2027).spawn(3)[2])
    )
    old_smooth = []
    new_smooth = []
    for inp, target in zip(tx, ty):
        old_smooth.extend(
            row["relative"]
            for row in stats(old.predict_array("rope", baseline, inp), target)
        )
        new_smooth.extend(
            row["relative"] for row in stats(a.rope_predict(inp, [5, 8], t, k), target)
        )
    report = {
        "modes": k.shape[1],
        "dt": float(t[1]),
        "train_fields": 96,
        "smooth_old_mean": float(np.mean(old_smooth)),
        "smooth_new_mean": float(np.mean(new_smooth)),
        "plucks": [],
        "sweep": [],
        "ablation": [],
    }
    locations = [0.13, 0.25, 0.37, 0.5, 0.67, 0.81]
    test_times = np.unique(
        np.r_[np.arange(0.037, 8, 0.083), 5.0, 8.0, f.ROPE.length / (2 * f.ROPE.nu)]
    )
    for n in [65, 129, 251, 501]:
        x = np.linspace(0, f.ROPE.length, n)
        for pos in locations:
            ref = a.pluck(x, np.array([5.0, 8.0]), pos)
            inp = a.pluck(x, 0.0, pos)
            pn = a.rope_predict(inp, [5, 8], t, k)
            po = old.predict_array("rope", baseline, inp)
            for at, before, after in zip([5, 8], stats(po, ref), stats(pn, ref)):
                report["plucks"].append(
                    {"n": n, "position": pos, "time": at, "old": before, "new": after}
                )
            truth = a.pluck(x, test_times, pos)
            rows = stats(a.rope_predict(inp, test_times, t, k), truth)
            for at, row in zip(test_times, rows):
                report["sweep"].append(
                    {"n": n, "position": pos, "time": float(at), **row}
                )
    x = np.linspace(0, f.ROPE.length, 501)
    inp = a.pluck(x, 0.0, 0.5)
    ts = np.array([5.0, 8.0])
    ref = a.pluck(x, ts, 0.5)
    before = old.predict_array("rope", baseline, inp)
    after = a.rope_predict(inp, ts, t, k)
    np.savez_compressed(out / "saite_beispiel.npz", x=x, ref=ref, old=before, new=after)
    for modes in [8, 24, 64, 128, 192]:
        for stride in [1, 4]:
            values = a.rope_predict(inp, test_times, t[::stride], k[::stride, :modes])
            errs = stats(values, a.pluck(x, test_times, 0.5))
            report["ablation"].append(
                {
                    "modes": modes,
                    "dt": float(t[stride]),
                    "worst_rms_m": max(r["abs_rms_m"] for r in errs),
                    "mean_rms_m": float(np.mean([r["abs_rms_m"] for r in errs])),
                }
            )
    exact = np.cos(
        t[:, None] * np.arange(1, k.shape[1] + 1) * np.pi * f.ROPE.nu / f.ROPE.length
    )
    report["max_training_knot_multiplier_error"] = float(abs(k - exact).max())
    report["upstream_max_diff_m"] = float(
        max(
            np.max(np.abs(upstream(inp, k[j]) - after[i]))
            for i, j in enumerate([200, 320])
        )
    )
    report["beyond_cutoff"] = {
        "mode": 193,
        "t": 0,
        "relative": stats(
            a.rope_predict(np.sin(193 * np.pi * x / f.ROPE.length), 0, t, k),
            np.sin(193 * np.pi * x / f.ROPE.length),
        )[0]["relative"],
    }
    # Keep every per-trial measurement in a compressed numeric table, with NaN only
    # for relative error at a zero reference. JSON retains the small, readable summary.
    sweep = report.pop("sweep")
    keys = ["n", "position", "time", "abs_rms_m", "reference_rms_m", "relative"]
    table = np.array(
        [[np.nan if r[key] is None else r[key] for key in keys] for r in sweep]
    )
    np.savez_compressed(out / "saite_zeitreihen.npz", columns=keys, rows=table)
    report["sweep"] = {
        "cases": len(sweep),
        "times": len(test_times),
        "max_abs_rms_m": float(table[:, 3].max()),
        "near_zero": int(np.isnan(table[:, -1]).sum()),
    }
    (out / "saite.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    run(args.out)
