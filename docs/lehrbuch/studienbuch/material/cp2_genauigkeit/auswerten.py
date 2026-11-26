"""Die gedruckten Feldvergleiche mit NumPy aus den gespeicherten Feldern nachrechnen."""

from pathlib import Path

import numpy as np

DATA = Path(__file__).resolve().parent

# Sollgrenzen nur für die ausgelieferten Kontrollfälle, keine Garantie
# für andere Dichtefelder, Auflösungen oder Zeiten.
KAVITAET_EINZELFELD_MAX_PROZENT = 0.05
KAVITAET_PROFIL_RMS_MAX = {"u": 0.010, "v": 0.003}


def pruefe_obergrenze(ist, soll, bezeichnung):
    if not np.isfinite(ist) or not 0 <= ist <= soll:
        raise ValueError(f"{bezeichnung}: {ist:.8g}; Sollgrenze {soll:.8g}")


def fehler(x, y):
    return np.linalg.norm(x - y) / np.linalg.norm(y)


def dreieck(x, position):
    """Anfangsauslenkung in Metern für eine bei x=position gezupfte Saite."""
    return 0.05 * np.minimum(x / position, (0.5 - x) / (0.5 - position))


def exakte_saite(x, zeit, position=0.25):
    """d'Alembert-Lösung mit festen Enden und Anfangsgeschwindigkeit null."""

    def ungerade(ort):
        r = (ort + 0.5) % 1.0 - 0.5
        return np.sign(r) * dreieck(np.abs(r), position)

    return (ungerade(x - 0.06 * zeit) + ungerade(x + 0.06 * zeit)) / 2


def pruefe_prozent(ist, soll, stellen, bezeichnung):
    toleranz = 0.5 * 10 ** (-stellen)
    if not np.isfinite(ist) or abs(ist - soll) > toleranz:
        raise ValueError(
            f"{bezeichnung}: {ist:.8f} % außerhalb von {soll:.{stellen}f} ± {toleranz} Prozentpunkten"
        )


def saite(profil, zeit, *, analytisch=False):
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
    if analytisch:
        moden = np.arange(1, k.shape[1] + 1)
        k = np.cos(t[:, None] * (0.06 * np.pi / 0.5) * moden[None, :])
    i = np.clip(np.searchsorted(t, zeit, side="right") - 1, 0, len(t) - 2)
    s = (zeit - t[i]) / (t[i + 1] - t[i])
    a = np.fft.rfft(np.r_[profil, -profil[-2:0:-1]])
    keep = min(len(a) - 2, k.shape[1])
    filt = np.zeros_like(a)
    filt[1 : keep + 1] = a[1 : keep + 1] * ((1 - s) * k[i, :keep] + s * k[i + 1, :keep])
    return np.fft.irfft(filt, n=2 * (len(profil) - 1))[: len(profil)]


def main():
    with np.load(DATA / "saite_beispiel.npz", allow_pickle=False) as d:
        x = np.linspace(0.0, 0.5, 501)
        np.testing.assert_array_equal(d["x"], x)
        g = dreieck(x, 0.25)
        with np.load(DATA / "saite.npz", allow_pickle=False) as modal:
            times, fitted = modal["times"], modal["kernels"]
            modes = np.arange(1, fitted.shape[1] + 1)
            exact = np.cos(times[:, None] * (0.06 * np.pi / 0.5) * modes[None, :])
            np.testing.assert_allclose(fitted, exact, atol=1.5e-13, rtol=0)
        for j, (t, alt_soll, neu_soll) in enumerate(
            ((5, 3.0009, 0.04303), (8, 0.8816, 0.01416))
        ):
            referenz = exakte_saite(x, t)
            np.testing.assert_allclose(d["ref"][j], referenz, atol=1e-12, rtol=0)
            pred = saite(g, t)
            kontrolle = saite(g, t, analytisch=True)
            np.testing.assert_allclose(pred, d["new"][j], atol=5e-14, rtol=0)
            np.testing.assert_allclose(pred, kontrolle, atol=5e-14, rtol=0)
            alt, neu = (100 * fehler(feld, referenz) for feld in (d["old"][j], pred))
            pruefe_prozent(alt, alt_soll, 4, f"Saite {t} s, bisher")
            pruefe_prozent(neu, neu_soll, 5, f"Saite {t} s, neu")
            print(
                f"Saite {t} s: bisher {alt:.5f} %, neu {neu:.5f} %, "
                f"analytische Faktoren {100 * fehler(kontrolle, referenz):.5f} %"
            )
    with np.load(DATA / "kavitaet_beispiel.npz", allow_pickle=False) as d:
        ref = np.linalg.norm(d["ref"], axis=0)[1:-1, 1:-1]
        for name in ("old", "affine", "new"):
            pred = d[name] if name == "old" else np.linalg.norm(d[name], axis=0)
            ist = 100 * fehler(pred[1:-1, 1:-1], ref)
            if name == "new":
                pruefe_obergrenze(
                    ist,
                    KAVITAET_EINZELFELD_MAX_PROZENT,
                    "Kavität Einzelfeldfehler (new, Prozent)",
                )
            print(f"Kavität, erstes zurückgehaltenes Feld, {name}: {ist:.5f} %")
    with np.load(DATA / "kavitaet_profile.npz", allow_pickle=False) as d:
        grid, u, v = d["profile_257"]
        for name, vals in (("u", u), ("v", v)):
            loc, ref = d["ghia_" + name].T
            label = f"Kavität Profilfehler {name}/U (RMS, 257²)"
            if not all(np.isfinite(a).all() for a in (grid, vals, loc, ref)):
                raise ValueError(f"{label}: nichtendliche Profildaten")
            ist = np.sqrt(np.mean((np.interp(loc, grid, vals) - ref) ** 2))
            pruefe_obergrenze(ist, KAVITAET_PROFIL_RMS_MAX[name], label)
            print(f"257², {name}: RMS an sechs Literaturpunkten = {ist:.6f}")


if __name__ == "__main__":
    main()
