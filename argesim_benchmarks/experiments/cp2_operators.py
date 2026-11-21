"""Train or use Fourier neural operators on two ARGESIM CP2 field problems."""

from __future__ import annotations

import argparse
import json
import os
import platform
import tempfile
import time
from importlib.metadata import version
from pathlib import Path

import numpy as np
import torch
from neuralop.models import FNO

from ..models import cp2_parallel_and_distributed as cp2
from . import cp2_fields as fields


def make_model(case):
    if case == "rope":
        return FNO(
            n_modes=(24,),
            in_channels=1,
            out_channels=2,
            hidden_channels=12,
            n_layers=2,
            positional_embedding=None,
        )
    if case == "cavity":
        return FNO(
            n_modes=(10, 10),
            in_channels=1,
            out_channels=1,
            hidden_channels=12,
            n_layers=3,
            domain_padding=0.15,
        )
    raise ValueError("case must be rope or cavity")


def forward_field(case, model, initial):
    """Map a batch of physical input fields directly to both times or the final speed."""
    if case == "rope":
        # Odd 2L-periodic extension supplies fixed-end boundary conditions.
        extended = torch.cat((initial, -initial[..., 1:-1].flip(-1)), dim=-1)
        raw = model(extended[:, None] / fields.ROPE.h)
        reflected = torch.roll(raw.flip(-1), shifts=1, dims=-1)
        projected = (raw - reflected) / 2
        return fields.ROPE.h * projected[..., : initial.shape[-1]]
    # A speed is a magnitude: enforce non-negativity in both training and prediction.
    speed = model(((initial - 1.0) / fields.DENSITY_SCALE)[:, None]).abs()
    # CP2's output convention prescribes |u|/u_lid = 1 on the driving row.
    return torch.cat((speed[..., :-1, :], torch.ones_like(speed[..., -1:, :])), dim=-2)


def scored(case, tensor):
    return tensor[..., 1:-1, 1:-1] if case == "cavity" else tensor


def errors(case, prediction, target):
    p, y = scored(case, prediction), scored(case, target)
    # Equally weight each physical initial field and each requested output time.
    axes = tuple(range(2, y.ndim))
    energy = np.sum(y**2, axis=axes)
    if np.any(energy == 0):
        raise ValueError("relative error is undefined for a zero reference")
    err = np.sqrt(np.sum((p - y) ** 2, axis=axes) / energy)
    return {"mean_relative_l2": float(err.mean()), "max_relative_l2": float(err.max())}


def predict_array(case, model, initial):
    x = np.ascontiguousarray(initial, dtype=np.float32)
    if not np.isfinite(x).all():
        raise ValueError("input must contain only finite values")
    if case == "rope":
        if x.ndim != 1 or x.size < 25 or np.any(np.abs(x[[0, -1]]) > 1e-7):
            raise ValueError(
                "rope input needs at least 25 equally spaced nodes and fixed zero ends"
            )
    elif x.shape != (fields.CAVITY_NODES, fields.CAVITY_NODES) or x.min() <= 0:
        raise ValueError(
            "cavity input must be a positive density field on the training grid"
        )
    model.eval()
    with torch.inference_mode():
        return forward_field(case, model, torch.from_numpy(x)[None])[0].numpy()


def tensor_weights(model):
    # Store only numerical arrays: architecture and boundary policy are fixed by format 1.
    return {
        key: tensor.detach().cpu().clone()
        for key, tensor in model.state_dict().items()
        if torch.is_tensor(tensor)
    }


def save_weights(path, case, weights):
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as temp:
        name = temp.name
    try:
        with open(name, "wb") as stream:
            np.savez_compressed(
                stream,
                format_version=1,
                case=case,
                **{k: t.numpy() for k, t in weights.items()},
            )
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def load_weights(path):
    with np.load(path, allow_pickle=False) as saved:
        if saved["format_version"].item() != 1:
            raise ValueError("unsupported CP2 checkpoint version")
        case = str(saved["case"].item())
        model = make_model(case)
        weights = {
            name: torch.from_numpy(saved[name])
            for name in saved.files
            if name not in ("case", "format_version")
        }
    torch.nn.Module.load_state_dict(model, weights)
    return case, model.eval()


def canonical_case(case, model, destination):
    if case == "rope":
        report = {}
        for nodes in (fields.ROPE_NODES, fields.ROPE.interior_points + 2):
            initial, reference, newmark = fields.canonical_rope(nodes)
            predicted = predict_array(case, model, initial)
            report[str(nodes)] = [
                {
                    "time_s": t,
                    "fno_relative_l2": fields.relative_l2(p, r),
                    "newmark_relative_l2": fields.relative_l2(n, r),
                    "fno_max_abs_m": float(np.abs(p - r).max()),
                    "newmark_max_abs_m": float(np.abs(n - r).max()),
                }
                for t, p, n, r in zip(
                    fields.PROFILE_TIMES, predicted, newmark, reference
                )
            ]
            np.save(destination / f"rope-{nodes}-input.npy", initial)
            np.savez_compressed(
                destination / f"rope-{nodes}-fields.npz",
                reference=reference,
                fno=predicted,
                newmark=newmark,
            )
        return report
    n = fields.CAVITY_NODES
    initial = np.ones((n, n), dtype=np.float32)
    run = cp2.cp2_task2_lid_driven_cavity(
        nx=n,
        iterations=fields.CAVITY_STEPS,
        reynolds=fields.REYNOLDS,
        u0_x=fields.LID_SPEED,
        backend="serial",
    )
    reference = np.array(run.relative_speed)
    prediction = predict_array(case, model, initial)[0]
    np.save(destination / "cavity-input.npy", initial)
    np.savez_compressed(
        destination / "cavity-fields.npz", reference=reference, fno=prediction
    )
    return {
        "nodes_per_axis": n,
        "iterations": fields.CAVITY_STEPS,
        "reynolds": fields.REYNOLDS,
        "lid_speed": fields.LID_SPEED,
        "fluid_relative_l2": fields.relative_l2(
            scored(case, prediction), scored(case, reference)
        ),
        "max_abs_relative_speed": float(np.abs(prediction - reference).max()),
        "lbm_mass_change": run.mass_error,
        "minimum_predicted_relative_speed": float(prediction.min()),
    }


def run_study(case, destination, seed, epochs):
    if seed < 0 or epochs < 1:
        raise ValueError("seed must be non-negative and epochs positive")
    destination.mkdir(parents=True, exist_ok=True)
    sizes = (96, 16, 24)
    streams = np.random.SeedSequence(seed).spawn(len(sizes))
    factory = fields.rope_samples if case == "rope" else fields.cavity_samples
    start = time.perf_counter()
    samples = [factory(n, np.random.default_rng(s)) for n, s in zip(sizes, streams)]
    data_seconds = time.perf_counter() - start
    (x, y), (vx, vy), (tx, ty) = [
        (torch.from_numpy(a), torch.from_numpy(b)) for a, b in samples
    ]
    torch.manual_seed(seed)
    model = make_model(case)
    optimizer = torch.optim.Adam(model.parameters(), lr=0.003)
    generator = torch.Generator().manual_seed(seed)
    scale = fields.ROPE.h if case == "rope" else 1.0
    best_error = float("inf")
    best = None
    best_epoch = 0
    start = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        for indices in torch.randperm(len(x), generator=generator).split(16):
            prediction = forward_field(case, model, x[indices])
            residual = scored(case, (prediction - y[indices]) / scale)
            optimizer.zero_grad(set_to_none=True)
            residual.square().mean().backward()
            optimizer.step()
        model.eval()
        with torch.inference_mode():
            val = forward_field(case, model, vx).numpy()
        error = errors(case, val, vy.numpy())["mean_relative_l2"]
        if error < best_error:
            best_error, best_epoch, best = error, epoch, tensor_weights(model)
    training_seconds = time.perf_counter() - start
    if best is None:
        raise ArithmeticError("validation did not yield a finite checkpoint")
    checkpoint = destination / f"{case}-weights.npz"
    save_weights(checkpoint, case, best)
    _, model = load_weights(checkpoint)
    with torch.inference_mode():
        start = time.perf_counter()
        test_prediction = forward_field(case, model, tx).numpy()
        inference_seconds = time.perf_counter() - start
    average_field = np.broadcast_to(y.numpy().mean(axis=0), ty.shape)
    metrics = {
        "case": case,
        "seed": seed,
        "train_validation_test_counts": sizes,
        "epochs": epochs,
        "best_epoch": best_epoch,
        "validation_mean_relative_l2": best_error,
        "test": errors(case, test_prediction, ty.numpy()),
        "train_mean_baseline_test": errors(case, average_field, ty.numpy()),
        "canonical": canonical_case(case, model, destination),
        "seconds": {
            "data_generation": data_seconds,
            "training": training_seconds,
            "cpu_inference_test_batch": inference_seconds,
        },
        "versions": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "torch": str(torch.__version__),
            "neuraloperator": version("neuraloperator"),
        },
        "cpu_threads": torch.get_num_threads(),
    }
    with (destination / f"{case}-metrics.json").open("w", encoding="utf-8") as out:
        json.dump(metrics, out, indent=2, allow_nan=False)
        out.write("\n")
    return metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    train = commands.add_parser(
        "train", help="train, select on validation, measure on held-out fields"
    )
    train.add_argument("case", choices=("rope", "cavity"))
    train.add_argument("--out", required=True, type=Path)
    train.add_argument("--seed", default=2027, type=int)
    train.add_argument("--epochs", default=80, type=int)
    predict = commands.add_parser(
        "predict", help="load a numerical checkpoint and predict one new field"
    )
    predict.add_argument("weights", type=Path)
    predict.add_argument("input", type=Path, help="physical initial field, .npy")
    predict.add_argument("output", type=Path, help="output profiles, .npy")
    args = parser.parse_args()
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    if args.command == "train":
        print(
            json.dumps(run_study(args.case, args.out, args.seed, args.epochs), indent=2)
        )
    else:
        case, model = load_weights(args.weights)
        field = np.load(args.input, allow_pickle=False)
        prediction = predict_array(case, model, field)
        with args.output.open("wb") as stream:
            np.save(stream, prediction)


if __name__ == "__main__":
    main()
