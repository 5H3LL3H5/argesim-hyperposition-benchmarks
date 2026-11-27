"""Reproduce the CoDA-NO/FNO exchange pilot on a single CPU thread."""

from __future__ import annotations

import argparse
from contextlib import redirect_stdout
import json
import sys
import time
from importlib.metadata import version

import numpy as np
import torch
from neuralop.models import CODANO, FNO

RATE = 1.25
DIFFUSION = np.array([0.03, 0.06])
HORIZON = 0.4
TRAIN_GRID = 13
MODES = ((1, 1), (2, 1), (1, 2), (2, 2), (3, 1), (1, 3))


def sample(coefficients, nodes):
    """Exact zero-Dirichlet two-field diffusion/exchange solution at HORIZON."""
    k = np.array(MODES)
    basis_1d = np.sin(np.pi * k[..., None] * np.linspace(0, 1, nodes))
    basis_1d[..., [0, -1]] = 0
    basis = (basis_1d[:, 0, :, None] * basis_1d[:, 1, None, :]).reshape(len(k), -1)
    eigenvalue = np.pi**2 * (k**2).sum(1)
    matrix = np.broadcast_to([[0.0, RATE], [RATE, 0.0]], (len(k), 2, 2)).copy()
    matrix[:, 0, 0] = -RATE - DIFFUSION[0] * eigenvalue
    matrix[:, 1, 1] = -RATE - DIFFUSION[1] * eigenvalue
    lam, vec = np.linalg.eigh(matrix)
    propagator = (vec * np.exp(HORIZON * lam)[:, None, :]) @ vec.transpose(0, 2, 1)
    future = np.einsum("kij,bjk->bik", propagator, coefficients)
    return tuple(
        torch.from_numpy((c @ basis).reshape(-1, 2, nodes, nodes).astype("float32"))
        for c in (coefficients, future)
    )


def arrays(count, rng, nodes):
    return sample(rng.normal(size=(count, 2, 6)) / np.arange(1, 7) ** 1.2, nodes)


def make(name):
    if name == "FNO":
        return FNO(
            n_modes=(8, 8),
            in_channels=2,
            out_channels=2,
            hidden_channels=8,
            n_layers=2,
            positional_embedding=None,
        )
    return CODANO(
        output_variable_codimension=1,
        lifting_channels=4,
        hidden_variable_codimension=4,
        projection_channels=4,
        n_layers=2,
        n_modes=[[8, 8], [8, 8]],
        n_heads=[1, 1],
        per_layer_scaling_factors=[[1, 1], [1, 1]],
        attention_scaling_factors=[1, 1],
        domain_padding=0,
        use_positional_encoding=True,
        variable_ids=["u", "v"],
        positional_encoding_dim=2,
        positional_encoding_modes=[4, 4],
    )


def predict(model, x):
    extended = x
    for axis in (-1, -2):
        extended = torch.cat(
            (extended, -extended.narrow(axis, 1, x.shape[axis] - 2).flip(axis)),
            dim=axis,
        )
    if isinstance(model, CODANO):
        y = model(extended, input_variable_ids=["u", "v"])
    else:
        y = model(extended)
    for axis in (-1, -2):
        y = (y - torch.roll(y.flip(axis), shifts=1, dims=axis)) / 2
    return y[..., : x.shape[-2], : x.shape[-1]]


def evaluate(p, y):
    e = p - y
    rel = e.flatten(2).norm(dim=-1) / y.flatten(2).norm(dim=-1)
    return {
        "mean_relative_l2_by_field": rel.mean(0).tolist(),
        "max_absolute_by_field": e.abs().amax((0, 2, 3)).tolist(),
    }


def trial(name, seed, epochs, train, val, tests, transfer):
    torch.manual_seed(seed)
    model = make(name)
    rng = torch.Generator().manual_seed(seed)
    opt = torch.optim.Adam(model.parameters(), lr=0.003)
    x, y = train
    best = float("inf")
    start = time.perf_counter()
    for epoch in range(1, epochs + 1):
        model.train()
        for ix in torch.randperm(len(x), generator=rng).split(16):
            opt.zero_grad(set_to_none=True)
            (predict(model, x[ix]) - y[ix]).square().mean().backward()
            opt.step()
        model.eval()
        with torch.inference_mode():
            score = (predict(model, val[0]) - val[1]).square().mean().item()
        if score < best:
            best, selected = score, epoch
            weights = {
                k: v.detach().clone()
                for k, v in model.state_dict().items()
                if torch.is_tensor(v)
            }
    torch.nn.Module.load_state_dict(model, weights)
    seconds = time.perf_counter() - start
    with torch.inference_mode():
        rows = {n: evaluate(predict(model, x), y) for n, (x, y) in tests.items()}
        x, y = transfer
        p = predict(model, x)
        truth = (y[1, 0] - y[0, 0]).norm()
        transfer_error = ((p[1, 0] - p[0, 0]) - (y[1, 0] - y[0, 0])).norm() / truth
        boundary = max(
            float(
                max(
                    predict(model, x)[..., [0, -1]].abs().max(),
                    predict(model, x)[..., [0, -1], :].abs().max(),
                )
            )
            for x, _ in tests.values()
        )
    return dict(
        model=name,
        seed=seed,
        selected_epoch=selected,
        seconds=seconds,
        real_parameter_count=sum(
            p.numel() * (2 if p.is_complex() else 1) for p in model.parameters()
        ),
        test=rows,
        counterfactual_relative_l2_u=float(transfer_error),
        boundary_max_abs=boundary,
    )


def run(epochs, seeds):
    torch.set_num_threads(1)
    torch.backends.nnpack.set_flags(False)
    torch.use_deterministic_algorithms(True)
    train = arrays(96, np.random.default_rng(42201), TRAIN_GRID)
    val = arrays(24, np.random.default_rng(42202), TRAIN_GRID)
    tests = {n: arrays(32, np.random.default_rng(42203), n) for n in (13, 25)}
    held = np.zeros((2, 2, 6))
    held[:, 0, 0] = 1
    held[1, 1, 0] = 1
    transfer = sample(held, 25)
    return dict(
        neuraloperator=version("neuraloperator"),
        torch=str(torch.__version__),
        problem=dict(rate=RATE, diffusivity=DIFFUSION.tolist(), horizon=HORIZON),
        epochs=epochs,
        threads=1,
        counts=[96, 24, 32],
        rows=[
            trial(name, seed, epochs, train, val, tests, transfer)
            for seed in seeds
            for name in ("FNO", "CoDA-NO")
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--seeds", type=int, nargs="+", default=[2027, 73, 3917])
    args = parser.parse_args()
    if args.epochs < 1:
        parser.error("epochs must be positive")
    # neuraloperator 2.0.0 prints its token dimensions to stdout.
    with redirect_stdout(sys.stderr):
        result = run(args.epochs, args.seeds)
    print(json.dumps(result, indent=2, allow_nan=False))
