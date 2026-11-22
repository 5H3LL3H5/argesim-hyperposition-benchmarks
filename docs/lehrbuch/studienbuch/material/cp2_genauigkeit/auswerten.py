"""Die gedruckten Feldvergleiche mit NumPy aus den gespeicherten Feldern nachrechnen."""

from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent


def fehler(x, y):
    return np.linalg.norm(x - y) / np.linalg.norm(y)


def saite(profil, zeit):
    """Ein neues Profil an einem beliebigen Zeitpunkt zwischen 0 und 8 s auswerten."""
    profil = np.asarray(profil, dtype=float)
    if (
        profil.ndim != 1
        or len(profil) < 3
        or not np.isfinite(profil).all()
        or np.any(abs(profil[[0, -1]]) > 1e-10)
        or not 0 <= zeit <= 8
    ):
        raise ValueError(
            "Enden müssen fest, Profil endlich und Zeit zwischen 0 und 8 s sein"
        )
    with np.load(DATA / "saite.npz", allow_pickle=False) as d:
        t, k = d["times"], d["kernels"]
    i = np.clip(np.searchsorted(t, zeit, side="right") - 1, 0, len(t) - 2)
    s = (zeit - t[i]) / (t[i + 1] - t[i])
    a = np.fft.rfft(np.r_[profil, -profil[-2:0:-1]])
    keep = min(len(a) - 2, k.shape[1])
    filt = np.zeros_like(a)
    filt[1 : keep + 1] = a[1 : keep + 1] * ((1 - s) * k[i, :keep] + s * k[i + 1, :keep])
    return np.fft.irfft(filt, n=2 * (len(profil) - 1))[: len(profil)]


if __name__ == "__main__":
    with np.load(DATA / "saite_beispiel.npz", allow_pickle=False) as d:
        g = 0.1 * np.minimum(d["x"] / 0.5, 1 - d["x"] / 0.5)
        for j, t in enumerate([5, 8]):
            pred = saite(g, t)
            np.testing.assert_allclose(pred, d["new"][j], atol=5e-14, rtol=0)
            print(
                f"Saite {t} s: bisher {100 * fehler(d['old'][j], d['ref'][j]):.5f} %, neu {100 * fehler(pred, d['ref'][j]):.5f} %"
            )
    with np.load(DATA / "kavitaet_beispiel.npz", allow_pickle=False) as d:
        ref = np.linalg.norm(d["ref"], axis=0)[1:-1, 1:-1]
        for name in ["old", "affine", "new"]:
            pred = d[name] if name == "old" else np.linalg.norm(d[name], axis=0)
            print(
                f"Kavität, erstes zurückgehaltenes Feld, {name}: {100 * fehler(pred[1:-1, 1:-1], ref):.5f} %"
            )
    with np.load(DATA / "kavitaet_profile.npz", allow_pickle=False) as d:
        grid, u, v = d["profile_257"]
        for name, vals in [("u", u), ("v", v)]:
            loc, ref = d["ghia_" + name].T
            print(
                f"257², {name}: RMS an sechs Literaturpunkten = {np.sqrt(np.mean((np.interp(loc, grid, vals) - ref) ** 2)):.6f}"
            )
