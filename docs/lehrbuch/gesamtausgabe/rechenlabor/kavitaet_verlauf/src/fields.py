"""Macroscopic fields in book units, frozen model inference and shared diagnostics."""

import numpy as np
from design import END, LID, N
from scipy.ndimage import map_coordinates

KINDS = (
    "fourier",
    "laplace",
    "wavelet",
    "hankel",
    "radon",
    "wavelet_laplace",
    "fourier_mellin",
)
GRID = np.indices((N, N), dtype=float) / 4


def lid_value(velocity):
    velocity[..., -1, :, 0] = 1.0
    velocity[..., -1, :, 1] = 0.0
    return velocity


def raw_field(raw, n, re, tick):
    if tick == 0:
        return lid_value(np.zeros((n, n, 2)))
    path = raw / f"n{n}_re{re}" / f"feld_{tick}.bin"
    planes = np.fromfile(path, dtype=np.float64).reshape((3, n, n))
    return lid_value(planes[1:].transpose(1, 2, 0).copy())


def prolong(field):
    return np.stack(
        [
            map_coordinates(
                field[:, :, j], GRID, order=1, mode="nearest", prefilter=False
            )
            for j in range(2)
        ],
        axis=-1,
    )


def batch_signature(ticks, dictionary, re):
    k = np.asarray(ticks, dtype=float)
    edges = np.expm1(np.linspace(0, np.log1p(END), 65))
    hist = np.clip((k[:, None] - edges[:-1]) / np.diff(edges), 0, 1)
    feat = hist @ dictionary
    r = (re - 1000) / 350
    return np.column_stack(
        (
            np.full(k.size, r),
            np.full(k.size, r * r),
            np.log1p(k * LID / (N - 1)),
            feat,
            feat * r,
        )
    )


class Frozen:
    def __init__(self, inputs, group, kind):
        self.group = group
        with np.load(inputs / "basis/zeitkerne.npz") as d:
            self.dictionary = d[kind]
        where = inputs / "daten/operatoren"
        with np.load(where / f"{group}_{kind}.npz") as p:
            self.params = dict(p)
        self.basis = np.load(where / f"basis_{group}.npy", mmap_mode="r")

    def predict(self, ticks, re=1000, coarse=None):
        p = self.params
        s = (batch_signature(ticks, self.dictionary, re) - p["shift"]) / p["scale"]
        design = np.column_stack((np.ones(len(s)), s, np.tanh(s @ p["W"] + p["b"])))
        v = ((design @ p["out"]) @ self.basis).reshape(-1, N, N, 2)
        if self.group == "direkt":
            return lid_value(v)
        if coarse is None or len(coarse) != len(ticks):
            raise ValueError(
                "one matched coarse field is required for every correction"
            )
        for i, field in enumerate(coarse):
            v[i] += prolong(field)
        return v


def diagnostics(guess, truth):
    ref = truth[1:-1, 1:-1]
    err = guess[1:-1, 1:-1] - ref
    sq_err = float(np.vdot(err, err))
    sq_ref = float(np.vdot(ref, ref))
    local = np.sum(err * err, axis=-1)
    row, col = np.unravel_index(np.argmax(local), local.shape)
    return {
        "error_sq": sq_err,
        "ref_sq": sq_ref,
        "rel": (np.sqrt(sq_err / sq_ref) if sq_ref else None),
        "max_U": float(np.sqrt(local[row, col])),
        "x": int(col + 1),
        "y": int(row + 1),
        "energy_ratio_ref": sq_ref / (2 * (N - 2) ** 2),
        "energy_ratio_pred": float(
            np.vdot(guess[1:-1, 1:-1], guess[1:-1, 1:-1]) / (2 * (N - 2) ** 2)
        ),
    }
