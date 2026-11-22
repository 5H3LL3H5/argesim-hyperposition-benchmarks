"""A parameter-conditioned residual FNO for the early CP2 cavity.

The trained grid is a tensor product of three lattice sizes, lid speeds and
output steps. Between grid points the fitted affine fields are interpolated
linearly in parameters and space. The Fourier correction receives the actual
parameters. Measurements distinguish new densities from new parameter points.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import torch
from cavity_study import OUT, dataset, metric, speed

from argesim_benchmarks.experiments import cp2_accuracy as a
from argesim_benchmarks.experiments.cp2_parameter_fno import (
    LIDS,
    NODES,
    STEPS,
    features,
    load,
    make_net,
    predict,
)


def run(out):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.manual_seed(1187)
    rng = np.random.default_rng(1187)
    train = np.random.default_rng(4250).uniform(-1, 1, (32, 6))
    val = np.random.default_rng(4251).uniform(-1, 1, (8, 6))
    test = np.random.default_rng(6922).uniform(-1, 1, (12, 6))
    net = make_net()
    opt = torch.optim.Adam(net.parameters(), lr=0.002)
    bank, sets, held = {}, {}, {}
    for i, n in enumerate(NODES):
        for j, lid in enumerate(LIDS):
            d, ys = dataset(np.concatenate([train, val, test]), n, lid, STEPS)
            for k, step in enumerate(STEPS):
                key = f"{i}_{j}_{k}"
                y = ys[step]
                coeff = a.fit_affine(train, y[:32])
                residual = y[:40] - a.affine_predict(d[:40], coeff)
                scale = float(np.sqrt(np.mean(residual[:32, ..., 1:-1, 1:-1] ** 2)))
                bank["coeff_" + key], bank["scale_" + key] = coeff, scale
                sets[key] = (
                    features(d[:40], n, lid, step),
                    torch.from_numpy(residual / scale),
                )
                held[key] = (d[40:], y[40:])
    keys = list(sets)
    best = float("inf")
    for epoch in range(1, 41):
        net.train()
        for key in rng.permutation(keys):
            z, y = sets[key]
            for indices in np.array_split(rng.permutation(32), 2):
                residual = (net(z[indices]) - y[indices])[..., 1:-1, 1:-1]
                opt.zero_grad(set_to_none=True)
                residual.square().mean().backward()
                opt.step()
        net.eval()
        with torch.inference_mode():
            error = np.mean(
                [
                    (net(z[32:]) - y[32:])[..., 1:-1, 1:-1].square().mean().item()
                    for z, y in sets.values()
                ]
            )
        if error < best:
            best, epoch_best = error, epoch
            weights = {
                k: t.detach().cpu().numpy().copy()
                for k, t in net.state_dict().items()
                if torch.is_tensor(t)
            }
    path = out / "kavitaet_familie.npz"
    np.savez_compressed(path, format_version=1, **bank, **weights)
    net, bank = load(path)
    records = []

    def score(n, lid, step, d, y, kind):
        pred, base = predict(net, bank, d, lid, step)
        records.append(
            {
                "n": n,
                "lid": lid,
                "step": step,
                "test": kind,
                "vector": metric(pred, y),
                "affine_vector": metric(base, y),
                "speed": metric(speed(pred), speed(y)),
            }
        )

    for i, j, k in itertools.product(range(3), repeat=3):
        d, y = held[f"{i}_{j}_{k}"]
        score(NODES[i], LIDS[j], STEPS[k], d, y, "new_density")
    for n, lid, step in [
        (17, 0.0875, 16),
        (25, 0.1, 12),
        (21, 0.1, 16),
        (29, 0.1125, 20),
    ]:
        d, y = dataset(test, n, lid, [step])
        score(n, lid, step, d, y[step], "new_parameters")
    d = a.density_samples(17, test)
    z = np.pi * np.linspace(0, 1, 17)
    d += 0.02 * np.outer(np.cos(3 * z), np.cos(4 * z))
    score(17, 0.1, 16, d, a.cavity_snapshots(d, 0.1, [16])[16], "new_density_mode")
    summary = {
        "epochs": 40,
        "best_epoch": epoch_best,
        "seed": 1187,
        "split": [32, 8, 12],
        "results": records,
    }
    (out / "kavitaet_familie.json").write_text(
        json.dumps(summary, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    run(args.out)
