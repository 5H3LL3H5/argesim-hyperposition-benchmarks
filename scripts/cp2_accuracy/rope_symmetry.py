"""Measure reflection error with the three published CP2 rope operators."""

import json
from pathlib import Path

import numpy as np
import torch

from argesim_benchmarks.experiments.cp2_operators import load_weights, predict_array
from docs.lehrbuch.studienbuch.material.cp2_genauigkeit.auswerten import (
    dreieck,
    exakte_saite,
    fehler,
    saite,
)

MATERIAL = Path(__file__).resolve().parents[2] / "docs/lehrbuch/studienbuch/material"


def run():
    torch.set_num_threads(1)
    x = np.linspace(0.0, 0.5, 501)
    positions = (0.125, 0.375)
    times = (5, 8)
    inputs = [dreieck(x, position) for position in positions]
    exact = np.array([[exakte_saite(x, t, p) for t in times] for p in positions])
    np.testing.assert_allclose(exact[0], exact[1, :, ::-1], atol=1e-15, rtol=0)
    results = {}
    weights = {
        "original_fno": MATERIAL / "cp2_feldlabor/rope/rope-weights.npz",
        "fine_tuned_fno": MATERIAL / "cp2_genauigkeit/saite_fno_nachtrainiert.npz",
    }
    for name, checkpoint in weights.items():
        case, model = load_weights(checkpoint)
        results[name] = np.array([predict_array(case, model, g) for g in inputs])
    results["linear_fourier"] = np.array([[saite(g, t) for t in times] for g in inputs])
    return {
        "nodes": len(x),
        "length_m": 0.5,
        "pluck_height_m": 0.05,
        "pluck_positions_m": positions,
        "rows": {
            name: [
                {
                    "time_s": t,
                    "relative_l2_percent": [
                        100 * fehler(pred[i, j], exact[i, j])
                        for i in range(len(inputs))
                    ],
                    "max_reflection_difference_mm": float(
                        1000 * abs(pred[0, j] - pred[1, j, ::-1]).max()
                    ),
                }
                for j, t in enumerate(times)
            ]
            for name, pred in results.items()
        },
    }


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, allow_nan=False))
