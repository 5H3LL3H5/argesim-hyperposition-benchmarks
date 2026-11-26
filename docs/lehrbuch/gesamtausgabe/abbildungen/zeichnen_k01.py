"""Abbildungen für Kapitel 1. Aufruf: python3 zeichnen.py (Matplotlib)."""
from math import cos, exp, hypot, pi, sin
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle

ORT = Path(__file__).resolve().parent
BLAU, GRUEN, ROST = "#19394D", "#006D67", "#A94322"
GITTER, GRAU = "#D8E1E3", "#687E87"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 10,
    "text.color": BLAU, "axes.labelcolor": BLAU,
    "xtick.color": BLAU, "ytick.color": BLAU,
    "axes.edgecolor": GRAU, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "axes.spines.top": False, "axes.spines.right": False,
    "svg.fonttype": "none", "svg.hashsalt": "Kapitel-1-2026-11-22",
})


def speichern(fig, name, titel, beschreibung):
    fig.savefig(ORT / (name + ".svg"), facecolor="white",
                metadata={"Title": titel, "Description": beschreibung,
                          "Date": "2026-11-22", "Creator": "Christian Stenzel"})
    plt.close(fig)


def tafel(achsen, titel):
    achsen.set_title(titel, loc="left", color=BLAU, fontweight="bold",
                     fontsize=12, pad=10)
    achsen.grid(True, color=GITTER, linewidth=0.65)
    achsen.set_axisbelow(True)
    achsen.tick_params(length=3)


def federwagen():
    fig, (zeit, phase) = plt.subplots(1, 2, figsize=(7.3, 3.48))
    fig.subplots_adjust(left=.084, right=.97, bottom=.27, top=.85, wspace=.35)
    tafel(zeit, "A   Zeitverlauf")
    tafel(phase, "B   Phasenporträt")
    t = [pi * j / 480 for j in range(481)]
    q = [cos(2 * z) for z in t]
    v = [-sin(2 * z) for z in t]
    zeit.plot(t, q, color=GRUEN, lw=2.1, label="Q = q/q₀")
    zeit.plot(t, v, "--", color=ROST, lw=2.1, label="V = v/(ωq₀)")
    zeit.set(xlabel="Zeit t [s]", ylabel="Q und V [1]", xlim=(-.06, 3.24),
             ylim=(-1.18, 1.22), xticks=[0, 1, 2, 3], yticks=[-1, 0, 1])
    zeit.legend(loc="upper left", bbox_to_anchor=(0, -.29), frameon=False,
                ncol=2, columnspacing=.85, fontsize=8.4, handlelength=1.65,
                borderaxespad=0, borderpad=.2)
    phase.set(xlabel="Q = q/q₀ [1]", ylabel="V = v/(ωq₀) [1]",
              xlim=(-1.24, 1.24), ylim=(-1.24, 1.24),
              xticks=[-1, 0, 1], yticks=[-1, 0, 1], aspect="equal")
    for x in [-1.0, -.5, 0.0, .5, 1.0]:
        for y in [-1.0, -.5, 0.0, .5, 1.0]:
            norm = hypot(x, y)
            if norm:
                phase.quiver(x, y, .19*y/norm, -.19*x/norm, angles="xy",
                             scale_units="xy", scale=1, width=.005, color="#94A9AF",
                             pivot="middle", zorder=1)
    phase.plot(q, v, color=GRUEN, lw=2.1, zorder=2)
    phase.annotate("", xy=(cos(.70), -sin(.70)), xytext=(cos(.58), -sin(.58)),
                   arrowprops={"arrowstyle":"-|>", "color":GRUEN, "lw":1.7})
    for ax, xs, ys in [(zeit, [0, pi/4], [1, 0]), (phase, [1, 0], [0, -1])]:
        ax.scatter(xs, ys, s=29, facecolor="white", edgecolor=BLAU, zorder=5)
    zeit.annotate("Start", (0, 1), (10, 3), textcoords="offset points", fontsize=8.5)
    zeit.annotate("Mitte", (pi/4, 0), (3, 7), textcoords="offset points", fontsize=8.5)
    phase.annotate("Start", (1, 0), (-25, 7), textcoords="offset points", fontsize=8.5)
    phase.annotate("Mitte", (0, -1), (5, 6), textcoords="offset points", fontsize=8.5)
    speichern(fig, "phasenraum", "Federwagen in Zeit und Zustandsraum",
              "A: Q und V gegen Sekunden. B: dimensionslose Koordinaten bei gleichem Achsenmaßstab; die Bahn ist ein Einheitskreis.")


def reaktionsmoden():
    fig, (exakt, euler) = plt.subplots(1, 2, figsize=(7.3, 3.56))
    fig.subplots_adjust(left=.096, right=.98, bottom=.29, top=.84, wspace=.32)
    tafel(exakt, "A   Exakte Moden")
    tafel(euler, "B   Schnelle Differenz")
    ms = [12*j/480 for j in range(481)]
    exakt.semilogy(ms, [exp(-x/1000) for x in ms], color=GRUEN, lw=2.1,
                   label="Summe s/c₀")
    exakt.semilogy(ms, [exp(-x) for x in ms], "--", color=ROST, lw=2.1,
                   label="Differenz d/c₀")
    exakt.set(ylabel="Anteil am Startwert [1]", ylim=(1e-6, 1.65),
              yticks=[1, 1e-2, 1e-4, 1e-6],
              yticklabels=["1", "10⁻²", "10⁻⁴", "10⁻⁶"])
    exakt.minorticks_off()
    exakt.legend(loc="lower left", frameon=True, facecolor="white", framealpha=.94,
                 edgecolor="none", fontsize=8.5, handlelength=2.0)
    euler.plot(ms, [exp(-x) for x in ms], color=BLAU, lw=1.8, label="Exakt")
    n = range(5)
    schritte = [3*j for j in n]
    euler.plot(schritte, [(-2)**j for j in n], "--o", color=ROST, ms=5.5,
               lw=1.6, label="Euler explizit")
    euler.plot(schritte, [(.25)**j for j in n], ":s", color=GRUEN, ms=5.4,
               markerfacecolor="white", lw=1.7, label="Euler implizit")
    euler.set(ylabel="d/c₀ [1]", ylim=(-9.7, 18.5), yticks=[-8, 0, 8, 16])
    euler.legend(loc="upper left", fontsize=8.3, handlelength=2.0,
                 frameon=True, facecolor="white", framealpha=.94, edgecolor="none")
    for ax in (exakt, euler):
        ax.set(xlabel="Zeit t [ms]", xlim=(-.23, 12.35), xticks=[0, 3, 6, 9, 12])
    wertepaar = f"Bei 3 ms: exakt {exp(-3):.4f}  ·  implizit {1/(1+3):.2f}"
    euler.text(0, -.365, wertepaar.replace(".", ","),
               transform=euler.transAxes, fontsize=8.5, color=BLAU,
               ha="left", va="top")
    speichern(fig, "steifigkeit", "Zwei Zeitskalen und ein instabiler Euler-Schritt",
              "A: exakte s/c₀ und d/c₀ auf logarithmischer Ordinate. B: d/c₀ auf linearer Ordinate bei drei Millisekunden Schrittweite. Der explizite Euler erreicht -8 bei 9 ms und +16 bei 12 ms.")


def rc_schaltung():
    fig, ax = plt.subplots(figsize=(7.3, 2.50))
    fig.subplots_adjust(left=.015, right=.985, bottom=.02, top=.98)
    ax.set(xlim=(.12, 8.25), ylim=(-.18, 3.0), aspect="equal")
    ax.axis("off")
    def leiter(x1, y1, x2, y2):
        ax.plot([x1, x2], [y1, y2], color=BLAU, lw=2, solid_capstyle="butt")
    def pfeil(start, ende, farbe):
        ax.annotate("", xy=ende, xytext=start, arrowprops={
            "arrowstyle":"-|>", "color":farbe, "lw":1.7, "mutation_scale":12})
    def label(x, y, s, farbe=BLAU, **kw):
        ax.text(x, y, s, color=farbe, ha="center", va="center", fontsize=11, **kw)
    xl, xr, oben, unten = 1.42, 6.70, 2.24, .34
    for punkte in [(xl,oben,3.43,oben),(4.93,oben,xr,oben),
                   (xl,oben,xl,1.73),(xl,.85,xl,unten),(xl,unten,xr,unten),
                   (xr,oben,xr,1.42),(xr,1.16,xr,unten)]:
        leiter(*punkte)
    ax.add_patch(Rectangle((3.43,oben-.17),1.50,.34,fill=False,edgecolor=BLAU,lw=2))
    ax.add_patch(Circle((xl,1.29),.44,fill=False,edgecolor=BLAU,lw=2))
    label(xl,1.47,"+"); label(xl,1.12,"−")
    for y in (1.42,1.16):
        leiter(xr-.53,y,xr+.53,y)
    label(4.18,oben,"R"); label(5.83,1.29,"C")
    label(3.40,2.53,"+"); label(4.98,2.53,"−")
    label(6.11,1.62,"+"); label(6.11,.98,"−")
    pfeil((1.83,2.58),(3.00,2.58),GRUEN); label(2.43,2.83,"i",GRUEN)
    pfeil((3.44,1.82),(4.94,1.82),ROST); label(4.18,1.55,"R i",ROST)
    pfeil((.75,2.02),(.75,.58),ROST); label(.44,1.31,"U",ROST)
    pfeil((7.57,2.02),(7.57,.58),ROST); label(7.90,1.31,"u",ROST)
    ax.scatter([4.18],[unten],s=15,c=BLAU)
    leiter(4.18,unten,4.18,.12)
    for y,width in ((.12,.46),(.025,.30),(-.07,.14)):
        leiter(4.18-width/2,y,4.18+width/2,y)
    label(4.84,.04,"0 V")
    speichern(fig, "rc_schaltung", "Zählpfeile des RC-Ladekreises",
              "Strom i fließt von der oberen Quellklemme über den Widerstand zur oberen Kondensatorplatte. Die Bezugsspannungen weisen vom Plus- zum Minuspol. Der untere Leiter liegt auf 0 Volt.")


if __name__ == "__main__":
    federwagen()
    reaktionsmoden()
    rc_schaltung()
