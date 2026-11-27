"""Vector-valued cavity FNO with a learned affine bypass; fixed 17²/16-step contract."""

from __future__ import annotations

import numpy as np
import torch
from neuralop.models import FNO

from . import cp2_reference as ref


def model():
    return FNO(
        n_modes=(12, 12),
        in_channels=1,
        out_channels=2,
        hidden_channels=12,
        n_layers=2,
        domain_padding=0.15,
    )


def correction(net, density):
    return net(((density - 1) / ref.DENSITY_SCALE)[:, None])


def predict(net, density, coefficients, scale):
    d = np.asarray(density, dtype="float32")
    if (
        d.ndim != 3
        or d.shape[1:] != (17, 17)
        or not np.isfinite(d).all()
        or d.min() <= 0
    ):
        raise ValueError("expected a batch of finite, positive 17 by 17 density fields")
    base = ref.affine_predict(d, coefficients)
    net.eval()
    with torch.inference_mode():
        result = base + scale * correction(net, torch.from_numpy(d)).numpy()
    result[:, 0, -1], result[:, 1, -1] = 1, 0
    return result


def train(train_x, train_y, val_x, val_y, coefficients, seed, epochs=80):
    torch.manual_seed(seed)
    net = model()
    gen = torch.Generator().manual_seed(seed)
    residual = train_y - ref.affine_predict(train_x, coefficients)
    scale = float(np.sqrt(np.mean(residual[..., 1:-1, 1:-1] ** 2)))
    x = torch.from_numpy(train_x)
    y = torch.from_numpy(residual / scale)
    v = torch.from_numpy(val_x)
    vy = torch.from_numpy((val_y - ref.affine_predict(val_x, coefficients)) / scale)
    optimizer = torch.optim.Adam(net.parameters(), lr=0.003)
    best, epoch_best, best_loss = None, 0, float("inf")
    for epoch in range(1, epochs + 1):
        net.train()
        for ix in torch.randperm(len(x), generator=gen).split(16):
            loss = (correction(net, x[ix]) - y[ix])[..., 1:-1, 1:-1].square().mean()
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            optimizer.step()
        net.eval()
        with torch.inference_mode():
            loss = (correction(net, v) - vy)[..., 1:-1, 1:-1].square().mean().item()
        if loss < best_loss:
            best_loss, epoch_best = loss, epoch
            best = {
                k: t.detach().clone()
                for k, t in net.state_dict().items()
                if torch.is_tensor(t)
            }
    torch.nn.Module.load_state_dict(net, best)
    return net, scale, epoch_best


def save(path, net, coefficients, scale):
    weights = {
        k: t.detach().cpu().numpy()
        for k, t in net.state_dict().items()
        if torch.is_tensor(t)
    }
    np.savez_compressed(
        path, format_version=1, coefficients=coefficients, scale=scale, **weights
    )


def load(path):
    with np.load(path, allow_pickle=False) as f:
        if f["format_version"].item() != 1:
            raise ValueError("unsupported cavity accuracy checkpoint")
        net = model()
        weights = {
            k: torch.from_numpy(f[k])
            for k in f.files
            if k not in {"format_version", "coefficients", "scale"}
        }
        torch.nn.Module.load_state_dict(net, weights)
        return net.eval(), f["coefficients"], float(f["scale"])
