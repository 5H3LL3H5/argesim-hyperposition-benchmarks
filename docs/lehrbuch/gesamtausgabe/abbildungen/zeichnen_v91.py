"""Vektorgrafiken der didaktischen Revision."""
from math import cos, pi, sin
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Polygon

ROOT = Path(__file__).resolve().parent
INK = "#1d3240"
BLUE = "#0072b2"
TEAL = "#08735e"
RUST = "#aa470e"
GRAY = "#50636c"
LIGHT = "#eaf2f4"

plt.rcParams.update({
    "font.size": 10.5,
    "font.family": "DejaVu Sans",
    "axes.labelcolor": INK,
    "text.color": INK,
    "svg.fonttype": "none",
    "svg.hashsalt": "lehrbuch-v91",
})


def save(fig, name):
    fig.savefig(ROOT / f"{name}.svg", metadata={"Date": None})
    plt.close(fig)


def arrow(ax, start, end, color=INK, **kwargs):
    ax.annotate("", xy=end, xytext=start, zorder=3,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=1.55, **kwargs))


def box(ax, center, width, height, label, *, edge=GRAY, fill="white"):
    x, y = center
    ax.add_patch(FancyBboxPatch(
        (x - width/2, y - height/2), width, height,
        boxstyle="round,pad=0.023", facecolor=fill, edgecolor=edge, lw=1.1,
    ))
    ax.text(x, y, label, ha="center", va="center", linespacing=1.35)


def rk():
    fig, ax = plt.subplots(figsize=(8, 2.65))
    fig.subplots_adjust(left=.018, right=.982, top=.99, bottom=.01)
    ax.set(xlim=(0, 8), ylim=(0, 2.65))
    ax.axis("off")
    box(ax, (4, 2.32), 3.2, .37, "Stufen berechnen und Fehler E schätzen", fill=LIGHT)
    arrow(ax, (4, 2.11), (4, 1.98))
    ax.add_patch(Polygon([(4, 1.99), (4.97, 1.70), (4, 1.41), (3.03, 1.70)],
                         closed=True, facecolor="white", edgecolor=GRAY, linewidth=1.1))
    ax.text(4, 1.70, r"$E\leq 1$?", ha="center", va="center")
    ax.plot([3.03, 2.0], [1.70, 1.70], color=TEAL, lw=1.55)
    ax.plot([4.97, 6.0], [1.70, 1.70], color=RUST, lw=1.55)
    arrow(ax, (2.0, 1.70), (2.0, 1.12), TEAL)
    arrow(ax, (6.0, 1.70), (6.0, 1.12), RUST)
    ax.text(2.50, 1.78, "Ja", color=TEAL, ha="center")
    ax.text(5.50, 1.78, "Nein", color=RUST, ha="center")
    box(ax, (2, .65), 3.47, .88,
        "Schritt annehmen\nZeit und Zustand fortschreiben\nNeues h nach dem Regler wählen",
        fill="#edf6f1", edge=TEAL)
    box(ax, (6, .65), 3.47, .88,
        "Schritt verwerfen\nZeit, Zustand und PI-Gedächtnis behalten\nMit kleinerem h erneut versuchen",
        fill="#fbf2ed", edge=RUST)
    save(fig, "k2_pruefpfad")


def modes():
    fig, ax = plt.subplots(figsize=(8, 2.65))
    fig.subplots_adjust(left=.08, right=.96, top=.93, bottom=.13)
    ax.set(xlim=(-3.9, 1.35), ylim=(-1.52, 1.52))
    ax.axis("off")
    angle = pi / 8
    origin = (0, 0)
    bound = [(-3.65 * cos(angle), -3.65 * sin(angle)),
             (-3.65 * cos(angle), +3.65 * sin(angle))]
    ax.add_patch(Polygon([origin, *bound], closed=True, color=LIGHT))
    for end in bound:
        ax.plot([0, end[0]], [0, end[1]], color=GRAY, linestyle="--", linewidth=1)
    arrow(ax, (-3.75, 0), (1.23, 0), GRAY)
    arrow(ax, (0, -1.47), (0, 1.48), GRAY)
    ax.plot([-2.8], [0], "o", color=TEAL, ms=7, zorder=4)
    ax.plot([0, 0], [-1.01, 1.01], "D", color=BLUE, ms=6, zorder=4)
    ax.text(-2.8, .12, r"$-ha$", color=TEAL, ha="center")
    ax.text(-2.73, -.31, "schnelles Abklingen", color=TEAL, ha="center")
    ax.text(.12, 1.01, r"$+\mathrm{i}h\omega$", color=BLUE, va="center")
    ax.text(.12, -1.01, r"$-\mathrm{i}h\omega$", color=BLUE, va="center")
    ax.text(1.15, .12, r"$\mathrm{Re}\,z$", ha="right")
    ax.text(-.11, 1.51, r"$\mathrm{Im}\,z$", ha="right", va="top")
    ax.text(-2.68, -1.35, "Sektor schematisch", color=GRAY, va="center", fontsize=9)
    save(fig, "k3_moden")


def sliding():
    fig, ax = plt.subplots(figsize=(8, 2.85))
    fig.subplots_adjust(left=.15, right=.87, bottom=.20, top=.96)
    ax.set(xlim=(-2.9, 2.9), ylim=(-.15, 2.62),
           xlabel="Normalenrichtung x [m]", ylabel="Tangentialrichtung y [m]")
    ax.set_xticks([-2, -1, 0, 1, 2])
    ax.set_yticks([0, 1, 2])
    ax.axvspan(-2.9, 0, color="#edf6f1")
    ax.axvspan(0, 2.9, color="#fbf2ed")
    ax.axvline(0, color=GRAY, lw=1.2)
    ax.spines[["top", "right"]].set_visible(False)

    left, right, middle = (-2.12, .37), (1.55, .37), (0, .46)
    scale = .46
    for point, vector, color in ((left, (2, 1), TEAL), (right, (-1, 4), RUST)):
        x, y = point
        vx, vy = vector
        ax.plot([x, x + scale * vx], [y, y], color=color, ls="--", lw=1.2)
        arrow(ax, point, (x + scale * vx, y + scale * vy), color)
    arrow(ax, middle, (0, middle[1] + scale * 3), BLUE)
    ax.text(-2.76, 1.09, r"$f_-=(2,1)\,\mathrm{m/s}$", color=TEAL, ha="left")
    ax.text(1.17, 2.43, r"$f_+=(-1,4)\,\mathrm{m/s}$", color=RUST, ha="left")
    ax.text(.09, 1.46, r"$f_\mathrm{gl}=(0,3)\,\mathrm{m/s}$", color=BLUE)
    ax.text(-.06, 2.49, "Schaltfläche", color=GRAY, ha="right")
    save(fig, "k5_gleiten")


def cfl():
    fig, axes = plt.subplots(1, 2, figsize=(8, 2.7))
    fig.subplots_adjust(left=.105, right=.976, top=.85, bottom=.222, wspace=.25)
    cases = ((.75, "A  Fußpunkt im Stencil", BLUE),
             (1.25, "B  Fußpunkt außerhalb", RUST))
    for ax, (sigma, title, color) in zip(axes, cases, strict=True):
        ax.set(title=title, xlim=(-1.48, .23), ylim=(-.05, 1.15),
               xlabel=r"$(x-x_i)/\Delta x$ [1]")
        ax.set_xticks([-1, 0], ["−1", "0"])
        ax.set_yticks([0, 1])
        ax.spines[["top", "right"]].set_visible(False)
        ax.add_patch(Polygon([(-1, 0), (0, 0), (0, 1)], facecolor=LIGHT,
                             edgecolor=GRAY, linestyle="--", linewidth=1))
        ax.plot([-1, 0], [0, 0], color=GRAY, linewidth=2.1, zorder=2)
        ax.plot([-1, 0], [0, 0], "o", color=GRAY, markersize=4, zorder=3)
        arrow(ax, (-sigma, 0), (0, 1), color)
        ax.plot(-sigma, 0, "o", color=color, markersize=6, zorder=4)
        ax.text(-.80, .73, f"σ = {sigma:.2f}".replace(".", ","), color=color, ha="center")
        ax.plot(0, 1, "o", color=INK, markersize=4, zorder=4)
    axes[0].set_ylabel(r"$(t-t_n)/h$ [1]")
    save(fig, "k7_cfl")


if __name__ == "__main__":
    rk()
    modes()
    sliding()
    cfl()
