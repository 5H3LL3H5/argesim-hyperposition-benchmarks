"""Die Rechenbilder zu D2Q9 und zur Fourier-Schicht aus den Beispielwerten setzen."""
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = Path(__file__).resolve().parents[1] / "docs/lehrbuch/studienbuch/abbildungen"
INK, SEA, AMBER = "#17374a", "#006f68", "#a84724"


def save(fig, filename):
    fig.savefig(OUT / filename, bbox_inches="tight", pad_inches=0.07,
                metadata={"CreationDate": None, "ModDate": None, "Creator": "Matplotlib"})
    plt.close(fig)


def transport():
    fig, axes = plt.subplots(1, 2, figsize=(7.1, 2.5), layout="constrained")
    for ax in axes:
        ax.set_aspect("equal")
        ax.axis("off")
    source, stream = axes
    source.set_title("Neun Kanäle am Quellort", color=INK, loc="left")
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx or dy:
                source.annotate("", xy=(dx, dy), xytext=(0, 0),
                                arrowprops={"arrowstyle": "-|>", "lw": 1.8,
                                            "color": AMBER if (dx, dy) == (1, 0) else SEA})
    source.scatter([0], [0], s=36, color=INK, zorder=4)
    source.text(1.10, 0, "Ost", va="center", color=AMBER)
    source.set(xlim=(-1.2, 1.9), ylim=(-1.2, 1.2))
    stream.set_title("Ein Zeitschritt im Ostkanal", color=INK, loc="left")
    for y, label in ((1, "vorher"), (0, "nachher")):
        stream.text(-0.12, y, label, ha="right", va="center", color=INK)
        for x in range(3):
            marked = (x, y) in ((0, 1), (1, 0))
            stream.add_patch(plt.Rectangle((x + .02, y - .34), .96, .68,
                                           facecolor="#fbe8d8" if marked else "#f1f5f5",
                                           edgecolor="#9aaeb3"))
            if marked:
                stream.text(x + .5, y, "1,33/9", ha="center", va="center", color=AMBER)
    stream.annotate("", xy=(1.30, .35), xytext=(.71, .65),
                    arrowprops={"arrowstyle": "-|>", "lw": 1.6, "color": AMBER})
    stream.set(xlim=(-1.05, 3), ylim=(-.5, 1.55))
    save(fig, "d2q9_transport.pdf")


def fourier():
    fig, (spectrum, field) = plt.subplots(1, 2, figsize=(7.25, 2.32), layout="constrained")
    for n, marker, color, size in ((8, "o", SEA, 7), (16, "D", AMBER, 4)):
        x = 2 * np.pi * np.arange(n) / n
        v = np.sin(x) + .25 * np.sin(3 * x)
        amplitudes = np.abs(np.fft.rfft(v, norm="forward"))
        spectrum.plot((1, 3), amplitudes[[1, 3]], ls="none", marker=marker, ms=size,
                      color=color, mfc="none", label=f"N = {n}")
    spectrum.vlines((1, 3), 0, (.5, .125), color="#a0afb1", lw=1)
    spectrum.set(xlabel="Modenindex k", ylabel="Betrag des Koeffizienten",
                 xticks=(0, 1, 2, 3, 4), yticks=(0, .125, .25, .5), ylim=(-.014,.56))
    spectrum.set_yticklabels(("0", "0,125", "0,25", "0,5"))
    spectrum.legend(frameon=False, fontsize=8)
    x = np.linspace(0, 2 * np.pi, 401)
    field.plot(x, np.sin(x) + .25 * np.sin(3 * x), color=SEA, label="Eingang")
    field.plot(x, np.sin(x), color=AMBER, ls="--", label="Testkanal")
    field.vlines(np.pi / 2, .75, 1, lw=2, color=INK)
    field.set(xlabel="Ort x", ylabel="Feldwert", xticks=[0, np.pi / 2, np.pi, 2*np.pi])
    field.set_xticklabels(["0", "π/2", "π", "2π"])
    field.legend(frameon=False, fontsize=8, loc="lower left")
    for ax in (spectrum, field):
        ax.spines[["right", "top"]].set_visible(False)
        ax.grid(axis="y", color="#d7e3e1", lw=.55)
        ax.tick_params(labelsize=8)
    save(fig, "fourier_filter.pdf")


if __name__ == "__main__":
    transport()
    fourier()
