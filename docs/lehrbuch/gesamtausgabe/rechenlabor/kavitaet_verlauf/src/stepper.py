"""Frozen design for a freely recurrent, reduced neural time-step operator.

Fit only on the two neighbour trajectories. The evaluation code supplies an initial
rest state, parameter and step schedule. No target measurements are used in rollout.
"""

import argparse
from pathlib import Path

import numpy as np
from design import END, N
from fields import lid_value, raw_field

WIDTH = 64
RIDGE = 0.01
ANCHORS = (950, 1050)
STRIDES = (1, 2, 4)


def support_grid(ticks):
    # Reserve the three hidden book times as well as every other dense output.
    return np.array(sorted({0, END, *ticks[::2]} - {4096, 65536, 262144}), dtype=int)


def clock(k):
    return np.log1p(np.asarray(k) / 16.0)


def features(z, t, h, shift, scale, w, b):
    # All nonlinear state features are bounded, including outside training range.
    x = np.column_stack((z, t, np.log1p(np.asarray(h) * 100)))
    x = (x - shift) / scale
    return np.column_stack((np.ones(len(x)), np.tanh(x), np.tanh(x @ w + b)))


def coefficients(field, basis):
    v = field.copy()
    v[-1] = 0
    return v.reshape(-1) @ basis.T


def fit(inputs, raw, output):
    ticks = np.loadtxt(inputs / "ticks257.txt", dtype=int)
    support = support_grid(ticks)
    tau = clock(support)
    basis = np.load(inputs / "daten/operatoren/basis_direkt.npy", mmap_mode="r")
    nmode = basis.shape[0]
    rng = np.random.default_rng(16027)
    w = rng.normal(0, 1 / np.sqrt(nmode + 2), (nmode + 2, WIDTH))
    b = rng.normal(0, 0.35, WIDTH)
    zset, tset, hset, targets = [], [], [], []
    for re in ANCHORS:
        z = np.stack(
            [coefficients(raw_field(raw, N, re, int(k)), basis) for k in support]
        )
        states, times, steps, slopes = [], [], [], []
        for d in STRIDES:
            h = tau[d:] - tau[:-d]
            states.append(z[:-d])
            times.append(tau[:-d])
            steps.append(h)
            slopes.append((z[d:] - z[:-d]) / h[:, None])
        zset.append(np.vstack(states))
        tset.append(np.concatenate(times))
        hset.append(np.concatenate(steps))
        targets.append(np.vstack(slopes))
    samples = np.column_stack(
        (np.vstack(zset), np.concatenate(tset), np.log1p(100 * np.concatenate(hset)))
    )
    shift, scale = samples.mean(axis=0), samples.std(axis=0)
    scale[scale < 1e-10] = 1
    heads = []
    for z, t, h, y in zip(zset, tset, hset, targets, strict=True):
        f = features(z, t, h, shift, scale, w, b)
        u, s, vt = np.linalg.svd(f, full_matrices=False)
        heads.append((vt.T * (s / (s * s + RIDGE))) @ (u.T @ y))
    np.savez_compressed(
        output,
        w=w,
        b=b,
        heads=heads,
        shift=shift,
        scale=scale,
        support=support,
        anchors=ANCHORS,
        ridge=RIDGE,
        strides=STRIDES,
        samples_per_re=len(zset[0]),
    )


class Stepper:
    def __init__(self, inputs, model):
        with np.load(model) as f:
            self.p = dict(f)
        self.basis = np.load(
            inputs / "daten/operatoren/basis_direkt.npy", mmap_mode="r"
        )

    def advance(self, z, k, next_k, head):
        t = clock(k)
        h = clock(next_k) - t
        if h <= 0:
            raise ValueError("ticks must be strictly increasing")
        p = self.p
        a = features(z[None, :], [t], [h], p["shift"], p["scale"], p["w"], p["b"])
        return z + h * (a[0] @ head)

    def head(self, re):
        left, right = self.p["anchors"]
        w = (re - left) / (right - left)
        return (1 - w) * self.p["heads"][0] + w * self.p["heads"][1]

    def rollout(self, ticks, re=1000):
        ticks = np.asarray(ticks)
        if not len(ticks) or ticks[0] != 0 or np.any(np.diff(ticks) <= 0):
            raise ValueError("expected tick zero followed by strictly increasing times")
        z = np.zeros((len(ticks), self.basis.shape[0]))
        head = self.head(re)
        for i in range(1, len(ticks)):
            z[i] = self.advance(z[i - 1], ticks[i - 1], ticks[i], head)
        return z

    def fields(self, z):
        return lid_value((z @ self.basis).reshape(-1, N, N, 2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "raw", "model"):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    fit(a.inputs, a.raw, a.model)
