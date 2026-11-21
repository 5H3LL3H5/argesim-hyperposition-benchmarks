"""Rechenpraktikum zu Numerische Simulation dynamischer Systeme, Studienausgabe 2026.

Ausführen mit Python 3.12, NumPy 2.3.5 und SciPy 1.17.0.
Die Referenzen für die Lehrversuche sind analytisch. Alle Auswertungen laufen lokal.
"""
import math

import numpy as np
import scipy
from scipy.integrate import solve_ivp


def waermespeicher():
    kapazitaet, leistung, r1, r2, h = 120.0, 10.0, 1.0, 3.0, 60.0
    tau = kapazitaet * (r1 + r2)
    f = lambda x: (leistung - x / (r1 + r2)) / kapazitaet
    k1 = f(0.0)
    k2 = f(h * k1 / 2)
    k3 = f(h * k2 / 2)
    k4 = f(h * k3)
    theta_rk4 = h * (k1 + 2 * k2 + 2 * k3 + k4) / 6
    theta_exakt = leistung * (r1 + r2) * (-math.expm1(-h / tau))
    # Unbekannte in der Reihenfolge Temperaturüberschuss, Kontaktüberschuss, Wärmestrom.
    matrix = np.array([[kapazitaet / h, 0, 1], [1, -1, -r1], [0, 1, -r2]])
    rhs = [leistung, 0, 0]
    zustand = np.linalg.solve(matrix, rhs)
    assert np.linalg.norm(matrix @ zustand - rhs, ord=np.inf) < 1e-12
    assert abs(zustand[0] - h * leistung / (kapazitaet + h / (r1 + r2))) < 1e-13
    return (k1, k2, k3, k4), (h * k1, theta_rk4, theta_exakt), zustand


def stab_und_regler():
    # Zellunbekannte U1, U2, Kontaktüberschuss und Randstrom.
    rhs = np.array([5.0, 5.0, 0.0, 0.0])
    matrix = [[9, -8, 0, 0], [-8, 9, 0, 1],
              [0, 1, -1, -1.0625], [0, 0, 1, -3]]
    dae = np.linalg.solve(matrix, rhs)
    reduziert = np.linalg.solve([[9, -8], [-8, 9+1/4.0625]], [5.0, 5.0])
    np.testing.assert_allclose(dae[:2], reduziert, rtol=1e-14, atol=1e-14)
    assert abs(sum(dae[:2]) - (10 - dae[3])) < 1e-12
    stationaer = np.linalg.solve([[4, -4], [-4, 4.25]], [5, 5])
    np.testing.assert_allclose(stationaer, [41.25, 40.0])
    sample = [(zeit, 3*math.exp(-.05*zeit)-2) for zeit in [5, 20, 25]]
    return dae, stationaer, sample


def molexperiment(n):
    # N Intervalle, homogener Dirichlet-Rand, dimensionsloser Zeitpunkt 0.1.
    tau = 0.1
    h_x = 1 / n
    schritte = math.ceil(tau / (0.4 * h_x**2))
    h_t = tau / schritte
    r = h_t / h_x**2
    x = np.arange(1, n) / n
    start = np.sin(np.pi * x)
    lam = -4 * n**2 * np.sin(np.pi / (2 * n))**2
    semidiskret = start * np.exp(lam * tau)
    exakt = start * np.exp(-np.pi**2 * tau)
    u = np.r_[0.0, start, 0.0]
    for _ in range(schritte):
        u[1:-1] += r * (u[:-2] - 2 * u[1:-1] + u[2:])
    euler = u[1:-1]
    assert np.max(np.abs(euler - (1 + h_t * lam)**schritte * start)) < 2e-12
    fehler = tuple(float(np.max(np.abs(a - b))) for a, b in
                   [(semidiskret, exakt), (euler, semidiskret), (euler, exakt)])
    return schritte, fehler


def oszillator(h=0.2, ende=100.0):
    ergebnis = []
    n = round(ende / h)
    assert math.isclose(n * h, ende)
    for name in ["Euler", "RK4", "Verlet"]:
        q, v = 1.0, 0.0
        phasen = [0.0]
        energien = [1.0]
        for _ in range(n):
            if name == "Euler":
                q, v = q + h * v, v - h * q
            elif name == "RK4":
                # RK4 auf q' = v, v' = -q. Die Matrix ist R_4(h A).
                c, s = 1 - h*h/2 + h**4/24, h - h**3/6
                q, v = c*q + s*v, -s*q + c*v
            else:
                v -= h*q/2
                q += h*v
                v -= h*q/2
            phasen.append(math.atan2(-v, q))
            energien.append(q*q + v*v)
        emax = np.max(np.abs(np.array(energien) - 1))
        phasenfehler = np.unwrap(phasen)[-1] - ende
        ergebnis.append((name, emax, phasenfehler))
    return ergebnis


def tracking():
    # Der analytische Anfangstransient ist in den Stützstellen aufgelöst.
    rate = 1000.0
    zeiten = np.unique(np.r_[0.0, np.geomspace(1e-7, 0.03, 501), np.linspace(0, 2, 2001)])
    exakt = np.cos(zeiten) - np.exp(-rate * zeiten)
    def rhs(t, y):
        return -rate * (y - np.cos(t)) - np.sin(t)
    ergebnis = []
    for name in ["RK45", "Radau", "BDF"]:
        for rtol in (1e-3, 1e-6):
            optionen = {} if name == "RK45" else {"jac": np.array([[-rate]])}
            loesung = solve_ivp(rhs, (0, 2), [0.0], method=name, rtol=rtol,
                                atol=rtol/100, dense_output=True, **optionen)
            assert loesung.success and loesung.t[-1] == 2
            fehler = np.max(np.abs(loesung.sol(zeiten)[0] - exakt))
            ergebnis.append((name, rtol, len(loesung.t)-1, loesung.nfev, loesung.nlu, fehler))
    return ergebnis


def c05_phase(y, zeit, c2, c4):
    a, b = 2.7e6, 3.5651205
    d = y[1] - c4
    slow = a*d / (a-b)
    return np.array([c4 + c2 + slow*np.exp(-b*zeit)
                     + (y[0]-c4-c2-slow)*np.exp(-a*zeit),
                     c4 + d*np.exp(-b*zeit)])


def c05_schaltungen():
    from scipy.optimize import brentq
    zeit, y = 0.0, np.array([4.2, 0.3])
    phasen = []
    for c2, c4, schwelle in [(0.4, 5.5, 5.8), (-0.3, 2.73, 2.5), (0.4, 5.5, 5.8)]:
        dt = brentq(lambda s, y=y, c2=c2, c4=c4, schwelle=schwelle: c05_phase(y, s, c2, c4)[0]-schwelle, 0.0, 2.0,
                    xtol=2e-14)
        phasen.append((zeit, y.copy(), c2, c4, dt))
        y = c05_phase(y, dt, c2, c4)
        zeit += dt
    phasen.append((zeit, y.copy(), -0.3, 2.73, 3.5-zeit))
    return phasen


if __name__ == "__main__":
    print("NumPy", np.__version__, "SciPy", scipy.__version__)
    print("Wärmespeicher: RK-Stufen, Euler/RK4/exakt, DAE", waermespeicher())
    print("Zwei Zellen (DAE), stationäre FE-Knoten und Tankregler", stab_und_regler())
    for n in (8, 16, 32, 64):
        print("MOL", n, molexperiment(n))
    for row in oszillator():
        print("Oszillator", *row)
    for row in tracking():
        print("Tracking", *row)
    print("C05: Schaltzeiten", [s[0] for s in c05_schaltungen()[1:]])
    print("C12: Kontakte", [i * 1.0 / 1.0 for i in (1, 2, 3)])
    t1 = math.sqrt(2*10/9.81)
    print("C21: zwei Stöße", t1, t1*(1+2*0.9))

