"""Controlled CP2 rope FNO ablation: A0, B1, B2, B3.

Run: python -m argesim_benchmarks.experiments.cp2_fno_ab --out results/cp2-ab
Requires the optional neuraloperator extra. No benchmark evidence is committed.
"""
from __future__ import annotations

import argparse
import json
import platform
import time
from pathlib import Path

import numpy as np
import torch

from . import cp2_fields as fields
from . import cp2_operators as baseline


VARIANTS = ("A0", "B1", "B2", "B3")
SPLIT_SIZES = (96, 16, 24)
EVAL_NODES = (65, 501)


def triangle_samples(count: int, rng: np.random.Generator, nodes: int = 65):
    """Piecewise-linear plucks with randomized peak location and signed amplitude.

    Propagation uses the exact odd-periodic d'Alembert solution for fixed ends.
    This distribution is intentionally disjoint from the canonical centered pluck.
    """
    x = np.linspace(0.0, fields.ROPE.length, nodes)
    peaks = rng.uniform(0.2, 0.8, size=count) * fields.ROPE.length
    amplitudes = rng.uniform(0.35, 1.25, size=count) * fields.ROPE.h
    signs = rng.choice((-1.0, 1.0), size=count)
    profiles = []
    targets = []
    for peak, amplitude, sign in zip(peaks, amplitudes, signs):
        def periodic_odd(z):
            q = np.mod(z + fields.ROPE.length, 2 * fields.ROPE.length) - fields.ROPE.length
            magnitude = np.abs(q)
            shape = np.where(magnitude <= peak, magnitude / peak,
                             (fields.ROPE.length - magnitude) / (fields.ROPE.length - peak))
            return np.sign(q) * sign * amplitude * shape
        profiles.append(periodic_odd(x))
        targets.append(np.stack([
            0.5 * (periodic_odd(x - fields.ROPE.nu * t) +
                   periodic_odd(x + fields.ROPE.nu * t))
            for t in fields.PROFILE_TIMES
        ]))
    return np.asarray(profiles, dtype=np.float32), np.asarray(targets, dtype=np.float32)


def mixed_samples(count: int, rng: np.random.Generator):
    """Half smooth modes and half randomized plucks, with exact references."""
    smooth_count = count // 2
    a, b = fields.rope_samples(smooth_count, rng)
    c, d = triangle_samples(count - smooth_count, rng)
    order = rng.permutation(count)
    return np.concatenate((a, c))[order], np.concatenate((b, d))[order]


def make_splits(seed: int, variant: str):
    """Distinct RNG streams for train, validation and in-distribution test."""
    streams = np.random.SeedSequence(seed).spawn(3)
    sampler = fields.rope_samples if variant == "A0" else mixed_samples
    return [sampler(n, np.random.default_rng(stream))
            for n, stream in zip(SPLIT_SIZES, streams)]


def gradient_loss(prediction: torch.Tensor, target: torch.Tensor):
    """Scale-invariant spatial H1-seminorm penalty, never applied to validation."""
    scale = fields.ROPE.h
    difference = (prediction[..., 1:] - prediction[..., :-1]) / scale
    reference = (target[..., 1:] - target[..., :-1]) / scale
    return (difference - reference).square().mean()


def make_model(variant: str):
    if variant not in VARIANTS:
        raise ValueError(f"unknown variant: {variant}")
    if variant != "B2":
        return baseline.make_model("rope")
    from neuralop.models import FNO
    return FNO(n_modes=(48,), in_channels=1, out_channels=2,
               hidden_channels=24, n_layers=3, positional_embedding=None)


def score(model, inputs, targets):
    with torch.inference_mode():
        predicted = baseline.forward_field("rope", model, inputs).numpy()
    return baseline.errors("rope", predicted, targets.numpy())


def train_variant(variant: str, seed: int, epochs: int):
    if seed < 0 or epochs < 1:
        raise ValueError("seed must be nonnegative and epochs positive")
    torch.manual_seed(seed)
    data_start = time.perf_counter()
    splits = make_splits(seed, variant)
    data_seconds = time.perf_counter() - data_start
    (x, y), (vx, vy), (tx, ty) = [
        (torch.from_numpy(a), torch.from_numpy(b)) for a, b in splits
    ]
    model = make_model(variant)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    generator = torch.Generator().manual_seed(seed)
    best_error = float("inf")
    best_epoch = 0
    best_weights = None
    start = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        for indices in torch.randperm(len(x), generator=generator).split(16):
            prediction = baseline.forward_field("rope", model, x[indices])
            residual = (prediction - y[indices]) / fields.ROPE.h
            loss = residual.square().mean()
            if variant == "B3":
                loss = loss + 0.1 * gradient_loss(prediction, y[indices])
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        model.eval()
        error = score(model, vx, vy)["mean_relative_l2"]
        if np.isfinite(error) and error < best_error:
            best_error, best_epoch = error, epoch
            best_weights = baseline.tensor_weights(model)
    train_seconds = time.perf_counter() - start
    if best_weights is None:
        raise ArithmeticError("no finite validation checkpoint")
    model.load_state_dict(best_weights)
    model.eval()
    start = time.perf_counter()
    test = score(model, tx, ty)
    inference_seconds = time.perf_counter() - start
    canonical = {}
    for nodes in EVAL_NODES:
        initial, reference, newmark = fields.canonical_rope(nodes)
        prediction = baseline.predict_array("rope", model, initial)
        canonical[str(nodes)] = [
            {"time_s": t,
             "fno_relative_l2": fields.relative_l2(p, r),
             "newmark_relative_l2": fields.relative_l2(n, r),
             "fno_max_abs_m": float(np.max(np.abs(p - r)))}
            for t, p, n, r in zip(fields.PROFILE_TIMES, prediction, newmark, reference)
        ]
    return {
        "variant": variant, "seed": seed, "epochs": epochs,
        "split_counts": SPLIT_SIZES, "best_epoch": best_epoch,
        "validation_mean_relative_l2": best_error,
        "test": test, "canonical": canonical,
        "seconds": {"data": data_seconds, "training": train_seconds,
                    "test_batch_inference": inference_seconds},
        "model_parameters": sum(p.numel() for p in model.parameters()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--seeds", type=int, nargs="+", default=[2027, 2028, 2029])
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=VARIANTS)
    args = parser.parse_args()
    if args.epochs < 1 or any(s < 0 for s in args.seeds):
        parser.error("epochs must be positive and seeds nonnegative")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    args.out.mkdir(parents=True, exist_ok=True)
    records = []
    for variant in args.variants:
        for seed in args.seeds:
            result = train_variant(variant, seed, args.epochs)
            records.append(result)
            print(f"{variant} seed={seed}: {result['test']['mean_relative_l2']:.5f}", flush=True)
    report = {
        "protocol": "CP2 FNO controlled ablation v1",
        "comparability": "A0 smooth; B1-B3 mixed train/validation/test. Canonical pluck shared.",
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "torch": str(torch.__version__)},
        "runs": records,
    }
    (args.out / "cp2-fno-ab.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
