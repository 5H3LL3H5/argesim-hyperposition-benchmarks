"""Fine-tune the published nonlinear FNO without changing its architecture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch

from argesim_benchmarks.experiments import cp2_accuracy as a
from argesim_benchmarks.experiments import cp2_fields as f
from argesim_benchmarks.experiments import cp2_operators as old

MAT = Path(__file__).resolve().parents[2] / "docs/lehrbuch/studienbuch/material"
OUT = MAT / "cp2_genauigkeit"
POSITIONS = (0.13, 0.25, 0.37, 0.5, 0.67, 0.81)
TIMES = (5.0, 8.0)


def data(count, seed):
    rng = np.random.default_rng(seed)
    smooth, target = f.rope_samples(count // 2, rng, nodes=129)
    x = np.linspace(0, f.ROPE.length, 129)
    inputs = []
    outputs = []
    while len(inputs) < count // 2:
        pos = rng.uniform(0.1, 0.9)
        if min(abs(p - pos) for p in POSITIONS) < 0.012:
            continue
        gain = rng.uniform(0.5, 1.5) * rng.choice([-1.0, 1.0])
        inputs.append(gain * a.pluck(x, 0.0, pos))
        outputs.append(gain * a.pluck(x, np.array(TIMES), pos))
    return [
        torch.from_numpy(np.concatenate([l, r]).astype("float32"))
        for l, r in [(smooth, inputs), (target, outputs)]
    ]


def objective(pred, true):
    # Each of the two output fields has a separate scale. The floor avoids
    # overweighting a displacement profile passing close to its rest position.
    scale = true.square().mean(-1).clamp_min((0.08 * f.ROPE.h) ** 2)
    return ((pred - true).square().mean(-1) / scale).mean()


def study(out):
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    x, y = data(96, 4101)
    vx, vy = data(16, 4102)
    smooth, target = f.rope_samples(
        24, np.random.default_rng(np.random.SeedSequence(2027).spawn(3)[2])
    )
    checkpoint = MAT / "cp2_feldlabor/rope/rope-weights.npz"
    runs = []
    for seed in [2027, 73, 3917]:
        _, net = old.load_weights(checkpoint)
        opt = torch.optim.Adam(net.parameters(), lr=0.0005)
        gen = torch.Generator().manual_seed(seed)
        best = float("inf")
        for epoch in range(1, 161):
            net.train()
            for b, indices in enumerate(torch.randperm(96, generator=gen).split(16)):
                stride = 1 + (b + epoch) % 2
                loss = objective(
                    old.forward_field("rope", net, x[indices, ::stride]),
                    y[indices, :, ::stride],
                )
                opt.zero_grad(set_to_none=True)
                loss.backward()
                opt.step()
            net.eval()
            with torch.inference_mode():
                score = objective(old.forward_field("rope", net, vx), vy).item()
            if score < best:
                best, selected = score, epoch
                weights = old.tensor_weights(net)
        torch.nn.Module.load_state_dict(net, weights)
        if seed == 2027:
            old.save_weights(out / "saite_fno_nachtrainiert.npz", "rope", weights)
        with torch.inference_mode():
            pred = old.forward_field("rope", net, torch.from_numpy(smooth)).numpy()
        rows = []
        for n in (65, 129, 251, 501):
            for pos in POSITIONS:
                z = np.linspace(0, f.ROPE.length, n)
                inp = a.pluck(z, 0.0, pos)
                ref = a.pluck(z, np.array(TIMES), pos)
                pred_new = old.predict_array("rope", net, inp)
                rows.append(
                    {
                        "n": n,
                        "position": pos,
                        "relative": [
                            f.relative_l2(pp, yy) for pp, yy in zip(pred_new, ref)
                        ],
                    }
                )
        runs.append(
            {
                "seed": seed,
                "best_epoch": selected,
                "validation_score": best,
                "smooth_mean": old.errors("rope", pred, target)["mean_relative_l2"],
                "plucks": rows,
            }
        )
    report = {
        "extra_train": [48, 48],
        "validation": [8, 8],
        "epochs": 160,
        "positions_excluded": POSITIONS,
        "exclusion_radius": 0.012,
        "runs": runs,
    }
    (out / "saite_nachtraining.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    args.out.mkdir(exist_ok=True, parents=True)
    study(args.out)
