"""Structure-aware Fourier operators for the two CP2 teaching experiments.

Distances are in metres, time in seconds for the rope. For the cavity all signed
velocity outputs are in lid-speed units. Axes are batch, component, y, x.
"""

from __future__ import annotations

import numpy as np
from scipy.fft import dst, idst

from ..models import cp2_parallel_and_distributed as cp2
from . import cp2_fields as fields

PAIRS = ((1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (2, 2))


def rope_fit(count=96, modes=192, step=0.025, seed=3917):
    """Fit independent real sine multipliers by ordinary least squares on paired modes.

    The teacher is the separated exact solution. Outputs at a new time interpolate
    learned kernels. The prediction path contains no wave speed or cosine evolution.
    """
    if count < 1 or modes < 1 or step <= 0 or not np.isclose(round(8 / step) * step, 8):
        raise ValueError("positive sample count, modes and a step dividing 8 required")
    k = np.arange(1, modes + 1)
    times = np.linspace(0, 8, round(8 / step) + 1)
    a = (
        np.random.default_rng(seed).normal(size=(count, modes))
        * fields.ROPE.h
        / k**1.25
    )
    energy = np.sum(a * a, axis=0)
    labels = a[:, None, :] * np.cos(
        np.pi * fields.ROPE.nu / fields.ROPE.length * times[:, None] * k
    )
    kernels = np.einsum("bk,btk->tk", a, labels) / energy
    return times, kernels


def rope_predict(initial, time, times, kernels):
    g = np.asarray(initial, dtype=float)
    t = np.atleast_1d(np.asarray(time, dtype=float))
    if (
        g.ndim != 1
        or len(g) < 3
        or not np.isfinite(g).all()
        or np.any(abs(g[[0, -1]]) > 1e-10)
    ):
        raise ValueError("rope needs a finite field on a uniform grid with fixed ends")
    if (
        t.ndim != 1
        or not np.isfinite(t).all()
        or np.any(t < times[0])
        or np.any(t > times[-1])
    ):
        raise ValueError("time outside learned interval")
    a = dst(g[1:-1], type=1, norm="ortho")
    use = min(a.size, kernels.shape[1])
    i = np.clip(np.searchsorted(times, t, side="right") - 1, 0, len(times) - 2)
    fraction = ((t - times[i]) / (times[i + 1] - times[i]))[:, None]
    interpolant = kernels[i, :use] + fraction * (
        kernels[i + 1, :use] - kernels[i, :use]
    )
    coeff = np.zeros((t.size, a.size))
    coeff[:, :use] = interpolant * a[:use]
    return np.pad(idst(coeff, type=1, norm="ortho"), ((0, 0), (1, 1)))


def pluck(x, time, location):
    """Independent characteristic solution; location is a fraction of the length."""
    if not 0 < location < 1:
        raise ValueError("pluck location must be interior")

    def odd(s):
        r = (s / fields.ROPE.length + 1) % 2 - 1
        return (
            fields.ROPE.h
            * np.sign(r)
            * np.minimum(abs(r) / location, (1 - abs(r)) / (1 - location))
        )

    shift = fields.ROPE.nu * np.asarray(time)[..., None]
    return (odd(x - shift) + odd(x + shift)) / 2


def density_basis(n):
    z = np.pi * np.linspace(0, 1, n)
    return np.stack([np.outer(np.cos(ky * z), np.cos(kx * z)) for kx, ky in PAIRS])


def density_samples(n, amplitudes):
    fluctuation = np.einsum("bk,kyx->byx", amplitudes, density_basis(n)) / np.sqrt(
        len(PAIRS)
    )
    return (1 + fields.DENSITY_SCALE * fluctuation).astype("float32")


def velocity(pop, lid):
    rho = pop.sum(axis=-1)
    if rho.min() <= 0 or not np.isfinite(rho).all():
        raise ValueError("non-positive or non-finite D2Q9 density")
    u = (
        pop[..., 1]
        + pop[..., 5]
        + pop[..., 8]
        - pop[..., 3]
        - pop[..., 6]
        - pop[..., 7]
    ) / rho
    v = (
        pop[..., 2]
        + pop[..., 5]
        + pop[..., 6]
        - pop[..., 4]
        - pop[..., 7]
        - pop[..., 8]
    ) / rho
    return rho, u, v


def cavity_snapshots(density, lid, stops):
    """Batched float64 CP2 reference. A missing upstream cell retains its local value."""
    d = np.asarray(density)
    if (
        d.ndim != 3
        or d.shape[1] != d.shape[2]
        or d.shape[1] < 3
        or d.min() <= 0
        or not np.isfinite(d).all()
        or not np.isfinite(lid)
        or lid <= 0
        or not stops
        or min(stops) < 1
    ):
        raise ValueError(
            "positive square densities, lid speed and positive output steps required"
        )
    n = d.shape[1]
    w = np.array(cp2.CP2_LBM_WEIGHTS)
    c = np.array(cp2.CP2_LBM_VELOCITIES)
    omega = cp2.cp2_lbm_relaxation(n, u0_x=lid)
    pop = d[..., None] * w
    result = {}
    for time in range(1, max(stops) + 1):
        rho, u, v = velocity(pop, lid)
        u[:, -1], v[:, -1] = lid, 0
        dot = u[..., None] * c[:, 0] + v[..., None] * c[:, 1]
        eq = (
            w
            * rho[..., None]
            * (1 - 1.5 * (u * u + v * v)[..., None] + dot * (3 + 4.5 * dot))
        )
        post = pop + omega * (eq - pop)
        for y, x in ((0, slice(None)), (slice(1, -1), 0), (slice(1, -1), -1)):
            post[:, y, x] = pop[:, y, x][..., cp2.CP2_LBM_REVERSE]
        post[:, -1] = eq[:, -1]
        pop = post.copy()
        for k, (cx, cy) in enumerate(cp2.CP2_LBM_VELOCITIES[1:], 1):
            dy, sy = (
                slice(max(cy, 0), n + min(cy, 0)),
                slice(max(-cy, 0), n + min(-cy, 0)),
            )
            dx, sx = (
                slice(max(cx, 0), n + min(cx, 0)),
                slice(max(-cx, 0), n + min(-cx, 0)),
            )
            pop[:, dy, dx, k] = post[:, sy, sx, k]
        if time in stops:
            _, u, v = velocity(pop, lid)
            u[:, -1], v[:, -1] = lid, 0
            result[time] = (np.stack([u, v], axis=1) / lid).astype("float32")
    return result


def fit_affine(amplitudes, target):
    design = np.column_stack([np.ones(len(amplitudes)), amplitudes])
    coeff = np.linalg.lstsq(design, target.reshape(len(design), -1), rcond=None)[0]
    return coeff.reshape((-1, *target.shape[1:])).astype("float32")


def affine_predict(density, coeff):
    """Infer the six amplitudes from the supplied density (test coefficients stay hidden)."""
    n = density.shape[-1]
    basis = density_basis(n).reshape(len(PAIRS), -1)
    z = (
        (density.reshape(-1, n * n).astype(float) - 1)
        * np.sqrt(len(PAIRS))
        / fields.DENSITY_SCALE
    )
    a = np.linalg.lstsq(basis.T, z.T, rcond=None)[0].T
    return (coeff[0] + np.einsum("bk,kcyx->bcyx", a, coeff[1:])).astype("float32")
