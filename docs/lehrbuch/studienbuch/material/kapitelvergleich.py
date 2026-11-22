"""Gegenproben zu den 17 Kapiteln. Im vollständig entpackten Rechenlabor ausführen."""
from __future__ import annotations

import cmath
import csv
import json
import math
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent


def pruefe(bedingung, fehlermeldung):
    if not bedingung:
        raise ValueError(fehlermeldung)


def nahe(wert, soll, toleranz=1e-10):
    pruefe(math.isclose(wert, soll, rel_tol=toleranz, abs_tol=toleranz),
           f"{wert} weicht vom Kontrollwert {soll} ab")


def daten(name):
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def theorie():
    abstand = 0.1 * math.exp(-2)
    nahe(abstand, 0.013533528324)
    yield 1, f"Abstand nach 1 s {abstand:.5f} K, Normschranke {0.1*math.exp(2):.3f} K"

    h = 0.1 * 0.9 / 8 ** (1/3)
    nahe(h, 0.045)
    nahe(8 * (h / 0.1) ** 3, 0.729)
    yield 2, f"Erneuter Versuch mit {h:.3f} s, vorhergesagter Fehler 0.729"

    z = -10
    faktor = (1 + 2*z/5 + z*z/20) / (1 - 3*z/5 + 3*z*z/20 - z**3/60)
    nahe(faktor, 3 / 58)
    yield 3, f"Radau-Faktor {faktor:.8f}, exakter Faktor {math.exp(z):.8f}"

    spannung = (6 + 3000 * .002 * 3) / (1 + 3000 * .002)
    strom = (6 - spannung) / 3000
    nahe(.002 * (spannung - 3) - strom, 0)
    nahe(spannung + 3000 * strom - 6, 0)
    yield 4, f"Rückwärts-Euler {spannung:.6f} V und {1000*strom:.6f} mA"

    # Aufprall ohne Luftwiderstand. Die exakte kleine Zeitverschiebung lässt
    # sich ohne Subtraktion fast gleicher Quadratwurzeln berechnen.
    dh = 1e-7
    g, tempo = 9.81, 2.0
    zeitverschiebung = 2*dh / (math.sqrt(tempo**2 + 2*g*dh) + tempo)
    nahe(zeitverschiebung / dh, 1 / tempo, 1e-6)
    yield 5, f"Ereigniszeitsensitivität {zeitverschiebung/dh:.7f} s/m"

    for indexfolge in ((0, 1), (1, 0)):
        q, x3, vorher = [0., 0.], 0., 0.
        for tick in range(1, 6):
            jetzt = tick / 5
            x3 += (jetzt - vorher) * (q[0] - q[1])
            for i in indexfolge:
                q[i] = jetzt
            vorher = jetzt
            nahe(x3, 0.)
            nahe(q[0] - q[1], 0.)
    yield 6, "Beide Einfügereihenfolgen ergeben an fünf Doppelterminen x3 = 0"

    def flaechenwert(links, mitte, rechts):
        a, b = mitte-links, rechts-mitte
        steigung = math.copysign(min(abs(a), abs(b)), a) if a*b > 0 else 0.0
        return mitte + steigung / 2
    nahe(flaechenwert(0, 1, 3), 1.5)
    nahe(flaechenwert(0, 1, 0), 1)
    yield 7, "Minmod liefert an der rechten Zellfläche 1.5 auf der Rampe und 1 am Gipfel"

    masse = impuls_x = impuls_y = 0.0
    for cx in (-1, 0, 1):
        for cy in (-1, 0, 1):
            w = (4/9, 1/9, 1/36)[abs(cx) + abs(cy)]
            cu = .1 * cx
            f = w * (1 + 3*cu + 4.5*cu**2 - 1.5*.1**2)
            masse += f
            impuls_x += cx*f
            impuls_y += cy*f
    nahe(masse, 1)
    nahe(impuls_x, .1)
    nahe(impuls_y, 0)
    yield 8, "Bewegtes D2Q9-Gleichgewicht: Dichte 1, Impuls (0.1, 0)"

    for n in (8, 16):
        x = [2*math.pi*j/n for j in range(n)]
        v = [math.sin(s) + math.sin(3*s)/4 for s in x]
        # Dieselbe Normierung wie in Kapitel 9. Die Summe ist hier kurz genug für eine direkte DFT.
        koeff = {k: sum(a*cmath.exp(-1j*k*s) for a, s in zip(v, x))/n for k in (-1, 1, 3)}
        nahe(abs(koeff[3] + 1j/8), 0.)
        test = [sum(koeff[k]*cmath.exp(1j*k*s) for k in (-1, 1)).real for s in x]
        relativ = math.sqrt(sum((a-b)**2 for a, b in zip(test, v)) / sum(a*a for a in v))
        nahe(relativ, 1/math.sqrt(17))
    yield 9, f"Relativer Fehler des Tiefpasses auf beiden Gittern {relativ:.8f}"


def benchmark():
    with (HERE / "qss-extension.csv").open(encoding="utf-8", newline="") as datei:
        laeufe = list(csv.DictReader(datei))
    def lauf(fall, methode):
        faktor = "0.001" if methode == "qss2" else ""
        treffer = [r for r in laeufe if (r["case"], r["method"], r["quantum_factor"]) ==
                   (fall, methode, faktor)]
        pruefe(len(treffer) == 1, f"Uneindeutige Konfiguration {fall}/{methode}")
        return treffer[0]

    ids = [(1, 2), (2, 3), (3, 4)]
    def kontaktpruefung(paare, zeiten):
        if paare != ids or len(zeiten) != len(ids):
            return "Ereignisfehler", None
        return "vollständig", max(abs(t-t0)/.001 for t, t0 in zip(zeiten, (1, 2, 3)))
    _, s = kontaktpruefung(ids, [1, 2, 3.0012])
    nahe(s, 1.2)
    pruefe(kontaktpruefung(ids[::-1], [1, 2, 3]) == ("Ereignisfehler", None), "Kontaktkennung")
    yield 10, "Zu später dritter Stoß S = 1.2, vertauschte Kennungen ohne Score"

    radau = max(.0152 / 10, 2.95e-8 / 1e-5)
    bdf = max(1.13 / 10, 2.33e-6 / 1e-5)
    nahe(radau, .00295)
    nahe(bdf, .233)
    pruefe(lauf("C05", "qss2")["status"] == "timeout", "C05-Zeitlimit")
    yield 11, f"Enge C05-Lehrbudgets aus gerundeten Fehlern: Radau {radau:.5f}, BDF {bdf:.3f}"

    qss, rk = lauf("C12", "qss2"), lauf("C12", "rk45")
    pruefe((qss["rhs"], rk["rhs"], qss["accepted"]) == ("36", "148", "0"), "C12-Zähler")
    nahe(float(qss["error_over_limit"]), 0.)
    yield 12, "Drei Kontakte bei null internen QSS2-Updates, 36 beziehungsweise 148 RHS-Aufrufe"

    diode = daten("c21-idas.json")
    pruefe(diode["idas_events"] == 149 and all(c["events"] == 149 for c in diode["comparisons"]), "C21-Ereignisse")
    pruefe(diode["max_residual"] < 2.20e-10, "C21-Defekt")
    nahe(float(lauf("C07", "qss2")["error_over_limit"]), 1.58304, 1e-5)
    yield 13, "149 C21-Übergänge und maximaler C07-Score 1.58304 für die gewählte QSS2-Konfiguration"

    tank = float(lauf("C09", "qss2")["error_over_limit"]) * .5
    nahe(tank, .00584324, 1e-7)
    nahe(53.585 - 41.916, 11.669)
    nahe(float(lauf("C13", "qss2")["error_over_limit"]), 33.6799, 1e-5)
    yield 14, f"C09-Kurzfenster {tank:.6f} mm, C09-Langzeitfenster 11.669 cm, C13-Score 33.68"

    reihe = daten("cp2_genauigkeit/transport_feste_raender.json")
    werte = [abs(zeile["well_mg_m3"] - 45021.62) / 450.2162 for zeile in reihe["rows"]]
    for zeile, s, soll in zip(reihe["rows"], werte, [8.12, 7.88, 1.97], strict=True):
        nahe(s, soll, .005)
        nahe(zeile["mass_rate_mg_s"] * reihe["time_s"], 1728000)
    yield 15, "C19R-Brunnenscores bei festen Rändern " + ", ".join(f"{s:.2f}" for s in werte)

    saite = [r for r in daten("cp2_genauigkeit/saite.json")["plucks"]
             if r["n"] == 501 and r["position"] == .5 and r["time"] in (5, 8)]
    pruefe(sorted(r["time"] for r in saite) == [5, 8], "Zeitfenster CP2")
    alt, modal = [max(r[modell]["relative"]/.01 for r in saite) for modell in ("old", "new")]
    nahe(alt, 3.00088, 1e-5)
    nahe(modal, .04303, 1e-5)
    yield 16, f"Saitenfeld bei einem Prozent Budget: ursprünglicher FNO {alt:.5f}, modal {modal:.5f}"

    anzahl = Counter(r["status"] for r in laeufe)
    erwartet = {"pass": 222, "accuracy_miss": 151, "event_mismatch": 20, "timeout": 46, "solver_error": 17}
    pruefe(anzahl == erwartet and len(laeufe) == 456, "Archivzählung")
    yield 17, f"{anzahl['pass']} bestandene von 456 begonnenen und 373 vollständig bewerteten Einstellungen"


if __name__ == "__main__":
    for nummer, befund in (*theorie(), *benchmark()):
        print(f"Kapitel {nummer:2d}  {befund}")
