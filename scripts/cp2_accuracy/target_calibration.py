"""Thirteen short reference solves adapt the affine part to a fresh cavity setting."""

from __future__ import annotations

import json

import numpy as np
import torch
from cavity_study import OUT, dataset, metric

from argesim_benchmarks.experiments import cp2_accuracy as a
from argesim_benchmarks.experiments.cp2_parameter_fno import load, predict


def run():
    torch.set_num_threads(1)
    net, bank = load(OUT / "kavitaet_familie.npz")
    axis = np.eye(6)
    probes = np.vstack([np.zeros(6), axis, -axis])
    test = np.random.default_rng(6922).uniform(-1, 1, (12, 6))
    rows = []
    for n, lid, step in [
        (17, 0.0875, 16),
        (25, 0.1, 12),
        (21, 0.1, 16),
        (29, 0.1125, 20),
    ]:
        _, experiment = dataset(probes, n, lid, [step])
        d, reference = dataset(test, n, lid, [step])
        obs = experiment[step]
        coeff = np.concatenate([obs[:1], (obs[1:7] - obs[7:]) / 2])
        calibrated = a.affine_predict(d, coeff)
        blind, base = predict(net, bank, d, lid, step)
        # Carry over the already trained residual; the new probes only replace the
        # affine bypass. Removing its prediction at unit density preserves the anchor.
        flat = np.ones((1, n, n), dtype="float32")
        flat_full, flat_affine = predict(net, bank, flat, lid, step)
        adapted = calibrated + (blind - base) - (flat_full - flat_affine)
        rows.append(
            {
                "n": n,
                "lid": lid,
                "step": step,
                "blind": metric(blind, reference[step]),
                "calibrated": metric(calibrated, reference[step]),
                "adapted": metric(adapted, reference[step]),
            }
        )
    (OUT / "zielkalibrierung.json").write_text(
        json.dumps(rows, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    run()
