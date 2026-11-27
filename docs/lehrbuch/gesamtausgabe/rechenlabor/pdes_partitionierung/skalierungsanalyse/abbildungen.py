"""Vier Drucktafeln zu den in auswerten.py eingelesenen Messwerten."""

from datetime import datetime, timezone
from statistics import median

import matplotlib
import numpy as np

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.ticker import FuncFormatter

NAVY, TEAL, ORANGE, GRAY = "#17486a", "#00756b", "#ac4d16", "#53606a"
STYLES = {
    "D2Q9-MPI": (NAVY, "o", "-"),
    "QSS3": (TEAL, "s", "-"),
    "QSS4": (ORANGE, "^", "--"),
}
P = [1, 2, 4, 8]


def decimal(x, _=None):
    return f"{x:g}".replace(".", ",").replace("-", "−")


def series(points, name):
    return sorted((r for r in points if r["reihe"] == name), key=lambda r: r["p"])


def base_axes(ax):
    ax.grid(axis="y", color="#dbe4e5", linewidth=0.6)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.tick_params(length=3, width=0.65)
    ax.yaxis.set_major_formatter(FuncFormatter(decimal))


def trace(ax, xs, ys, style, bounds=None):
    c, mark, line = style
    if bounds:
        lo, hi = bounds
        ax.errorbar(
            xs,
            ys,
            yerr=(np.asarray(ys) - lo, np.asarray(hi) - ys),
            fmt="none",
            ecolor=c,
            elinewidth=0.85,
            capsize=2.7,
        )
    ax.plot(
        xs,
        ys,
        color=c,
        marker=mark,
        linestyle=line,
        linewidth=1.6,
        markersize=4.8,
        markerfacecolor="white",
        markeredgewidth=1.3,
    )


def scaling(points, costs=False):
    measures = (
        ["wand_mehr_s", "overhead_arbeiter_s", "karp_flatt_pct"]
        if costs
        else ["speedup", "effizienz_pct"]
    )
    labels = {
        "speedup": "Speedup  $S_p$",
        "effizienz_pct": "Effizienz  $E_p$  (%)",
        "wand_mehr_s": r"Mehrzeit  $\Delta_p$  (s)",
        "overhead_arbeiter_s": "Overhead  $H_p$  (Arbeiter·s)",
        "karp_flatt_pct": "Karp–Flatt  $f_p$  (%)",
    }
    fig, axes = plt.subplots(len(measures), 2, figsize=(7.15, 5.85 if costs else 4.25))
    fig.subplots_adjust(
        left=0.125,
        right=0.98,
        bottom=0.115 if not costs else 0.09,
        top=0.84 if not costs else 0.885,
        hspace=0.44,
        wspace=0.30,
    )
    for col, cases in enumerate([["D2Q9-MPI"], ["QSS3", "QSS4"]]):
        for i, key in enumerate(measures):
            ax = axes[i, col]
            base_axes(ax)
            ax.set_xlim(0.72, 8.33)
            ax.set_xticks(P)
            if i == 0:
                ax.set_title(["Voll · 350 000 Takte", "Präfix · acht Intervalle"][col])
            if i == len(measures) - 1:
                ax.set_xlabel(
                    ["MPI-Prozesse  $p$", "Logische Prozesse (LPs)  $p$"][col]
                )
            if col == 0:
                ax.set_ylabel(labels[key])
            if costs:
                ax.axhline(0, color=GRAY, ls="--", lw=1)
                if key == "karp_flatt_pct":
                    ax.set_ylim(-8, 34)
            elif key == "speedup":
                ax.plot([1, 8], [1, 8], color=GRAY, ls="--", lw=1)
                ax.axhline(1, color=GRAY, ls=":", lw=1)
                ax.set_ylim(0.65, 8.5)
            else:
                ax.axhline(100, color=GRAY, ls="--", lw=1)
                ax.set_ylim(0, 121)
            for name in cases:
                data = [r for r in series(points, name) if r[key] is not None]
                xs = [r["p"] for r in data]
                span = None
                if not costs and any(r["n"] > 1 for r in data):
                    factor = np.array(
                        [100 / p if key == "effizienz_pct" else 1 for p in xs]
                    )
                    span = tuple(
                        np.array([r[f] for r in data]) * factor
                        for f in ("s_min_feste_basis", "s_max_feste_basis")
                    )
                trace(ax, xs, [r[key] for r in data], STYLES[name], span)
    legend = [
        Line2D(
            [], [], color=c, marker=m, linestyle=line, label=n, markerfacecolor="white"
        )
        for n, (c, m, line) in STYLES.items()
    ]
    legend.append(Line2D([], [], color=GRAY, ls="--", label="Ideal"))
    fig.legend(handles=legend, ncol=4, loc="upper center", frameon=False)
    return fig


def openmp(pairs):
    fig, axes = plt.subplots(2, 1, figsize=(7.05, 4.75))
    fig.subplots_adjust(left=0.34, right=0.95, bottom=0.115, top=0.895, hspace=0.57)
    panels = [
        (
            "Voll · 350 000 Takte",
            ["Intel · Kern", "Intel · Gesamt, 7 Ausgaben", "EPYC · Kern"],
        ),
        (
            "Präfix · 1 024 oder 4 096 Takte",
            [
                "Intel · Pilot 1024",
                "Intel · erste 1024",
                "EPYC · 0 Lastprozesse",
                "EPYC · 3 Lastprozesse",
            ],
        ),
    ]
    for ax, (title, labels) in zip(axes, panels, strict=True):
        base_axes(ax)
        ax.grid(False, axis="y")
        ax.set_title(title, loc="left")
        ax.set_xscale("log")
        ax.set_xlim(0.18, 4.25)
        ax.set_xticks([0.25, 0.5, 1, 2, 4], ["0,25", "0,5", "1", "2", "4"])
        ax.set_yticks(range(len(labels)), labels)
        ax.set_ylim(len(labels) - 0.4, -0.6)
        ax.axvline(1, color=GRAY, ls=":", lw=1)
        ax.axvline(4, color=GRAY, ls="--", lw=1)
        for y, label in enumerate(labels):
            s = [r["speedup_gepaart"] for r in pairs if r["versuch"] == label]
            if label == "EPYC · Kern":
                ax.scatter(
                    s,
                    [y] * len(s),
                    marker="D",
                    facecolors="white",
                    edgecolors=NAVY,
                    s=22,
                    zorder=2,
                )
                ax.annotate(
                    " / ".join(decimal(round(v, 2)) for v in s),
                    (min(s), y),
                    xytext=(-5, 7),
                    ha="right",
                    textcoords="offset points",
                    fontsize=7.2,
                    color=NAVY,
                )
            else:
                v = median(s)
                c = NAVY if v >= 1 else ORANGE
                ax.plot([min(s), max(s)], [y, y], c=c, lw=1.6)
                ax.plot(v, y, "o", c=c, ms=4)
                ax.annotate(
                    decimal(round(v, 3)),
                    (v, y),
                    xytext=(5, 2),
                    textcoords="offset points",
                    fontsize=7.2,
                    color=c,
                )
    axes[-1].set_xlabel("Speedup  $S_4$  ·  logarithmische Skala")
    fig.legend(
        [Line2D([], [], color=GRAY, ls=":"), Line2D([], [], color=GRAY, ls="--")],
        ["Gleiche Zeit", "Ideal bei vier Threads"],
        loc="upper center",
        ncol=2,
        frameon=False,
    )
    return fig


def sparse(points):
    fig, axes = plt.subplots(1, 2, figsize=(7.15, 3.15), sharey=True)
    fig.subplots_adjust(left=0.12, right=0.98, bottom=0.20, top=0.78, wspace=0.22)
    modes = [
        ("conservative", "konservativ", (TEAL, "s", "-")),
        ("optimistic", "optimistisch", (ORANGE, "^", "--")),
    ]
    for ax, prefix, title in zip(
        axes,
        ["C19R", "rope_pilot"],
        ["C19R · volle 10 Modelltage", "Saite · Pilot über 4 s"],
        strict=True,
    ):
        base_axes(ax)
        ax.set_title(title)
        ax.set_xlabel("MPI-Prozesse  $p$")
        ax.set_xlim(0.7, 8.35)
        ax.set_xticks(P)
        ax.set_yscale("log")
        ax.set_ylim(0.035, 10)
        ax.set_yticks(
            [0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8],
            ["0,05", "0,1", "0,25", "0,5", "1", "2", "4", "8"],
        )
        ax.axhline(1, color=GRAY, ls=":", lw=1)
        ideal = np.linspace(1, 8, 225)
        ax.plot(ideal, ideal, color=GRAY, ls="--", lw=1)
        for mode, _, style in modes:
            data = series(points, prefix + "-" + mode)
            span = (
                (
                    [r["s_min_feste_basis"] for r in data],
                    [r["s_max_feste_basis"] for r in data],
                )
                if data and data[0]["n"] > 1
                else None
            )
            trace(ax, [r["p"] for r in data], [r["speedup"] for r in data], style, span)
    axes[0].set_ylabel("Speedup  $S_p$  ·  logarithmisch")
    handles = [
        Line2D([], [], label=label, color=c, marker=m, ls=line, markerfacecolor="white")
        for _, label, (c, m, line) in modes
    ]
    handles.append(Line2D([], [], color=GRAY, ls="--", label="Ideal"))
    fig.legend(handles=handles, ncol=3, loc="upper center", frameon=False)
    return fig


def zeichnen(out, points, pairs):
    stamp = datetime(2026, 11, 27, tzinfo=timezone.utc)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 8.5,
            "axes.titlesize": 10,
            "axes.titleweight": "bold",
            "axes.labelcolor": "#244354",
            "axes.titlecolor": "#193c4c",
            "axes.edgecolor": "#9ba9ae",
            "axes.linewidth": 0.65,
            "axes.labelsize": 9.3,
            "svg.hashsalt": "argesim-cp2-skalierung",
            "svg.fonttype": "none",
            "pdf.fonttype": 42,
        }
    )
    figures = [
        ("cp2_skalierung", scaling(points)),
        ("cp2_overhead_karp_flatt", scaling(points, True)),
        ("cp2_openmp_last", openmp(pairs)),
        ("pdes_c19r_saite_skalierung", sparse(points)),
    ]
    with PdfPages(
        out / "ergebnisse" / "CP2_Abbildungen.pdf", metadata={"CreationDate": stamp}
    ) as atlas:
        for name, fig in figures:
            for fmt in ("pdf", "svg", "png"):
                meta = (
                    {"Date": "2026-11-27"}
                    if fmt == "svg"
                    else {"CreationDate": stamp}
                    if fmt == "pdf"
                    else {}
                )
                fig.savefig(
                    out / "abbildungen" / (name + "." + fmt), dpi=300, metadata=meta
                )
            atlas.savefig(fig)
            plt.close(fig)
