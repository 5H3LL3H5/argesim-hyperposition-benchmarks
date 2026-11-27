"""CP2 cavity-only extraction of the original NumPy reference at PR 91 (see SOURCES.md)."""
import numpy as np

DENSITY_SCALE = 0.02
PAIRS = ((1, 0), (0, 1), (1, 1), (2, 1), (1, 2), (2, 2))
CP2_LBM_WEIGHTS = (4.0 / 9.0,) + (1.0 / 9.0,) * 4 + (1.0 / 36.0,) * 4
CP2_LBM_VELOCITIES = (
    (0, 0),
    (1, 0),
    (0, 1),
    (-1, 0),
    (0, -1),
    (1, 1),
    (-1, 1),
    (-1, -1),
    (1, -1),
)
# Bounce-back reversed directions
CP2_LBM_REVERSE = (0, 3, 4, 1, 2, 7, 8, 5, 6)


def cp2_lbm_relaxation(nx: int = 257, *, u0_x: float = 0.1, reynolds: float = 1000.0) -> float:
    """Return the BGK relaxation rate from the official Reynolds number."""

    if nx < 3 or u0_x <= 0.0 or reynolds <= 0.0:
        raise ValueError("nx >= 3, u0_x > 0, and reynolds > 0 are required")
    viscosity = (nx - 1) * u0_x / reynolds
    return 1.0 / (3.0 * viscosity + 0.5)


def density_basis(n):
    z = np.pi * np.linspace(0, 1, n)
    return np.stack([np.outer(np.cos(ky * z), np.cos(kx * z)) for kx, ky in PAIRS])


def density_samples(n, amplitudes):
    fluctuation = np.einsum("bk,kyx->byx", amplitudes, density_basis(n)) / np.sqrt(
        len(PAIRS)
    )
    return (1 + DENSITY_SCALE * fluctuation).astype("float32")


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
    w = np.array(CP2_LBM_WEIGHTS)
    c = np.array(CP2_LBM_VELOCITIES)
    omega = cp2_lbm_relaxation(n, u0_x=lid)
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
            post[:, y, x] = pop[:, y, x][..., CP2_LBM_REVERSE]
        post[:, -1] = eq[:, -1]
        pop = post.copy()
        for k, (cx, cy) in enumerate(CP2_LBM_VELOCITIES[1:], 1):
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
        / DENSITY_SCALE
    )
    a = np.linalg.lstsq(basis.T, z.T, rcond=None)[0].T
    return (coeff[0] + np.einsum("bk,kcyx->bcyx", a, coeff[1:])).astype("float32")
