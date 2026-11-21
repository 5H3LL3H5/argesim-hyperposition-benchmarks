"""Regenerate the German textbook's vector figures from equations and study data."""

import csv
import hashlib
import json
import sys
from math import exp, factorial, sqrt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker
from matplotlib.colors import LinearSegmentedColormap

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from argesim_benchmarks.models.c05_two_state import (
    C05_INITIAL_STATE,
    C05_MODE_1,
    c05_exact_step,
    simulate_c05,
)

OUT = ROOT / "docs/lehrbuch/abbildungen"
EVIDENCE = ROOT / "docs/evidence"
INK, TEAL, RUST, BLUE, MUTED = "#183649", "#00776f", "#ad482c", "#53578b", "#526674"
FILL, GRID, PAPER = "#cce7dd", "#d9e1df", "#ffffff"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9.5,
        "text.color": INK,
        "axes.labelcolor": INK,
        "axes.edgecolor": MUTED,
        "axes.labelsize": 9.5,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "xtick.labelsize": 8.5,
        "ytick.labelsize": 8.5,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.axisbelow": True,
        "lines.linewidth": 2.1,
        "axes.linewidth": 0.7,
        "legend.frameon": False,
        "legend.fontsize": 8.2,
        "svg.fonttype": "none",
        "svg.hashsalt": "argesim-textbook-2026",
        "axes.unicode_minus": True,
        "path.simplify": True,
        "savefig.facecolor": PAPER,
    }
)


def sheet(widths=(1,), height=2.75):
    fig, ax = plt.subplots(
        1,
        len(widths),
        figsize=(7.25, height),
        squeeze=False,
        gridspec_kw={"width_ratios": widths},
        layout="constrained",
    )
    for a in ax[0]:
        a.grid(axis="y", color=GRID, linewidth=0.65)
        a.tick_params(length=3)
    return fig, ax[0]


def panel(ax, title):
    ax.set_title(title, loc="left", fontsize=10, weight="bold", color=INK, pad=9)


def save(fig, name, description):
    path = OUT / (name + ".svg")
    fig.savefig(
        path,
        format="svg",
        facecolor=fig.get_facecolor(),
        metadata={"Date": None, "Title": description, "Description": description},
    )
    plt.close(fig)
    # SVG path coordinates are whitespace-separated across lines.
    path.write_text(
        "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
    )


def cooling():
    fig, (a, b) = sheet((1.25, 1), 2.8)
    t = np.linspace(0, 2, 241)
    a.plot(t, 20 + 60 * np.exp(-t / 2), color=TEAL, label="exakte Temperatur")
    a.plot(
        [0, 1, 2], [80, 50, 35], "o--", color=RUST, ms=5, label="Euler, Schritt 1 min"
    )
    a.set(
        xlabel="Zeit t [min]",
        ylabel="Temperatur [°C]",
        xlim=(-0.06, 2.08),
        ylim=(29, 85),
    )
    a.legend(loc="upper right")
    panel(a, "A   Vom Messwert zum Modell")
    n = np.array([2, 4, 8, 16, 32, 64])
    h = 1 / n
    for order, color, style in ((1, RUST, "o-"), (2, BLUE, "s--"), (4, TEAL, "^-.")):
        r = sum((-h) ** j / factorial(j) for j in range(order + 1))
        err = np.abs(r**n - exp(-1))
        b.loglog(
            n,
            err,
            style,
            color=color,
            ms=4,
            label={1: "Euler", 2: "Mittelpunkt", 4: "RK4"}[order],
        )
    b.set(xlabel="Anzahl der Schritte bis s = 1", ylabel="absoluter Fehler")
    b.set_xticks(n, labels=[str(v) for v in n])
    b.xaxis.set_minor_locator(ticker.NullLocator())
    b.legend(loc="lower left")
    panel(b, "B   Was Halbieren bewirkt")
    save(fig, "fehler", "Abkühlung und Konvergenz von drei Einschrittverfahren")


def stages():
    fig, (a, b) = sheet((1.2, 1), 2.65)
    t = np.linspace(0, 0.5, 100)
    a.plot(t, np.exp(-t), color=TEAL, label="exakte Lösung")
    pts = [(0, 1), (0.25, 0.75), (0.25, 0.8125), (0.5, 0.59375)]
    for (x, y), tag, ofs in zip(
        pts, ("1", "2", "3", "4"), ((5, 3), (-13, -12), (6, 2), (-11, -14))
    ):
        a.plot(x, y, "o", color=RUST, ms=5)
        a.annotate(
            tag,
            (x, y),
            xytext=ofs,
            textcoords="offset points",
            color=RUST,
            weight="bold",
        )
    a.plot(
        0.5,
        1 - 0.5 * (1 + 2 * 0.75 + 2 * 0.8125 + 0.59375) / 6,
        "D",
        mfc=PAPER,
        mec=INK,
        ms=6,
        label="RK4-Endwert",
    )
    a.set(
        xlabel="dimensionslose Zeit s",
        ylabel="normierte Temperatur u",
        xlim=(-0.025, 0.54),
        ylim=(0.53, 1.05),
    )
    a.set_xticks([0, 0.25, 0.5], ["0", "¼", "½"])
    a.legend(loc="upper right")
    panel(a, "A   Wo wird die Steigung gemessen?")
    k = np.array([-1.0, -0.75, -0.8125, -0.59375])
    weights = np.array([1, 2, 2, 1]) / 6
    a2 = b.barh([3, 2, 1, 0], -k * weights, color=[BLUE, TEAL, TEAL, BLUE], height=0.48)
    for bar, w in zip(a2, ("1/6", "2/6", "2/6", "1/6")):
        b.text(
            bar.get_width() + 0.006,
            bar.get_y() + bar.get_height() / 2,
            w,
            va="center",
            fontsize=8.5,
        )
    b.set_yticks([3, 2, 1, 0], ["Stufe 1", "Stufe 2", "Stufe 3", "Stufe 4"])
    b.set(xlim=(0, 0.34), xlabel="Betrag des Beitrags zur mittleren Steigung")
    panel(b, "B   Wie viel trägt jede Stufe bei?")
    save(
        fig,
        "rk-stufen",
        "RK4-Stufenzustände und gewichtete Steigungen eines einzelnen Schritts",
    )


def oscillator():
    fig, (a, b) = sheet((1, 1.15), 2.85)
    h = 0.25
    steps = np.arange(25)
    z = 1j * h
    euler = (1 + z) ** steps
    t = np.linspace(0, 2 * np.pi, 241)
    a.plot(np.cos(t), -np.sin(t), color=TEAL, label="exakte Bahn")
    a.plot(
        euler.real,
        -euler.imag,
        "o--",
        color=RUST,
        ms=2.8,
        lw=1.3,
        label="Euler, h = 0,25",
    )
    a.set(xlabel="Auslenkung u", ylabel="Geschwindigkeit v", aspect="equal")
    a.legend(loc="upper left", fontsize=7.8)
    panel(a, "A   Amplitude im Phasenraum")
    h = 0.5
    n = np.arange(1, 51)
    z = 1j * h
    for factor, style, color, name in (
        ((1 + z / 2) / (1 - z / 2), "--", BLUE, "impliziter Mittelpunkt"),
        (1 + z + z**2 / 2 + z**3 / 6 + z**4 / 24, "-", TEAL, "RK4"),
    ):
        b.semilogy(n * h, n * (h - np.angle(factor)), style, color=color, label=name)
    b.set(xlabel="Zeit t", ylabel="Phasennachlauf [rad]")
    b.legend(loc="lower right")
    panel(b, "B   Phasenfehler bei h = 0,5")
    save(
        fig,
        "oszillator",
        "Amplitudenwachstum und Phasennachlauf am harmonischen Oszillator",
    )


def stability():
    fig, (a, b) = sheet((1, 1.12), 2.95)
    x = np.linspace(-3.4, 0.65, 280)
    y = np.linspace(-3.25, 3.25, 280)
    xx, yy = np.meshgrid(x, y)
    z = xx + 1j * yy
    for r, c, style, lab in [
        (1 + z, RUST, "--", "Euler"),
        (1 + z + z**2 / 2 + z**3 / 6, BLUE, "-.", "RK23"),
        (1 + z + z**2 / 2 + z**3 / 6 + z**4 / 24, TEAL, "-", "RK4"),
    ]:
        a.contour(
            xx, yy, abs(r), levels=[1], colors=[c], linewidths=[1.8], linestyles=[style]
        )
        a.plot([], [], style, color=c, label=lab)
    a.axhline(0, color=MUTED, lw=0.6)
    a.axvline(0, color=MUTED, lw=0.6)
    a.set_aspect("equal")
    a.set(
        xlabel="Realteil von hλ",
        ylabel="Imaginärteil",
        xlim=(-3.3, 1.0),
        ylim=(-3.15, 3.15),
    )
    a.legend(loc="upper right", bbox_to_anchor=(1.28, 0.97), fontsize=7.4)
    panel(a, "A   Stabilitätsgrenzen in der Ebene")
    q = np.geomspace(0.03, 1e3, 450)
    b.semilogx(q, 1 / (1 + q), color=TEAL, label="rückwärts Euler")
    b.semilogx(q, (1 - q / 2) / (1 + q / 2), "--", color=RUST, label="Trapezregel")
    b.semilogx(q, np.exp(-q), ":", color=INK, label="exakte Dämpfung")
    b.axhline(0, color=MUTED, lw=0.7)
    b.set(
        ylim=(-1.09, 1.09),
        xlabel="Betrag von hλ, negativer reeller Modus",
        ylabel="Verstärkung mit Vorzeichen",
    )
    b.legend(loc="lower left")
    panel(b, "B   Dämpfung sehr schneller Anteile")
    save(
        fig,
        "stabilitaet",
        "Absolute Stabilitätsgebiete und Folgen A- beziehungsweise L-stabiler Dämpfung",
    )


def heat():
    fig, (a, b) = sheet((1.12, 1), 2.85)
    x = np.linspace(0, 1, 201)
    t = np.linspace(0, 0.18, 191)
    vals = np.sin(np.pi * x[None, :]) * np.exp(-(np.pi**2) * t[:, None])
    cmap = LinearSegmentedColormap.from_list(
        "heat", ["#f5f1de", "#b9dacc", "#4b9d94", "#123c52"]
    )
    lev = np.linspace(0, 1, 21)
    im = a.contourf(x, t, vals, levels=lev, cmap=cmap)
    cs = a.contour(x, t, vals, levels=(0.2, 0.5, 0.8), colors="#193b4b", linewidths=0.8)
    a.clabel(cs, cs.levels, fmt="%.1f", fontsize=7, inline=True)
    a.set(xlabel="Ort x [m]", ylabel="Zeit t [s]")
    panel(a, "A   Temperatur eines Stabes")
    cb = fig.colorbar(
        im,
        ax=a,
        orientation="horizontal",
        fraction=0.075,
        pad=0.05,
        aspect=23,
        ticks=(0, 0.5, 1),
    )
    cb.set_label("Temperaturüberschuss u [K]", fontsize=8)
    j = np.arange(9)
    v = np.sin(np.pi * j / 8)
    b.plot(j / 8, v, color=MUTED, lw=1.2)
    b.scatter(j / 8, v, color=MUTED, s=18)
    b.scatter(j[3:6] / 8, v[3:6], color=[RUST, TEAL, RUST], s=48, zorder=3)
    for i, lab, dy in [(3, "j − 1", -16), (4, "j", 8), (5, "j + 1", -16)]:
        b.annotate(
            lab,
            (i / 8, v[i]),
            xytext=(0, dy),
            textcoords="offset points",
            ha="center",
            weight="bold",
        )
    b.set(
        xlabel="Ort x [m]",
        ylabel="u zur Zeit t = 0 [K]",
        ylim=(-0.07, 1.2),
        xticks=(0, 0.25, 0.5, 0.75, 1),
    )
    panel(b, "B   Drei Knoten für eine Krümmung")
    save(fig, "waerme", "Exakte Wärmeleitung und Drei-Punkt-Ortsdiskretisierung")


def circuit():
    from matplotlib.patches import Circle, Rectangle

    fig, (a, b) = sheet((1.18, 1), 2.5)
    a.axis("off")
    a.set_aspect("equal")
    a.set(xlim=(-0.2, 5.2), ylim=(-0.3, 3.05))

    def wire(xs, ys):
        a.plot(xs, ys, color=INK, lw=2, solid_capstyle="round")

    wire([0.6, 0.6, 1.85], [1.8, 2.45, 2.45])
    wire([3.15, 4.1, 4.1], [2.45, 2.45, 1.45])
    wire([4.1, 4.1, 0.6, 0.6], [1.2, 0.3, 0.3, 0.94])
    a.add_patch(Circle((0.6, 1.37), 0.43, fill=False, lw=1.8, edgecolor=INK))
    a.text(0.6, 1.55, "+", ha="center", va="center", weight="bold")
    a.text(0.6, 1.19, "−", ha="center", va="center", weight="bold")
    a.text(0.02, 0.67, "5 V", weight="bold", color=BLUE)
    a.add_patch(Rectangle((1.85, 2.25), 1.30, 0.40, color=FILL, ec=TEAL, lw=1.7))
    a.text(2.5, 2.80, "R = 2 kΩ", ha="center", fontsize=9)
    wire([3.63, 4.57], [1.45, 1.45])
    wire([3.63, 4.57], [1.2, 1.2])
    a.text(3.3, 1.02, "C = 1 mF", ha="right", fontsize=9)
    a.annotate(
        "",
        xy=(1.72, 2.83),
        xytext=(0.85, 2.83),
        arrowprops={"arrowstyle": "->", "color": RUST, "lw": 1.7},
    )
    a.text(1.10, 2.92, "i", color=RUST, weight="bold")
    a.annotate(
        "",
        xy=(4.85, 0.66),
        xytext=(4.85, 2.0),
        arrowprops={"arrowstyle": "->", "color": BLUE, "lw": 1.7},
    )
    a.text(4.97, 1.27, "u", color=BLUE, weight="bold")
    panel(a, "A   Ein Strom, zwei Spannungsabfälle")
    t = np.array([0, 2 * np.log(2), 4])
    u = 5 * (1 - np.exp(-t / 2))
    positions = [2, 1, 0]
    b.barh(positions, u, height=0.45, color=TEAL, label="Kondensator u")
    b.barh(
        positions,
        5 - u,
        left=u,
        height=0.45,
        color=BLUE,
        hatch="//",
        label="Widerstand Ri",
    )
    b.set(
        yticks=positions,
        yticklabels=("Start", "2 ln(2) s", "4 s"),
        xlabel="Teilspannungen [V]",
        xlim=(0, 5.12),
        ylim=(-0.72, 2.55),
    )
    b.legend(loc="upper center", bbox_to_anchor=(0.5, 1.03), ncols=2, fontsize=7.3)
    panel(b, "B   Die Summe bleibt bei 5 V")
    save(
        fig,
        "ladekreis",
        "Schaltung des RC-Ladekreises und Maschenbilanz zu drei Zeiten",
    )


def constraint():
    fig, (a, b) = sheet((1, 1.08), 2.75)
    u = np.linspace(0, 5.15, 110)
    t = np.array([0, 0.5, 1, 2, 4])
    volt = 5 * (1 - np.exp(-t / 2))
    curr = (5 - volt) / 2
    a.plot(u, (5 - u) / 2, color=TEAL)
    a.plot(volt, curr, "o", color=TEAL, ms=5)
    a.plot(0, 1, "x", color=RUST, ms=8, mew=2)
    a.annotate(
        "Vorgabe (0 V, 1 mA)",
        (0, 1),
        xytext=(0.43, 0.74),
        fontsize=8,
        color=RUST,
        arrowprops={"arrowstyle": "-", "color": RUST},
    )
    a.annotate("Start", (0, 2.5), xytext=(0.45, 2.6), fontsize=8)
    a.set(
        xlabel="Spannung u [V]",
        ylabel="Strom i [mA]",
        xlim=(-0.25, 5.25),
        ylim=(-0.1, 2.95),
    )
    panel(a, "A   Zulässige Zustandspaare")
    s = np.linspace(0, 6, 200)
    b.plot(s, 1 - np.exp(-s / 2), color=TEAL, label="u / 5 V")
    b.plot(s, np.exp(-s / 2), "--", color=BLUE, label="i / 2,5 mA")
    b.plot(t, volt / 5, "o", color=TEAL, ms=3)
    b.plot(t, curr / 2.5, "s", color=BLUE, ms=3)
    b.set(xlabel="Zeit t [s]", ylabel="normierter Wert", ylim=(-0.04, 1.08))
    b.legend()
    panel(b, "B   Dieselben Paare im Zeitverlauf")
    save(
        fig,
        "nebenbedingung",
        "RC-Ladekreis mit algebraischer Nebenbedingung und konsistentem Start",
    )


def quantizer():
    fig, (a, b) = sheet((1.1, 1), 2.75)
    edges = np.array([0, 0.2, 0.45, 0.45 + 1 / 3, 1.24])
    q = np.array([1.0, 0.8, 0.6, 0.4, 0.4])
    x = np.array([1, 0.8, 0.6, 0.4, 0.4 - 0.4 * (edges[-1] - edges[-2])])
    t = np.linspace(0, 1.24, 120)
    a.plot(t, np.exp(-t), ":", color=INK, label="exakte Lösung")
    a.plot(edges, x, color=TEAL, label="QSS1-Zustand x")
    a.step(edges, q, where="post", color=BLUE, ls="--", label="Meldung q")
    a.set(
        xlabel="dimensionslose Zeit s", ylabel="normierte Temperatur", ylim=(0.12, 1.08)
    )
    a.legend()
    panel(a, "A   Ein Zustand, zwei Darstellungen")
    b.plot([0, 1 / 8, 11 / 8], [0, 1 / 8, -0.5], color=TEAL)
    b.step(
        [0, 7 / 8, 11 / 8, 1.45],
        [0, -0.25, -0.5, -0.5],
        where="post",
        color=BLUE,
        ls="--",
    )
    b.plot([1 / 8, 0.25], [1 / 8, 0.25], ":", color=RUST)
    b.plot([1 / 8], [1 / 8], "o", ms=5, color=RUST)
    b.annotate(
        "Eingang ändert Steigung",
        (1 / 8, 0.125),
        xytext=(0.42, 0.165),
        fontsize=8,
        color=RUST,
        arrowprops={"arrowstyle": "-", "color": RUST},
    )
    b.plot([3 / 8], [0], "D", ms=4, mfc=PAPER, mec=INK)
    b.set(
        xticks=(0, 1 / 8, 3 / 8, 7 / 8, 11 / 8),
        xticklabels=("0", "⅛", "⅜", "⅞", "11/8"),
        xlabel="Zeit t",
        ylabel="Zustand oder Meldung",
        ylim=(-0.57, 0.32),
    )
    panel(b, "B   Eine Vorhersage wird ungültig")
    save(
        fig,
        "zustandsquantisierung",
        "Zustandsquantisierung beim Abkühlen und nach einem äußeren Eingang",
    )


def contacts():
    fig, (a, b) = sheet((1.25, 1), 2.6)
    t = np.linspace(0, 4, 161)
    for j, (color, style) in enumerate(
        zip((TEAL, BLUE, RUST, INK), ("-", "--", "-.", ":"))
    ):
        # Initial surface gaps 1. Positions in a frame with sphere diameters subtracted.
        pos = j + np.clip(t - j, 0, 1) if j < 3 else j + np.maximum(t - j, 0)
        a.plot(t, pos, style, color=color, label=f"Kugel {j + 1}")
    for j in range(1, 4):
        a.scatter(j, j, s=29, facecolor=PAPER, edgecolor=INK, zorder=4)
    a.set(
        xlabel="Zeit [s]",
        ylabel="Position ohne Durchmesser [m]",
        xticks=range(5),
        yticks=range(5),
    )
    a.legend(loc="upper left", ncols=2, fontsize=7.6)
    panel(a, "A   Bewegung der vier Kugeln")
    for j, (color, style) in enumerate(zip((TEAL, BLUE, RUST), ("-", "--", "-."))):
        p = j + np.clip(t - j, 0, 1)
        next_p = j + 1 + np.clip(t - j - 1, 0, 1)
        b.plot(t, next_p - p, style, color=color, label=f"Spalt {j + 1}")
    b.set(
        xlabel="Zeit [s]",
        ylabel="freier Abstand [m]",
        xticks=range(5),
        ylim=(-0.12, 1.24),
    )
    b.legend(loc="lower right", fontsize=7.5)
    panel(b, "B   Kontakte als erste Nullstellen")
    save(
        fig,
        "kontakte",
        "C12-A2 in der reduzierten Impulsvariante: Positionen und Kontaktbedingungen",
    )


def switches():
    ref = simulate_c05(t_bound=3.5, output_step=0.004)
    times = np.array(ref.times)
    states = np.asarray(ref.states)
    fig, (a, b) = sheet((1.42, 1), 2.7)
    a.plot(times, states[:, 0], color=TEAL, label="Zustand y₁")
    a.plot(times, states[:, 1], "--", color=BLUE, label="Zustand y₂")
    for level in (2.5, 5.8):
        a.axhline(level, lw=0.8, ls=":", color=MUTED)
    for e in ref.events:
        a.scatter(e.time, e.state[0], color=RUST, s=23, zorder=4)
    a.set(xlabel="Zeit [s]", ylabel="Zustandswert", ylim=(0, 6.55))
    a.legend(loc="lower right", fontsize=8)
    panel(a, "A   Drei Schwellenübertritte")
    us = np.linspace(0, 3, 151)
    layer = np.asarray(
        [c05_exact_step(C05_INITIAL_STATE, v * 1e-6, C05_MODE_1) for v in us]
    )
    b.plot(us, layer[:, 0], color=TEAL)
    b.plot(us, layer[:, 1], "--", color=BLUE)
    b.axhline(0.7, ls=":", lw=1, color=RUST)
    b.set(xlabel="Zeit nach Start [µs]", ylabel="Zustandswert", ylim=(0, 4.55))
    panel(b, "B   Die ersten drei Mikrosekunden")
    save(fig, "schaltmodell", "C05: analytische Phasenlösung auf zwei Zeitskalen")


def bouncing():
    fig, (a, b) = sheet((1.1, 1), 2.55)
    g, restitution = 9.81, 0.9
    first = np.sqrt(20 / g)
    next_flight = 2 * restitution * first
    second = first + next_flight
    for t0, t1, height, speed in (
        (0, first, 10, 0),
        (first, second, 0, g * first * restitution),
        (second, 5, 0, g * first * restitution**2),
    ):
        t = np.linspace(t0, t1, 101) - t0
        a.plot(t + t0, height + speed * t - g * t * t / 2, color=TEAL)
    a.scatter([first, second], [0, 0], color=RUST, zorder=3)
    a.set(
        xlabel="Zeit seit Loslassen [s]",
        ylabel="Höhe [m]",
        ylim=(-0.6, 11),
        xlim=(0, 5),
    )
    panel(a, "A   C21 ohne Luftwiderstand")
    t = np.linspace(0, next_flight, 121)

    def arc(t):
        return g * first * restitution * t - g * t * t / 2

    b.plot(t, arc(t), color=TEAL)
    ext = np.linspace(next_flight, 2.82, 31)
    b.plot(ext, arc(ext), ":", color=RUST, label="Fortsetzung ohne Reset")
    b.axhline(0, color=MUTED, lw=0.8)
    for v, lab, delta in (
        (next_flight / 2, "Scheitel", (-18, 10)),
        (next_flight, "Rückkehr", (-42, -17)),
    ):
        b.plot(v, arc(v), "o", color=INK, ms=4)
        b.annotate(
            lab, (v, arc(v)), xytext=delta, textcoords="offset points", fontsize=8
        )
    b.set(
        xlabel="Zeit seit erstem Stoß [s]",
        ylabel="Wächterwert [m]",
        ylim=(-4.15, 10.15),
    )
    b.legend(loc="lower left", fontsize=7.7)
    panel(b, "B   Wiederkehr innerhalb eines Schritts")
    save(
        fig,
        "rueckkehr",
        "Bodenberührung und gerichteter Wiederkontakt nach einem Reset",
    )


def scores():
    csvfile = EVIDENCE / "rk23-devs.csv"
    meta = json.loads((EVIDENCE / "rk23-devs.json").read_text())
    assert hashlib.sha256(csvfile.read_bytes()).hexdigest() == meta["csv_sha256"]
    with csvfile.open() as f:
        rows = {(r["case"], r["method"], r["level"]): r for r in csv.DictReader(f)}
    assert len(rows) == 138
    fig, (a, b) = sheet((1.2, 1), 2.85)
    a.axhspan(1e-8, 1, color=FILL, alpha=0.65)
    a.axhline(1, color=INK, lw=0.9, ls=":")
    for m, c, mark in [
        ("esdirk32", TEAL, "o-"),
        ("Radau", BLUE, "s--"),
        ("BDF", RUST, "^-."),
    ]:
        a.semilogy(
            range(3),
            [float(rows["C05", m, str(k)]["error_over_limit"]) for k in range(3)],
            mark,
            color=c,
            label=m,
            ms=5,
        )
    a.set(
        xticks=(0, 1, 2),
        xticklabels=("10⁻³", "10⁻⁵", "10⁻⁷"),
        ylim=(1e-5, 20),
        xlabel="relative Integratortoleranz",
        ylabel="Fehler / zulässiger Fehler",
    )
    a.legend(loc="upper right", fontsize=7.5)
    panel(a, "A   C05  ·  Grenzwert bei 1")
    names = ["qss2", "rk23", "rk45", "esdirk32"]
    work = [int(rows["C12", m, "0"]["rhs"]) for m in names]
    bars = b.barh(range(4), work, color=[TEAL, BLUE, BLUE, RUST], height=0.48)
    for rect, v in zip(bars, work):
        b.text(
            v + 7, rect.get_y() + 0.24, str(v), va="center", fontsize=9, weight="bold"
        )
    b.set_yticks(range(4), names)
    b.invert_yaxis()
    b.set(xlim=(0, max(work) * 1.18), xlabel="Auswertungen der rechten Seite")
    panel(b, "B   C12  ·  Alle vier erfüllen das Ziel")
    save(
        fig,
        "vergleich",
        "Messwerte aus dem archivierten Vergleich bei gemeinsamem physikalischen Ziel",
    )


def cover():
    fig = plt.figure(figsize=(7.25, 3.25), facecolor="#102e3c")
    a = fig.add_axes([0, 0, 1, 1], facecolor="#102e3c")
    t = np.linspace(0, 2, 501)
    curve = 1 - 0.72 * t + 0.19 * t * t
    for level in np.arange(0.3, 1.01, 0.1):
        a.axhline(level, color="#41606a", lw=0.55)
    a.plot(t, curve, color="#d8f0d9", lw=3)
    # Downward 0.1 crossings of the analytical curve up to its minimum.
    crossings = [0] + [
        (0.72 - sqrt(0.72**2 - 4 * 0.19 * j / 10)) / (2 * 0.19) for j in range(1, 7)
    ]
    a.step(
        crossings + [2],
        [1 - j / 10 for j in range(7)] + [0.4],
        where="post",
        color="#ffb78a",
        lw=2.3,
    )
    a.scatter(
        crossings,
        [1 - j / 10 for j in range(7)],
        s=31,
        facecolor="#102e3c",
        edgecolor="#ffb78a",
        zorder=4,
    )
    a.set(xlim=(-0.04, 2.03), ylim=(0.23, 1.1))
    a.axis("off")
    a.text(
        0.02,
        0.12,
        "kontinuierlicher Zustand",
        color="#d8f0d9",
        transform=a.transAxes,
        fontsize=10,
    )
    a.text(
        0.58,
        0.12,
        "quantisierte Meldung",
        color="#ffb78a",
        transform=a.transAxes,
        fontsize=10,
    )
    save(fig, "titel", "Eine kontinuierliche Kurve und ihre Quantisierungsereignisse")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for draw in (
        cover,
        cooling,
        stages,
        oscillator,
        stability,
        heat,
        circuit,
        constraint,
        quantizer,
        contacts,
        switches,
        scores,
        bouncing,
    ):
        draw()


if __name__ == "__main__":
    main()
