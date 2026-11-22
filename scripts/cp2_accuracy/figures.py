"""Rebuild the five vector figures from archived field arrays and measurement tables."""

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[2] / "docs/lehrbuch/studienbuch"
DATA = ROOT / "material/cp2_genauigkeit"
DEST = ROOT / "abbildungen"
INK = "#173950"
TEAL = "#00776a"
RUST = "#a74324"
GOLD = "#a97410"
plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "font.size": 9,
        "axes.labelsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.labelcolor": INK,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "axes.edgecolor": "#71848a",
        "axes.axisbelow": True,
        "legend.frameon": False,
        "legend.fontsize": 8,
        "pdf.fonttype": 42,
    }
)


def read(name):
    return json.loads((DATA / name).read_text())


def save(name, fig):
    fig.savefig(
        DEST / (name + ".pdf"),
        bbox_inches="tight",
        pad_inches=0.04,
        metadata={
            "CreationDate": None,
            "ModDate": None,
            "Creator": "ARGESIM Rechenlabor",
        },
    )
    plt.close(fig)


def rope():
    d = np.load(DATA / "saite_beispiel.npz")
    x = d["x"]
    ref = d["ref"][0]
    fig, ax = plt.subplots(2, 1, sharex=True, figsize=(6.8, 3.05), layout="constrained")
    ax[0].plot(x, ref * 1000, color=INK, label="exakt")
    ax[0].plot(x, d["old"][0] * 1000, "--", color=RUST, label="bisheriges FNO")
    ax[0].set_ylabel("Auslenkung [mm]")
    ax[0].legend(ncol=2, loc="lower center")
    for key, label, col in [
        ("old", "bisheriges FNO", RUST),
        ("new", "lineare Fourier-Schicht", TEAL),
    ]:
        ax[1].plot(x, (d[key][0] - ref) * 1000, color=col, label=label, lw=1.4)
    ax[1].legend(ncol=2, loc="upper center")
    ax[1].set(xlabel="Ort [m]", ylabel="Fehler [mm]")
    for axis in ax:
        axis.grid(axis="y", alpha=0.22)
    save("fno_saite_feld", fig)
    fig, ax = plt.subplots(1, 2, figsize=(6.9, 2.65), layout="constrained")
    s = read("saite.json")
    for t, mark, col in [(5, "o", TEAL), (8, "s", RUST)]:
        pts = [p for p in s["plucks"] if p["n"] == 501 and p["time"] == t]
        ax[0].plot(
            [p["position"] for p in pts],
            [p["new"]["abs_rms_m"] * 1e6 for p in pts],
            marker=mark,
            color=col,
            label=f"{t} s",
        )
    ax[0].set(xlabel="Zupfposition / Saitenlänge", ylabel="RMS-Fehler [µm]")
    ax[0].legend()
    for dt, mark, col in [(0.025, "o", TEAL), (0.1, "s", RUST)]:
        pts = [p for p in s["ablation"] if p["dt"] == dt]
        ax[1].plot(
            [p["modes"] for p in pts],
            [p["worst_rms_m"] * 1e6 for p in pts],
            marker=mark,
            color=col,
            label=f"Δt = {str(dt).replace('.', ',')} s",
        )
    ax[1].set(yscale="log", xlabel="Behaltene Moden", ylabel="Größter RMS-Fehler [µm]")
    ax[1].legend()
    for axis in ax:
        axis.grid(axis="y", alpha=0.22)
    save("fno_saite_moden", fig)


def cavity():
    d = np.load(DATA / "kavitaet_beispiel.npz")
    target = np.linalg.norm(d["ref"], axis=0)
    fig, axes = plt.subplots(1, 3, figsize=(7.3, 2.35), layout="constrained")
    from matplotlib.colors import SymLogNorm

    errors = [
        d["old"] - target,
        np.linalg.norm(d["affine"], axis=0) - target,
        np.linalg.norm(d["new"], axis=0) - target,
    ]
    norm = SymLogNorm(linthresh=0.0001, vmin=-0.04, vmax=0.04)
    for ax, e, name in zip(
        axes, errors, ["Bisheriges FNO", "Affines Modell", "Affin + FNO"]
    ):
        im = ax.imshow(
            e[1:-1, 1:-1],
            origin="lower",
            cmap="RdBu_r",
            norm=norm,
            interpolation="nearest",
        )
        ax.set_title(name, fontsize=10)
        ax.set(xticks=[], yticks=[], xlabel="Innenraum")
    cb = fig.colorbar(
        im, ax=axes, shrink=0.87, extend="both", ticks=[-0.01, -0.001, 0, 0.001, 0.01]
    )
    cb.ax.set_yticklabels(["−0,01", "−0,001", "0", "+0,001", "+0,01"])
    cb.set_label("Fehler / Deckeltempo")
    save("fno_kavitaet_feld", fig)
    d = read("zielkalibrierung.json")
    fig, ax = plt.subplots(figsize=(6.7, 2.55), layout="constrained")
    y = np.arange(len(d))
    for i, (key, label, col, mark) in enumerate(
        [
            ("blind", "ohne neue Referenz", RUST, "s"),
            ("calibrated", "13 Referenzen, affin", GOLD, "^"),
            ("adapted", "13 Referenzen + FNO", TEAL, "o"),
        ]
    ):
        ax.scatter(
            [r[key]["mean"] * 100 for r in d],
            y + (i - 1) * 0.13,
            color=col,
            marker=mark,
            label=label,
            s=37,
        )
    ax.set_yticks(
        y,
        [
            "17² · 0,0875 · 16",
            "25² · 0,1000 · 12",
            "21² · 0,1000 · 16",
            "29² · 0,1125 · 20",
        ],
    )
    ax.invert_yaxis()
    ax.set_xscale("log")
    ax.set_xlabel("Mittlerer relativer Vektorfehler [%]")
    ax.set_ylabel("Gitter · Deckeltempo · Schritt")
    ax.grid(axis="x", which="both", alpha=0.17)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, 1.25), ncol=3, fontsize=7.5)
    save("fno_kavitaet_transfer", fig)
    d = np.load(DATA / "kavitaet_profile.npz")
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 3.0), layout="constrained")
    for n, col, ls in [(65, GOLD, ":"), (129, RUST, "--"), (257, TEAL, "-")]:
        z, u, v = d[f"profile_{n}"]
        axes[0].plot(u, z, ls, color=col, label=f"{n}²")
        axes[1].plot(z, v, ls, color=col)
    uu, vv = d["ghia_u"], d["ghia_v"]
    axes[0].scatter(
        uu[:, 1],
        uu[:, 0],
        s=22,
        facecolor="white",
        edgecolor=INK,
        label="Ghia u. a.",
        zorder=4,
    )
    axes[1].scatter(
        vv[:, 0], vv[:, 1], s=22, facecolor="white", edgecolor=INK, zorder=4
    )
    axes[0].set(xlabel="Horizontale Geschwindigkeit / Deckeltempo", ylabel="Höhe y / L")
    axes[1].set(
        xlabel="Position x / L", ylabel="Vertikale Geschwindigkeit / Deckeltempo"
    )
    axes[0].legend(ncol=2, loc="lower right", fontsize=7.5)
    for axis in axes:
        axis.grid(alpha=0.19)
    save("fno_kavitaet_profile", fig)


if __name__ == "__main__":
    rope()
    cavity()
