"""Reproduce training, fixed-split ablations and transfer checks for the CP2 cavity."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from argesim_benchmarks.experiments import cp2_accuracy as a
from argesim_benchmarks.experiments import cp2_fields as f
from argesim_benchmarks.experiments import cp2_operators as old
from argesim_benchmarks.experiments import cp2_residual_fno as new
from argesim_benchmarks.experiments.cp2_parameter_fno import resize

ROOT = Path(__file__).resolve().parents[2]
MAT = ROOT / "docs/lehrbuch/studienbuch/material"
OUT = MAT / "cp2_genauigkeit"


def metric(p, y):
    diff = (p - y)[..., 1:-1, 1:-1].reshape(len(y), -1)
    ref = y[..., 1:-1, 1:-1].reshape(len(y), -1)
    error = np.linalg.norm(diff, axis=1) / np.linalg.norm(ref, axis=1)
    return {
        "mean": float(error.mean()),
        "max": float(error.max()),
        "median": float(np.median(error)),
        "abs_rms": float(np.sqrt(np.mean(diff**2))),
    }


def speed(v):
    return np.linalg.norm(v, axis=1)


def dataset(ampl, n, lid, steps):
    d = a.density_samples(n, ampl)
    chunks = [
        a.cavity_snapshots(chunk, lid, steps)
        for chunk in np.array_split(d, max(1, (len(d) + 15) // 16))
    ]
    return d, {
        step: np.concatenate([batch[step] for batch in chunks]) for step in steps
    }


def run(out, epochs=80):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    sizes = [96, 16, 24]
    amps = [
        np.random.default_rng(s).uniform(-1, 1, (size, 6))
        for size, s in zip(sizes, np.random.SeedSequence(2027).spawn(3))
    ]
    sets = [dataset(aa, 17, 0.1, [16]) for aa in amps]
    (x, tr), (vx, va), (tx, te) = sets
    y, vy, ty = tr[16], va[16], te[16]
    affine = a.fit_affine(amps[0], y)
    ux, ut = dataset(np.zeros((1, 6)), 17, 0.1, [16])
    _, baseline = old.load_weights(MAT / "cp2_feldlabor/cavity/cavity-weights.npz")
    with torch.inference_mode():
        before = old.forward_field("cavity", baseline, torch.from_numpy(tx)).numpy()[
            :, 0
        ]
        ub = old.forward_field("cavity", baseline, torch.from_numpy(ux)).numpy()[:, 0]
    old_y = speed(ty)
    base = a.affine_predict(tx, affine)
    result = {
        "original": metric(before, old_y),
        "affine": metric(speed(base), old_y),
        "affine_vector": metric(base, ty),
        "uniform_original": metric(ub, speed(ut[16])),
        "runs": [],
        "transfer": [],
        "counts": sizes,
        "scalar_max_difference": float(
            np.max(np.abs(speed(ty[:1])[0] - f.cavity_field(tx[0])))
        ),
    }
    for seed in [2027, 73, 3917]:
        net, scale, epoch = new.train(x, y, vx, vy, affine, seed, epochs)
        p = new.predict(net, tx, affine, scale)
        up = new.predict(net, ux, affine, scale)
        result["runs"].append(
            {
                "seed": seed,
                "epoch": epoch,
                "scale": scale,
                "speed": metric(speed(p), old_y),
                "vector": metric(p, ty),
                "uniform": metric(speed(up), speed(ut[16])),
            }
        )
        if seed == 2027:
            new.save(out / "kavitaet.npz", net, affine, scale)
            np.savez_compressed(
                out / "kavitaet_beispiel.npz",
                ref=ty[0],
                old=before[0],
                affine=base[0],
                new=p[0],
            )
    net, affine, scale = new.load(out / "kavitaet.npz")
    # Blind transfer uses the unchanged checkpoint. Separate affine calibrations show
    # the added information from labels at the target parameters, using fresh fields.
    train_a = np.random.default_rng(4250).uniform(-1, 1, (32, 6))
    test_a = np.random.default_rng(6922).uniform(-1, 1, (12, 6))
    blind17 = new.predict(net, a.density_samples(17, test_a), affine, scale)
    for n, lid in [(17, 0.075), (17, 0.1), (17, 0.125), (25, 0.1), (33, 0.1)]:
        _, train_targets = dataset(train_a, n, lid, [8, 16, 24])
        td, test_targets = dataset(test_a, n, lid, [8, 16, 24])
        blind = resize(blind17, n)
        for step, target in test_targets.items():
            fitted = a.affine_predict(td, a.fit_affine(train_a, train_targets[step]))
            result["transfer"].append(
                {
                    "nodes": n,
                    "lid": lid,
                    "step": step,
                    "blind": metric(blind, target),
                    "calibrated": metric(fitted, target),
                }
            )
    (out / "kavitaet.json").write_text(
        json.dumps(result, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    run(args.out)
