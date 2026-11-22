"""Parameter-conditioned Fourier correction for short CP2 cavity simulations."""

from __future__ import annotations

import itertools

import numpy as np
import torch
from neuralop.models import FNO
from scipy.interpolate import RegularGridInterpolator

from . import cp2_accuracy as a
from . import cp2_fields as f


def resize(fields, n):
    m = fields.shape[-1]
    if n == m:
        return fields
    z = np.linspace(0, 1, n)
    grid = np.stack(np.meshgrid(z, z, indexing="ij"), axis=-1)
    flat = fields.reshape(-1, m, m)
    interp = RegularGridInterpolator(
        (np.linspace(0, 1, m),) * 2, flat.transpose(1, 2, 0)
    )
    return (
        interp(grid)
        .transpose(2, 0, 1)
        .reshape(*fields.shape[:-2], n, n)
        .astype("float32")
    )


NODES = (17, 25, 33)
LIDS = (0.075, 0.1, 0.125)
STEPS = (8, 16, 24)


def features(density, n, lid, step):
    d = torch.from_numpy(density)
    channels = [(d - 1) / f.DENSITY_SCALE]
    for val in [(n - 25) / 8, (lid - 0.1) / 0.025, (step - 16) / 8]:
        channels.append(torch.full_like(d, float(val)))
    return torch.stack(channels, dim=1)


def make_net():
    return FNO(
        n_modes=(10, 10),
        in_channels=4,
        out_channels=2,
        hidden_channels=10,
        n_layers=2,
        domain_padding=0.15,
    )


def bracket(grid, x):
    if not grid[0] <= x <= grid[-1]:
        raise ValueError("outside calibrated parameter range")
    i = min(np.searchsorted(grid, x, side="right") - 1, len(grid) - 2)
    w = (x - grid[i]) / (grid[i + 1] - grid[i])
    return [(v, s) for v, s in [(i, 1 - w), (i + 1, w)] if s > 0]


def predict(net, bank, density, lid, step):
    density = np.asarray(density, dtype="float32")
    if density.ndim != 3:
        raise ValueError("a batch of square density fields is required")
    n = density.shape[-1]
    if (
        density.shape[-2] != n
        or not np.isfinite(density).all()
        or density.min() <= 0
        or not isinstance(step, (int, np.integer))
    ):
        raise ValueError("finite positive square density and integer step required")
    affine = 0
    scale = 0
    for (i, p), (j, q), (k, r) in itertools.product(
        bracket(NODES, n), bracket(LIDS, lid), bracket(STEPS, step)
    ):
        key = f"{i}_{j}_{k}"
        affine = affine + p * q * r * resize(bank["coeff_" + key], n)
        scale += p * q * r * float(bank["scale_" + key])
    base = a.affine_predict(density, affine)
    net.eval()
    with torch.inference_mode():
        pred = base + scale * net(features(density, n, lid, step)).numpy()
    pred[:, 0, -1], pred[:, 1, -1] = 1, 0
    return pred, base


def load(path):
    with np.load(path, allow_pickle=False) as archive:
        if archive["format_version"].item() != 1:
            raise ValueError("unsupported parameter-conditioned checkpoint")
        bank = {
            k: archive[k] for k in archive.files if k.startswith(("coeff_", "scale_"))
        }
        weights = {
            k: torch.from_numpy(archive[k])
            for k in archive.files
            if k not in bank and k != "format_version"
        }
    net = make_net()
    torch.nn.Module.load_state_dict(net, weights)
    return net.eval(), bank
