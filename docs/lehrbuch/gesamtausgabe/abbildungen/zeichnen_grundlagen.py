"""Abbildungen zu den mathematischen Grundlagen, als Vektorgrafiken."""
from math import exp, pi, sin, sqrt
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle
from matplotlib.ticker import FuncFormatter

ROOT = Path(__file__).resolve().parent
BLUE, GREEN, RUST, INK = "#0072B2", "#08735E", "#AA470E", "#1D3240"

plt.rcParams.update({
    "font.size": 10,
    "font.family": "DejaVu Sans",
    "axes.labelcolor": INK,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "svg.fonttype": "none",
    "svg.hashsalt": "argesim-grundlagen",
})

GERMAN = FuncFormatter(lambda value, _pos: f"{value:g}".replace(".", ",").replace("-", "−"))


def save(fig, name):
    fig.savefig(ROOT / f"{name}.svg", metadata={"Date": None})
    plt.close(fig)


def axes(size=(8, 2.48)):
    fig, ax = plt.subplots(figsize=size)
    fig.subplots_adjust(left=.11, right=.97, bottom=.24, top=.91)
    ax.xaxis.set_major_formatter(GERMAN)
    ax.yaxis.set_major_formatter(GERMAN)
    ax.grid(alpha=.21)
    return fig, ax


def norms():
    fig, ax = axes()
    fig.subplots_adjust(left=.18, right=.68, bottom=.22, top=.96)
    ax.add_patch(Rectangle((-1, -1), 2, 2, facecolor="#EFF6F2", edgecolor=GREEN,
                           ls="--", lw=1.5, label=r"$\|x\|_\infty \leq 1$"))
    ax.add_patch(Circle((0, 0), 1, facecolor="#E7F2F8", edgecolor=BLUE, lw=1.5,
                        label=r"$\|x\|_2 \leq 1$"))
    ax.plot(.8, .8, "o", color=RUST, ms=5, label=r"$(0{,}8;\,0{,}8)$")
    ax.axhline(0, color=INK, lw=.5, alpha=.45)
    ax.axvline(0, color=INK, lw=.5, alpha=.45)
    ax.set(xlim=(-1.13, 1.13), ylim=(-1.13, 1.13), aspect="equal",
           xlabel=r"$x_1$ [1]", ylabel=r"$x_2$ [1]")
    ax.set_xticks([-1, 0, 1])
    ax.set_yticks([-1, 0, 1])
    ax.legend(loc="center left", bbox_to_anchor=(1.25, .5), frameon=False)
    save(fig, "g_normen")


def taylor():
    fig, ax = axes()
    xs = [i / 200 for i in range(171)]
    ax.plot(xs, [exp(-x) for x in xs], color=BLUE, lw=1.9, label=r"$e^{-s}$")
    ax.plot(xs, [1-x for x in xs], "--", color=RUST, lw=1.5, label=r"$1-s$")
    ax.plot(xs, [1-x+x*x/2 for x in xs], "-.", color=GREEN, lw=1.5,
            label=r"$1-s+s^2/2$")
    ax.axvline(.5, color=INK, lw=.8, ls=":")
    for value, color in ((exp(-.5), BLUE), (.5, RUST), (.625, GREEN)):
        ax.plot(.5, value, "o", ms=4, color=color, zorder=5)
    ax.set(xlim=(0, .85), ylim=(.1, 1.05), xlabel="Normierte Zeit s [1]",
           ylabel="Überschuss u [1]")
    ax.set_xticks([0, .25, .5, .75])
    ax.legend(loc="lower left", frameon=False)
    save(fig, "g_taylor")


def root_search():
    fig, ax = axes()
    samples = [1 + j / 200 for j in range(205)]
    ax.axhline(0, color=INK, lw=.7)
    ax.plot(samples, [x*x-2 for x in samples], color=BLUE, lw=1.9,
            label=r"$g(s)=s^2-2$")
    tx = [1.24, 2.03]
    ax.plot(tx, [4*x-6 for x in tx], "--", color=RUST, lw=1.5, label="Tangente bei 2")
    ax.plot(sqrt(2), 0, "o", color=BLUE, ms=5, zorder=5)
    ax.plot(1.5, 0, "s", color=RUST, ms=5, zorder=5)
    ax.annotate(r"$\sqrt{2}$", (sqrt(2), 0), (1.27, .64), color=BLUE,
                arrowprops={"arrowstyle": "-", "color": BLUE})
    ax.annotate("1,5", (1.5, 0), (1.56, -.67), color=RUST,
                arrowprops={"arrowstyle": "-", "color": RUST})
    ax.set(xlim=(.98, 2.04), ylim=(-1.14, 2.25), xlabel="s [1]", ylabel="g(s) [1]")
    ax.set_xticks([1, 1.25, 1.5, 1.75, 2])
    ax.legend(loc="upper left", frameon=False)
    save(fig, "g_nullstelle")


def aliasing():
    fig, ax = axes((8, 2.65))
    xs = [i / 500 for i in range(501)]
    ax.plot(xs, [sin(2*pi*x) for x in xs], color=BLUE, lw=1.8, label=r"$k=1$")
    ax.plot(xs, [sin(10*pi*x) for x in xs], "--", color=RUST, lw=1.4, label=r"$k=5$")
    ax.plot([0, .25, .5, .75], [0, 1, 0, -1], "o", color=INK, ms=4.4,
            label="Gitterwerte", clip_on=False, zorder=5)
    ax.set(xlim=(0, 1), ylim=(-1.13, 1.62), xlabel=r"Ort $x/L$ [1]",
           ylabel="Wellenwert [1]")
    ax.set_xticks([0, .25, .5, .75, 1])
    ax.set_yticks([-1, 0, 1])
    ax.legend(loc="upper center", ncols=3, frameon=False)
    save(fig, "g_aliasing")


if __name__ == "__main__":
    norms()
    taylor()
    root_search()
    aliasing()
