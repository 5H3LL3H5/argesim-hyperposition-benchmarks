"""Diffusion/exchange fields, Dirichlet projection, and structured predictors.

Field layout is (sample, channel, x, y). Training functions only receive arrays.
The analytical propagator is reserved for manufacturing labels and diagnostics.
"""

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.fft import dstn, idstn
from scipy.optimize import least_squares

KNOWN = ((1, 1), (2, 1), (1, 2), (2, 2), (3, 1), (1, 3))
NEW = ((3, 2), (2, 3), (4, 1))


@dataclass(frozen=True)
class Physics:
    du: float = 0.03
    dv: float = 0.06
    rate: float = 1.25
    time: float = 0.4

    def __post_init__(self):
        values = (self.du, self.dv, self.rate, self.time)
        if not np.isfinite(values).all() or min(values) < 0:
            raise ValueError(
                "diffusivities, rate and horizon must be finite and nonnegative"
            )


NOMINAL = Physics()
SHIFTS = {
    "nominal": NOMINAL,
    "diff_swap": Physics(0.06, 0.03),
    "k_low": Physics(rate=0.45),
    "k_high": Physics(rate=2.5),
    "k_zero": Physics(rate=0.0),
    "t_zero": Physics(time=0.0),
    "t_short": Physics(time=0.2),
    "t_long": Physics(time=0.8),
}


@lru_cache(maxsize=32)
def basis(nodes, modes=KNOWN):
    labels = np.array(modes)
    if (
        nodes < 3
        or labels.ndim != 2
        or labels.shape[1] != 2
        or not np.issubdtype(labels.dtype, np.integer)
        or np.min(labels) < 1
        or np.max(labels) >= nodes - 1
        or len(set(modes)) != len(modes)
    ):
        raise ValueError("sine frequencies must be distinct and resolvable on the grid")
    s = np.sin(np.pi * labels[..., None] * np.linspace(0.0, 1.0, nodes))
    s[..., [0, -1]] = 0
    b = (s[:, 0, :, None] * s[:, 1, None, :]).reshape(len(modes), -1)
    b.setflags(write=False)
    return b


def project(fields, modes=KNOWN):
    n = fields.shape[-1]
    b = basis(n, modes)
    f = np.asarray(fields, dtype=np.float64).reshape(-1, 2, n * n)
    return (f @ b.T) * (4.0 / (n - 1) ** 2)


def reconstruct(coeffs, nodes, modes=KNOWN):
    return (coeffs @ basis(nodes, modes)).reshape(-1, 2, nodes, nodes)


def reference_matrix(modes, p):
    k = np.asarray(modes)
    lam = np.pi**2 * (k * k).sum(axis=1)
    a = np.broadcast_to([[0.0, p.rate], [p.rate, 0.0]], (len(k), 2, 2)).copy()
    a[:, 0, 0] = -p.rate - p.du * lam
    a[:, 1, 1] = -p.rate - p.dv * lam
    val, vec = np.linalg.eigh(a)
    return (vec * np.exp(p.time * val)[:, None, :]) @ vec.transpose(0, 2, 1)


def draw(count, seed, modes=KNOWN):
    rng = np.random.default_rng(seed)
    return rng.normal(size=(count, 2, len(modes))) / np.arange(1, len(modes) + 1) ** 1.2


def samples(coeffs, nodes, modes=KNOWN, params=NOMINAL):
    if isinstance(params, Physics):
        future = np.einsum("kij,bjk->bik", reference_matrix(modes, params), coeffs)
    else:
        if len(params) != len(coeffs):
            raise ValueError("one parameter tuple per field pair is required")
        mats = np.stack([reference_matrix(modes, p) for p in params])
        future = np.einsum("bkij,bjk->bik", mats, coeffs)
    return tuple(
        reconstruct(a, nodes, modes).astype(np.float32) for a in (coeffs, future)
    )


def fixed_split(count, seed, nodes):
    return samples(draw(count, seed), nodes)


def family(count, seed):
    rng = np.random.default_rng(seed)
    table = rng.uniform(
        [0.018, 0.04, 0.60, 0.25], [0.045, 0.09, 1.80, 0.55], (count, 4)
    )
    return tuple(Physics(*row) for row in table)


def add_training_noise(y, rho, seed=42204, mode_noise=False):
    """Add centered noise at the prescribed expected interior RMS scale."""
    if rho == 0:
        return y.copy()
    if rho < 0:
        raise ValueError("noise scale must be nonnegative")
    rng = np.random.default_rng(seed)
    values = y.astype(np.float64)
    interior = values[..., 1:-1, 1:-1]
    rms = np.sqrt(np.mean(interior**2, axis=(-2, -1), keepdims=True))
    if mode_noise:
        z = rng.normal(size=(len(y), 2, len(KNOWN)))
        eps = reconstruct(z, y.shape[-1])[..., 1:-1, 1:-1]
        # Expected spatial mean of a sum of six unit-variance sine coefficients squared.
        n = y.shape[-1]
        eps /= np.sqrt(len(KNOWN)) * (n - 1) / (2 * (n - 2))
    else:
        eps = rng.normal(size=interior.shape)
    interior += rho * rms * eps
    return values.astype(np.float32)


class Modal:
    def __init__(self, blocks):
        self.blocks = blocks

    @classmethod
    def fit(cls, x, y):
        a, b = project(x), project(y)
        blocks = []
        for k in range(len(KNOWN)):
            coeff, _, rank, _ = np.linalg.lstsq(a[:, :, k], b[:, :, k], rcond=None)
            if rank != 2:
                raise ValueError(f"training inputs have rank {rank} in mode {KNOWN[k]}")
            blocks.append(coeff.T)
        return cls(np.stack(blocks))

    def predict(self, x, p=NOMINAL):
        coeffs = np.einsum("kij,bjk->bik", self.blocks, project(x))
        return reconstruct(coeffs, x.shape[-1])


@lru_cache(maxsize=256)
def strang_multipliers(n, p):
    freq = np.arange(1, n - 1) ** 2
    lam = np.pi**2 * (freq[:, None] + freq[None, :])
    hu, hv = (np.exp(-0.5 * p.time * d * lam) for d in (p.du, p.dv))
    off = -0.5 * np.expm1(-2 * p.rate * p.time)
    return (1 - off) * hu**2, off * hu * hv, (1 - off) * hv**2


def strang(x, p=NOMINAL):
    """One diffusion/exchange/diffusion Strang step on all resolved sine modes."""
    if not isinstance(p, Physics):
        if len(p) != len(x):
            raise ValueError("one parameter tuple per field pair is required")
        return np.concatenate([strang(field[None], par) for field, par in zip(x, p)])
    return _apply_multipliers(x, strang_multipliers(x.shape[-1], p))


def _apply_multipliers(x, multipliers):
    z = dstn(x[..., 1:-1, 1:-1].astype(np.float64), type=1, norm="ortho", axes=(-2, -1))
    a, b, c = multipliers
    out = np.stack((a * z[:, 0] + b * z[:, 1], b * z[:, 0] + c * z[:, 1]), axis=1)
    out = idstn(out, type=1, norm="ortho", axes=(-2, -1))
    return np.pad(out, ((0, 0), (0, 0), (1, 1), (1, 1)))


def exchange_multipliers(lam, p):
    """Stable closed form for the fitted generator, independent of the label eigensolver."""
    m = p.rate + 0.5 * lam * (p.du + p.dv)
    delta = 0.5 * lam * (p.dv - p.du)
    omega = np.hypot(delta, p.rate)
    eplus = np.exp((-m + omega) * p.time)
    eminus = np.exp((-m - omega) * p.time)
    mean = 0.5 * (eplus + eminus)
    b = np.divide(
        eplus * (-np.expm1(-2 * p.time * omega)),
        2 * omega,
        out=p.time * eplus.copy(),
        where=omega > 0,
    )
    return mean + b * delta, b * p.rate, mean - b * delta


@lru_cache(maxsize=256)
def generator_grid(n, p):
    squares = np.arange(1, n - 1) ** 2
    return exchange_multipliers(np.pi**2 * (squares[:, None] + squares[None, :]), p)


class Generator:
    """Identify physical coefficients from fields at a known time, then accept only T."""

    def __init__(self, coeff):
        self.coeff = tuple(float(v) for v in coeff)

    @classmethod
    def fit(cls, x, y, train_time=NOMINAL.time):
        if train_time <= 0:
            raise ValueError("positive training horizon required for identification")
        a, b = project(x), project(y)
        lam = np.pi**2 * (np.array(KNOWN) ** 2).sum(axis=1)

        def residual(coeff):
            uu, uv, vv = exchange_multipliers(lam, Physics(*coeff, train_time))
            pred = np.stack(
                (uu * a[:, 0] + uv * a[:, 1], uv * a[:, 0] + vv * a[:, 1]), axis=1
            )
            return (pred - b).ravel()

        fit = least_squares(
            residual,
            [0.05, 0.05, 0.75],
            bounds=(0, np.inf),
            xtol=1e-13,
            gtol=1e-13,
            ftol=1e-13,
        )
        if not fit.success or np.linalg.matrix_rank(fit.jac) != 3:
            raise ValueError("the physical parameters could not be identified")
        return cls(fit.x)

    def predict(self, x, p=NOMINAL):
        if not isinstance(p, Physics):
            if len(x) != len(p):
                raise ValueError("one time per field pair required")
            return np.concatenate([self.predict(a[None], q) for a, q in zip(x, p)])
        learned = Physics(*self.coeff, p.time)
        return _apply_multipliers(x, generator_grid(x.shape[-1], learned))


class StrangModal:
    """Learn the six nominal defect blocks; use the full-grid split for every other mode."""

    def __init__(self, residual):
        self.residual = residual

    @classmethod
    def fit(cls, x, y):
        return cls(Modal.fit(x, y - strang(x)))

    def predict(self, x, p=NOMINAL):
        return strang(x, p) + self.residual.predict(x)


def scenario_sets():
    a = draw(32, 42203)
    unseen = draw(32, 62203, NEW)
    mixed = np.concatenate((a, unseen), axis=2) / np.sqrt(2)
    scenarios = {
        name: (*samples(a, 25, params=p), p, KNOWN) for name, p in SHIFTS.items()
    }
    scenarios["nominal13"] = (*samples(a, 13), NOMINAL, KNOWN)
    scenarios["pure_new"] = (*samples(unseen, 25, NEW), NOMINAL, NEW)
    scenarios["mixed_new"] = (*samples(mixed, 25, KNOWN + NEW), NOMINAL, KNOWN + NEW)
    test_params = family(32, 52203)
    scenarios["family_test"] = (*samples(a, 25, params=test_params), test_params, KNOWN)
    return scenarios


def counter_probe(p=NOMINAL, mode=(1, 1), nodes=25):
    c = np.zeros((2, 2, 1))
    c[:, 0, 0] = 1
    c[1, 1, 0] = 1
    return samples(c, nodes, (mode,), p)


def score(pred, truth):
    p = np.asarray(pred, dtype=np.float64)
    y = np.asarray(truth, dtype=np.float64)
    diff = np.linalg.norm((p - y).reshape(len(y), 2, -1), axis=2)
    norm = np.linalg.norm(y.reshape(len(y), 2, -1), axis=2)
    if np.any(norm == 0):
        raise ValueError("relative field error is undefined for a zero target")
    per_field = diff / norm
    return {
        "u": float(per_field[:, 0].mean()),
        "v": float(per_field[:, 1].mean()),
        "boundary": float(
            max(np.abs(p[..., [0, -1], :]).max(), np.abs(p[..., [0, -1]]).max())
        ),
    }


def probe_score(pred, truth):
    y = truth.astype(np.float64)
    delta = y[1, 0] - y[0, 0]
    e = np.asarray(pred[1, 0], dtype=np.float64) - pred[0, 0] - delta
    denom = np.linalg.norm(delta)
    return {
        "response": float(np.linalg.norm(e) / denom) if denom else None,
        "response_abs_l2": float(np.linalg.norm(e)),
    }
