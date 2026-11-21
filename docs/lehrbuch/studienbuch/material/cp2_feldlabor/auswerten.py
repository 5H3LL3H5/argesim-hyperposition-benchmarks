"""Rechnet die CP2-Feldfehler aus gespeicherten Arrays nach. Benötigt nur NumPy."""
from pathlib import Path

import numpy as np

BASIS = Path(__file__).resolve().parent


def fehler(prognose, referenz):
    """Relativer räumlicher Fehler in Prozent."""
    return 100.0 * np.linalg.norm(prognose - referenz) / np.linalg.norm(referenz)


def dreieck(x, t):
    """Unabhängige Referenz durch zwei wandernde, an den Rändern gespiegelte Wellen."""
    def versetzt(ort):
        # Erst auf die Periode [-L,L) abbilden, dann den positiven Halbast spiegeln.
        laenge, auslenkung = 0.5, 0.05
        r = (ort + laenge) % (2*laenge) - laenge
        hoehe = 2*auslenkung * np.minimum(np.abs(r), laenge-np.abs(r)) / laenge
        return np.sign(r) * hoehe

    return (versetzt(x - 0.06*t) + versetzt(x + 0.06*t)) / 2


def main():
    for knoten in (65, 501):
        x = np.linspace(0, 0.5, knoten)
        with np.load(BASIS / 'rope' / f'rope-{knoten}-fields.npz', allow_pickle=False) as daten:
            for i,t in enumerate((5, 8)):
                soll = dreieck(x, t)
                np.testing.assert_allclose(soll, daten['reference'][i], atol=1e-12)
                print(f'Saite {knoten} Knoten, t = {t} s: '
                      f'FNO {fehler(daten["fno"][i], soll):.3f} %, '
                      f'Newmark {fehler(daten["newmark"][i], soll):.3f} %')
    with np.load(BASIS / 'cavity' / 'cavity-fields.npz', allow_pickle=False) as daten:
        ref, fno = daten['reference'], daten['fno']
        np.testing.assert_array_equal(fno[-1], np.ones(17))
        np.testing.assert_array_equal(ref[-1], np.ones(17))
        if fno.min() < 0:
            raise ValueError('Ein Geschwindigkeitsbetrag muss nichtnegativ sein.')
        print(f'Kavität 17 × 17, 16 Schritte: FNO gegen D2Q9 im Inneren '
              f'{fehler(fno[1:-1, 1:-1], ref[1:-1, 1:-1]):.3f} %')


if __name__ == '__main__':
    main()
