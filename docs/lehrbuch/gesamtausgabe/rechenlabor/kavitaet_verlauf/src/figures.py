"""Create the two vectors and high-resolution print previews from the numerical tables."""

import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker


def records(path):
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def save(fig, folder, stem):
    for typ in ("pdf", "svg", "png"):
        fig.savefig(
            folder / f"{stem}.{typ}",
            dpi=230,
            facecolor="white",
            bbox_inches="tight",
            pad_inches=0.06,
        )
    plt.close(fig)


def figures(results, folder):
    folder.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.labelsize": 8.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.edgecolor": "#61747e",
            "axes.labelcolor": "#263d47",
            "xtick.color": "#263d47",
            "ytick.color": "#263d47",
            "legend.frameon": False,
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )
    data = records(results / "verlauf.csv")
    fig, ax = plt.subplots(figsize=(6.45, 2.75), layout="constrained")
    for method, label, color, linestyle in [
        ("direkt_fourier", "Fourier direkt", "#b44d22", "-"),
        ("korrektur_hankel", "Grobgitter + Hankel", "#136a77", "-"),
        ("rollout", "Freier Zeitschrittoperator", "#6a538c", "--"),
    ]:
        series = [r for r in data if r["method"] == method and int(r["k"]) > 0]
        x = np.array([int(r["k"]) for r in series])
        y = np.array([100 * float(r["rel"]) for r in series])
        ax.plot(x, y, color=color, ls=linestyle, lw=1.15, label=label)
        old = np.array([r["book7"] == "True" for r in series])
        ax.scatter(
            x[old], y[old], s=11, color=color, edgecolors="white", linewidths=0.35, zorder=3
        )
    ax.axhline(1, color="#37464c", lw=0.9, ls=":", label="Feldgrenze 1 %")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlim(4, 350000)
    ax.set_ylim(0.06, 2500)
    ax.set_yticks([0.1, 1, 10, 100, 1000], labels=["0,1", "1", "10", "100", "1 000"])
    ax.set_xticks(
        [4, 32, 256, 2048, 16384, 65536, 350000],
        labels=["4", "32", "256", "2 048", "16 384", "65 536", "350 000"],
    )
    ax.xaxis.set_minor_locator(ticker.NullLocator())
    ax.grid(axis="y", which="major", lw=0.5, color="#d8e0e1")
    ax.set_xlabel("D2Q9-Takt k")
    ax.set_ylabel("Relativer Feldfehler (%)")
    ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, 1.27),
        ncol=2,
        columnspacing=1.3,
        handlelength=2.5,
    )
    save(fig, folder, "fehlerverlauf")
    data = records(results / "smooth_fenster.csv")
    fig, axes = plt.subplots(1, 2, figsize=(6.5, 2.55), layout="constrained")
    for ax, side, title in zip(
        axes, ["entry", "exit"], ["Beginn der Überblendung", "Ende der Überblendung"]
    ):
        anchor = 32768 if side == "entry" else 65536
        for name, label, c, ls in [
            ("hard", "Abrupter Wechsel", "#b44d22", "--"),
            ("smooth", "Gleitender Wechsel", "#136a77", "-"),
        ]:
            pts = [
                r
                for r in data
                if r["re"] == "975" and r["method"] == name and r["side"] == side
            ]
            x = [int(r["k"]) - anchor for r in pts]
            y = [float(r["delta_max_U"]) for r in pts]
            ax.plot(x, y, color=color, lw=1.45, ls=linestyle, label=label)
        ax.set_yscale("log")
        ax.set_title(title, loc="left", fontsize=9, fontweight="semibold")
        ax.set_xlabel(f"Takte relativ zu {anchor:,}".replace(",", " "))
        ax.grid(axis="y", lw=0.5, color="#d8e0e1")
        ax.axvline(0, color="#53636d", lw=0.7, ls=":")
    axes[0].set_ylabel("Lokaler Fehler je 4 Takte / U")
    axes[0].legend(loc="lower right", fontsize=7.2)
    axes[1].yaxis.set_label_position("right")
    save(fig, folder, "uebergabe")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("results", type=Path)
    p.add_argument("figures", type=Path)
    a = p.parse_args()
    figures(a.results, a.figures)
