"""Kurze numerische Kontrollen für die Kapitelaufgaben des Studienbuchs.

python kapitelproben.py       # alle zwölf Kapitel
python kapitelproben.py 5     # nur das RC-Beispiel

Benötigt nur die Python-Standardbibliothek. Jede Probe verwendet die Einheiten
der jeweiligen Aufgabe. Die Rückgabewerte erscheinen auch im Lösungsweg.
"""
import argparse
import math


def nahe(wert, erwartet):
    if not math.isclose(wert, erwartet, rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError(f"{wert} weicht vom Kontrollwert {erwartet} ab")


def zustand():
    netto = 1.2 - 0.7
    endinhalt = 8 + 4 * netto
    nahe(endinhalt, 10)
    nahe((11 - 8) / netto, 6)
    fehler = []
    for abweichung in [1, 5]:
        original = 1 - 0.01 * (10 + abweichung)**2
        linear = -0.2 * abweichung
        fehler.append(abs((original - linear) / original))
    nahe(fehler[0], 1 / 21)
    nahe(fehler[1], 0.2)
    # Unabhängige Kontrolle der beiden Startwerte aus der Einleitung.
    for startwert, referenz in [(0, 0.46211715726000974), (0.98, 0.9925956064828929)]:
        k = (1-startwert) / (1+startwert)
        nahe((math.e-k) / (math.e+k), referenz)
    euler = 0
    for _ in range(8):
        euler += (1-euler*euler)/16
    nahe(euler, 0.46796596371415616)
    return f"Tank nach 4 s: {endinhalt:g} L; relative Fehler der Steigungen: {fehler[0]:.2%}, {fehler[1]:.2%}"


def feder():
    q, v = 0.25, -0.5
    beschleunigung = (-v - 8*q) / 2
    schritt = 0.20
    q_neu, v_neu = q + schritt*v, v + schritt*beschleunigung
    nahe(q_neu, 0.15)
    nahe(v_neu, -0.65)
    # Im dritten Beispiel stammen u und die höchste Ableitung aus zwei Gesetzen.
    q, q_zweipunkt = 1, -1
    u = 3 - q
    q_dreipunkt = u - 2*q_zweipunkt
    nahe(q_dreipunkt, 4)
    return f"Euler-Zustand: {q_neu:g} m und {v_neu:g} m/s; dritte Ableitung: {q_dreipunkt:g}"


def heizer():
    leistung, kapazitaet, widerstand = 15, 300, 2
    anstieg = leistung / kapazitaet
    ueberschuss = leistung * widerstand
    zeitkonstante = widerstand * kapazitaet
    nahe(anstieg, 0.05)
    nahe(ueberschuss, 30)
    nahe(zeitkonstante, 600)
    signal, ableitung = 3, -5
    x2 = -ableitung - signal
    x1 = signal - x2
    nahe(x1, 1)
    nahe(x2, 2)
    return f"Anstieg: {anstieg:g} K/s; Endüberschuss: {ueberschuss} K; Zeitkonstante: {zeitkonstante} s"


def zeitintegration():
    h, z = 0.25, 1
    k1 = -4*z
    euler = z + h*k1
    k2 = -4*euler
    heun = z + h*(k1+k2)/2
    nahe(euler, 0)
    nahe(heun, 0.5)
    nahe(1-4*0.4, -0.6)
    nahe(1-4*0.6, -1.4)
    for grob, fein in [(0.04, 0.01), (0.01, 0.0025)]:
        nahe(math.log2(grob/fein), 2)
    return f"Euler: {euler:g}; Heun: {heun:g}; exakt: {math.exp(-4*h):.6f}"


def schaltung():
    quelle, widerstand, kapazitaet = 8, 2000, 0.001
    u0, h = 2, 0.5
    faktor = h / (widerstand*kapazitaet)
    u1 = (u0 + faktor*quelle) / (1 + faktor)
    i1 = (quelle - u1) / widerstand
    nahe(kapazitaet * (u1-u0) / h, i1)  # Speichergesetz unabhängig prüfen
    nahe(u1, 3.2)
    nahe(1000*i1, 2.4)
    nahe(quelle - 3 - widerstand*0.001, 3)
    for t in [0, 0.5, 1]:
        x = 2 / (1+2*t)
        x_punkt = -4 / (1+2*t)**2
        nahe(x_punkt + x*x, 0)
    return f"Rückwärts Euler: {u1:g} V, {1000*i1:g} mA; beide Gleichungen erfüllt"


def waerme():
    def innen(links, mitte, rechts, r):
        return mitte + r*(links - 2*mitte + rechts)

    temperatur = innen(10, 16, 14, 0.2)
    zu_grosser_schritt = innen(0, 10, 0, 4*0.2)
    nahe(temperatur, 14.4)
    nahe(zu_grosser_schritt, -6)
    fluss = 1 * (20-14)
    anstieg_links, anstieg_rechts = -fluss/2, fluss/1
    nahe(2*anstieg_links + anstieg_rechts, 0)
    endtemperatur = (2*20+14)/3
    nahe(endtemperatur, 18)
    # Eine Hutfunktion aus zwei linearen Stücken auf dem Einheitsstab.
    breite = 0.5
    masse = 2 * breite / 3
    steifigkeit = 2 * breite * (1/breite)**2
    nahe(-steifigkeit/masse, -12)
    nahe(-2/breite**2, -8)
    return f"Innenpunkt: {temperatur:g} °C; nach unpassender Verfeinerung: {zu_grosser_schritt:g} °C; zwei Körper: {endtemperatur:g} °C"


def schalten():
    an_zeit = (21-20)/1
    aus_zeit = (21-19)/0.5
    nahe(an_zeit, 1)
    nahe(an_zeit + aus_zeit, 5)
    quantum, wechsel = 0.3, 0.1
    zustand_am_wechsel = 2*wechsel
    alt = quantum / 2
    neu = wechsel + (quantum-zustand_am_wechsel) / 0.5
    nahe(alt, 0.15)
    nahe(neu, 0.30)
    return f"Thermostat: {an_zeit:g} und {an_zeit+aus_zeit:g} min; Meldetermin mit Ratenwechsel: {neu:g} s"


def schnelle_mode():
    rate = 400000
    zeit_1e_us = 1e6 / rate
    zeit_prozent_us = -math.log(0.01) * zeit_1e_us
    nahe(zeit_1e_us, 2.5)
    nahe(math.exp(-rate*zeit_prozent_us*1e-6), 0.01)
    nahe(1 - rate*5e-6, -1)
    nahe(1 - rate*2.5e-6, 0)
    fehler = {"A": [0.3,0.7,0.9], "B": [0.2,1.4,0.4]}
    bei_einer_us = [name for name,zeiten in fehler.items() if max(zeiten)<=1]
    if bei_einer_us != ["A"]:
        raise ValueError("Ereignisgrenze falsch ausgewertet")
    return f"Zeit bis 1/e: {zeit_1e_us:g} µs; bis auf 1 %: {zeit_prozent_us:.2f} µs"


def kugelstoss():
    spalte = [0.4, 1.1-0.4]
    t1, t2 = spalte[0]/1, sum(spalte)/1
    nahe(t1, 0.4)
    nahe(t2, 1.1)
    summe, differenz = 1, 0.5
    links = (summe-differenz)/2
    rechts = (summe+differenz)/2
    verlust = 0.5 - (links**2+rechts**2)/2
    nahe(links, 0.25)
    nahe(rechts, 0.75)
    nahe(verlust, 0.1875)
    return f"Kontakte: {t1:g}, {t2:g} s; Energieverlust im teilweise elastischen Stoß: {verlust:g} J"


def pendel_und_diode():
    tempo = 0.3*3
    omega = tempo / 1
    nahe(omega, 0.9)
    nahe(-0.3*(-0.1), 0.03)
    daten = []
    for quelle in (1, 0.6):
        if quelle <= 0.7:
            z = quelle
        else:
            z = (quelle + 2*0.7)/3
        strom = max(0, (z-0.7)/100)
        nahe((quelle-z)/200, strom)
        daten.append(z)
    nahe(daten[0], 0.8)
    nahe(daten[1], 0.6)
    return f"Nach Ablösung: {omega:g} rad/s; Diodenspannungen: {daten[0]:g} V und {daten[1]:g} V"


def transport():
    wasser = 0.5**2 * 10 * 0.25
    quelle, dauer = 2, 5
    zuwachs = quelle * dauer / wasser
    nahe(wasser, 0.625)
    nahe(zuwachs, 16)
    nahe(zuwachs * wasser, 10)
    reisezeit = 5 / 0.864
    return f"Wasservolumen: {wasser:g} m³; Quellbeitrag: {zuwachs:g} mg/m³; Reisezeit: {reisezeit:.2f} Tage"


def verfahrenswahl():
    zeiten = {"A": (0.3,0.018,90), "B": (0.6,0.002,40), "C": (0.4,0.010,110)}
    auswahl = []
    for zeitgrenze in (0.5,0.75):
        brauchbar = [name for name,(zeit,endwert,laufzeit) in zeiten.items()
                     if zeit<=zeitgrenze and endwert<=0.02]
        auswahl.append(min(brauchbar, key=lambda name: zeiten[name][2]))
    if auswahl != ["A","B"]:
        raise ValueError("Falsche Wahl für das neue Zeitbudget")
    reihen = [(1,2,math.inf,3),(2,2,4,6)]
    bestzeiten = [min(paar) for paar in zip(*reihen)]
    anteile = [sum(t <= 1.5*best for t,best in zip(reihe,bestzeiten))/len(reihe) for reihe in reihen]
    nahe(anteile[0], 0.75)
    nahe(anteile[1], 0.5)
    return f"Wahl: {' / '.join(auswahl)}; Fallanteile bei Faktor 1,5: {anteile[0]:.0%} und {anteile[1]:.0%}"


def feldoperatoren():
    def heizrate(t, zustand):
        theta, = zustand
        return ((10.0 - theta / 4.0) / 120.0,)
    nahe(heizrate(0, (0,))[0], 1 / 12)
    nahe(heizrate(60, (40,))[0], 0)
    nahe(4 / 9 + 4 / 9 + 4 / 36, 1)
    # Ungerade Fortsetzung einer an beiden Enden befestigten Dreiecksform.
    def fortsetzung(x):
        r = (x / 0.5 + 1) % 2 - 1
        return math.copysign(0.1 * min(abs(r), 1 - abs(r)), r)
    nahe(fortsetzung(0.375), 0.025)
    nahe(fortsetzung(-0.375), -0.025)
    return "Heizrate, D2Q9-Ruhegewichte und ungerade Saitenfortsetzung stimmen."


PROBEN = (zustand, feder, heizer, zeitintegration, schaltung, waerme, schalten,
          schnelle_mode, kugelstoss, pendel_und_diode, transport, verfahrenswahl, feldoperatoren)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kapitel", type=int, nargs="?", choices=range(1,len(PROBEN)+1))
    args = parser.parse_args()
    for nummer, probe in enumerate(PROBEN,1):
        if args.kapitel is None or args.kapitel == nummer:
            print(f"{nummer:2d}  {probe()}")


if __name__ == "__main__":
    main()
