"""Rechnet die CP2-Feldfehler aus gespeicherten Arrays nach. Benötigt nur NumPy."""

from pathlib import Path

import numpy as np

BASIS = Path(__file__).resolve().parent
# Published percentages at the script's three-decimal reporting precision.
SAITE_SOLL = {
    65: ((3.000, 2.504), (0.879, 0.937)),
    501: ((3.001, 0.374), (0.882, 0.152)),
}
KAVITAET_SOLL = 11.589
RUNDUNG = 0.0005  # Prozentpunkte


def pruefe_fehler(ist, soll, bezeichnung):
    if not np.isfinite(ist) or abs(ist - soll) > RUNDUNG:
        raise ValueError(
            f"{bezeichnung}: {ist:.6f} % außerhalb von {soll:.3f} ± {RUNDUNG} Prozentpunkten"
        )


def fehler(prognose, referenz):
    """Relativer räumlicher Fehler in Prozent."""
    if prognose.shape != referenz.shape or not np.isfinite(prognose).all():
        raise ValueError("Das Prognosefeld hat ungültige Werte oder Abmessungen.")
    norm = np.linalg.norm(referenz)
    if not np.isfinite(norm) or norm == 0:
        raise ValueError("Die Referenznorm muss endlich und positiv sein.")
    return 100.0 * np.linalg.norm(prognose - referenz) / norm


def dreieck(x, t):
    """Unabhängige Referenz durch zwei wandernde, an den Rändern gespiegelte Wellen."""

    def versetzt(ort):
        # Erst auf die Periode [-L,L) abbilden, dann den positiven Halbast spiegeln.
        laenge, auslenkung = 0.5, 0.05
        r = (ort + laenge) % (2 * laenge) - laenge
        hoehe = 2 * auslenkung * np.minimum(np.abs(r), laenge - np.abs(r)) / laenge
        return np.sign(r) * hoehe

    return (versetzt(x - 0.06 * t) + versetzt(x + 0.06 * t)) / 2


def main():
    for knoten in (65, 501):
        x = np.linspace(0, 0.5, knoten)
        with np.load(
            BASIS / "rope" / f"rope-{knoten}-fields.npz", allow_pickle=False
        ) as daten:
            for i, t in enumerate((5, 8)):
                soll = dreieck(x, t)
                np.testing.assert_allclose(
                    daten["reference"][i], soll, atol=1e-12, rtol=0
                )
                werte = []
                for name, erwartung in zip(("fno", "newmark"), SAITE_SOLL[knoten][i]):
                    wert = fehler(daten[name][i], soll)
                    pruefe_fehler(wert, erwartung, f"Saite {knoten}, {t} s, {name}")
                    werte.append(wert)
                print(
                    f"Saite {knoten} Knoten, t = {t} s: "
                    f"FNO {werte[0]:.3f} %, Newmark {werte[1]:.3f} %"
                )
    with np.load(BASIS / "cavity" / "cavity-fields.npz", allow_pickle=False) as daten:
        ref, fno = daten["reference"], daten["fno"]
        if ref.shape != (17, 17) or fno.shape != ref.shape:
            raise ValueError("Für die Kavität werden 17 × 17 Werte erwartet.")
        np.testing.assert_array_equal(fno[-1], np.ones(17))
        np.testing.assert_array_equal(ref[-1], np.ones(17))
        if not np.isfinite(fno).all() or fno.min() < 0:
            raise ValueError("Ein Geschwindigkeitsbetrag muss nichtnegativ sein.")
        innen = fehler(fno[1:-1, 1:-1], ref[1:-1, 1:-1])
        pruefe_fehler(innen, KAVITAET_SOLL, "Kavität, Innenraum")
        print(f"Kavität 17 × 17, 16 Schritte: FNO gegen D2Q9 im Inneren {innen:.3f} %")


if __name__ == "__main__":
    main()
