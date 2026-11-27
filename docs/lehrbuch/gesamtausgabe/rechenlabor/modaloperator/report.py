"""Build charts and the editable German chapter directly from the measured CSV files."""

import argparse
import csv
import json
import re
import subprocess
from pathlib import Path
from statistics import mean, median

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.ticker import ScalarFormatter
from physics import NOMINAL, reference_matrix

ROOT = Path(__file__).resolve().parent
CH = ROOT / "chapter"
ORDER = [
    "FNO-small",
    "UNO",
    "CoDA-NO",
    "Modal24",
    "Generator3",
    "Strang",
    "Strang-R24",
    "Strang-FNO",
]
LABEL = {
    "FNO-small": "FNO",
    "Strang-R24": "Strang + R24",
    "Strang-FNO": "Strang + FNO",
    "Strang-fixed": "Strang fest",
    "FNO-cond": "FNO kond.",
    "Strang-FNO-cond": "Strang + FNO kond.",
}


def load_rows(results):
    rows = []
    for name in ("neural", "structured"):
        with (results / (name + ".csv")).open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for key in (
                    "u",
                    "v",
                    "response",
                    "response_abs_l2",
                    "train_s",
                    "latency_ms",
                ):
                    row[key] = float(row[key]) if row[key] else None
                for key in ("seed", "n", "parameters"):
                    row[key] = int(row[key])
                rows.append(row)
    return rows


def group(rows, model, scenario="nominal", case=None, seeds=None):
    if case is None:
        case = "no_fit" if model in ("Strang", "Strang-fixed") else "n96"
    if seeds is None and model in ("Modal24", "Generator3", "Strang-R24"):
        seeds = [42201]
    found = [
        r
        for r in rows
        if (r["model"], r["case"], r["scenario"]) == (model, case, scenario)
        and (seeds is None or r["seed"] in seeds)
    ]
    if not found:
        raise ValueError(f"missing results for {model}, {case}, {scenario}, {seeds}")
    return found


def err(rows):
    return 100 * mean((r["u"] + r["v"]) / 2 for r in rows)


def de(x, digits=2):
    return f"{x:.{digits}f}".replace(".", ",")


def pct(value):
    if 0 < value < 0.001:
        exponent = int(np.floor(np.log10(value)))
        power = str(exponent).translate(str.maketrans("-0123456789", "⁻⁰¹²³⁴⁵⁶⁷⁸⁹"))
        return f"{de(value / 10**exponent)}·10{power}"
    return de(value, 3 if 0 < value < 0.1 else 2)


def table(labels, values):
    sep = ["---"] + ["---:"] * (len(labels) - 1)
    return "\n".join(
        "| " + " | ".join(map(str, row)) + " |" for row in [labels, sep, *values]
    )


def figures(rows, vector_dir=None):
    def save_figure(fig, stem, dpi):
        fig.savefig(out / f"{stem}.png", dpi=dpi, bbox_inches="tight")
        if vector_dir is not None:
            vector_dir.mkdir(parents=True, exist_ok=True)
            for ext, metadata in (("svg", {"Date": None}), ("pdf", {"CreationDate": None})):
                fig.savefig(vector_dir / f"modal_{stem}.{ext}", bbox_inches="tight", metadata=metadata)

    out = CH / "figures"
    out.mkdir(exist_ok=True)
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "svg.hashsalt": "argesim-modaloperator",
            "font.size": 9,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.labelcolor": "#29414c",
            "text.color": "#203743",
            "axes.edgecolor": "#91a1a6",
            "xtick.color": "#435961",
            "ytick.color": "#435961",
        }
    )
    coords = np.linspace(0, 1, 101)
    phi = np.outer(np.sin(np.pi * coords), np.sin(np.pi * coords))
    block = reference_matrix(((1, 1),), NOMINAL)[0]
    cmap = LinearSegmentedColormap.from_list(
        "warm", ["#f4f4df", "#efc567", "#de8947", "#a33b3c", "#55263b"]
    )
    fig, axes = plt.subplots(1, 3, figsize=(7, 2.47), layout="constrained")
    for ax, a, title in zip(
        axes,
        (1.0, block[0, 1], block[1, 1]),
        ("Ausgang  ·  v(0)", "Antwort  ·  u(0,4)", "Rest  ·  v(0,4)"),
    ):
        im = ax.imshow(
            a * phi.T, origin="lower", extent=(0, 1, 0, 1), cmap=cmap, vmin=0, vmax=1
        )
        ax.set(title=title, xticks=[0, 0.5, 1], yticks=[0, 0.5, 1], xlabel="x")
        ax.text(
            0.5,
            0.5,
            de(a, 3),
            ha="center",
            va="center",
            fontweight="bold",
            color="white" if a > 0.38 else "#2e2e2c",
            bbox={
                "boxstyle": "round,pad=0.17",
                "facecolor": "black" if a > 0.38 else "white",
                "alpha": 0.38,
                "edgecolor": "none",
            },
        )
    axes[0].set_ylabel("y")
    fig.colorbar(im, ax=axes, ticks=[0, 0.5, 1], fraction=0.027, pad=0.015)
    save_figure(fig, "austausch", 175)
    plt.close(fig)

    fig, axes = plt.subplots(
        1,
        2,
        figsize=(7.35, 2.72),
        layout="constrained",
        gridspec_kw={"width_ratios": [1, 1.65]},
    )
    n = np.array([2, 8, 24, 96])
    colors = {
        "FNO-small": "#24608a",
        "UNO": "#d47734",
        "CoDA-NO": "#875979",
        "Strang-FNO": "#087b74",
        "Modal24": "#24608a",
        "Generator3": "#ac5b34",
    }
    for i, names in enumerate(
        (("Modal24", "Generator3"), ("FNO-small", "UNO", "CoDA-NO", "Strang-FNO"))
    ):
        ax = axes[i]
        for j, name in enumerate(names):
            y = [
                err(group(rows, name, case=f"n{k}", seeds=[42201 if i == 0 else 2027]))
                for k in n
            ]
            ax.plot(
                n,
                np.asarray(y) * (1e6 if i == 0 else 1),
                color=colors[name],
                marker=("o", "s", "^", "D")[j],
                markersize=4,
                linestyle=("-", "--", "-.", ":")[j],
                label=LABEL.get(name, name),
            )
        ax.set_xscale("log")
        ax.set_xticks(n, labels=[str(k) for k in n])
        ax.minorticks_off()
        ax.grid(axis="y", alpha=0.23)
        ax.set_xlabel("Trainingsfeldpaare")
        ax.legend(
            frameon=False,
            fontsize=7,
            ncols=1 if i == 0 else 2,
            loc="upper right" if i == 0 else "lower left",
        )
        ax.set_title(
            "Direkte Fits" if i == 0 else "Neuronale Modelle",
            fontsize=10,
            fontweight="bold",
        )
    axes[0].set_ylabel(r"Mittlerer Kanalfehler ($10^{-6}$ %)")
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Mittlerer Kanalfehler (%)")
    axes[1].set_ylim(0.12, 180)
    axes[1].set_yticks([0.3, 1, 3, 10, 30, 100])
    axes[1].yaxis.set_major_formatter(ScalarFormatter())
    save_figure(fig, "lerndaten", 180)
    plt.close(fig)


def contents(rows, results):
    idrows = []
    for m in ORDER:
        g = group(rows, m)
        fit = median(r["train_s"] for r in g)
        idrows.append(
            [
                LABEL.get(m, m),
                g[0]["parameters"],
                *[pct(100 * mean(r[k] for r in g)) for k in ("u", "v", "response")],
                de(fit, 5 if fit < 0.01 else 2) if fit else "–",
                de(median(r["latency_ms"] for r in g), 3),
            ]
        )
    idtable = table(
        [
            "Modell",
            "Gewichte",
            "$e_u$ / %",
            "$e_v$ / %",
            "$e_\\Delta$ / %",
            "Fit / s",
            "Paar / ms",
        ],
        idrows,
    )
    archive = json.loads((ROOT / "reference" / "messung_kapazitaet.json").read_text())[
        "rows"
    ]
    am = [
        100
        * mean(r["counterfactual_relative_l2_u"] for r in archive if r["model"] == m)
        for m in ORDER[:3]
    ]
    local = [100 * mean(r["response"] for r in group(rows, m)) for m in ORDER[:3]]
    ar_text = (
        f"**Archiv und neuer Lauf.** Der PR meldet für FNO, UNO und CoDA-NO "
        f"{de(am[0])} %, {de(am[1])} % und {de(am[2])} % Kopplungsfehler. Die unabhängigen "
        f"Neutrainings ergeben {de(local[0])} %, {de(local[1])} % und {de(local[2])} %. "
        "Die kleine Abweichung bei CoDA-NO ist im Einzelvergleich sichtbar. "
        "Die Zahlen im Archiv und die hiesigen Zeiten wurden auf getrennten Ausführungen erhoben."
    )
    steps = []
    for m in ["FNO-small", "UNO", "CoDA-NO", "Strang-FNO"]:
        steps.append(
            [
                LABEL.get(m, m),
                *[
                    pct(err(group(rows, m, case=c, seeds=[2027])))
                    for c in ("n8", "n8_steps", "n96")
                ],
            ]
        )
    mt = []
    for m in ORDER:
        a, b = group(rows, m, "pure_new"), group(rows, m, "mixed_new")
        mt.append(
            [
                LABEL.get(m, m),
                *[
                    pct(100 * mean(r[k] for r in g))
                    for g, k in [(a, "u"), (a, "v"), (b, "u"), (b, "v")]
                ],
            ]
        )
    shifts = ["diff_swap", "k_low", "k_high", "t_short", "t_long"]
    st = []
    for m in [
        *ORDER[:3],
        "Modal24",
        "Generator3",
        "Strang-fixed",
        "Strang",
        "Strang-R24",
        "Strang-FNO",
    ]:
        st.append([LABEL.get(m, m), *[pct(err(group(rows, m, s))) for s in shifts]])
    baseline = group(rows, "FNO-cond", "family_test", "family")
    hybrid = group(rows, "Strang-FNO-cond", "family_test", "family")
    s = err(group(rows, "Strang", "family_test"))
    cond = (
        f"**Gemessen auf den 32 ungesehenen Parametersätzen.** Bei jeweils {baseline[0]['parameters']:,} "
        f"trainierbaren Gewichten erreicht das konditionierte FNO {de(err(baseline))} % mittleren "
        f"Kanalfehler, der konditionierte Hybrid {de(err(hybrid))} %. Strang allein erreicht {de(s)} %. "
        "Die Netzwerte sind Mittel über drei Initialisierungen. "
        "Hier erhöht der gelernte Rest den Fehler der Physikbasis geringfügig. Der große Abstand zum reinen FNO entsteht überwiegend durch den Physik-Layer."
    ).replace("1,050", "1 050")
    nt = []
    for m in ["Modal24", "Generator3", "Strang-R24"]:
        nt.append(
            [
                LABEL.get(m, m),
                *[
                    pct(err(group(rows, m, case=c, seeds=[42201, 42211, 42221])))
                    for c in (
                        "noise1",
                        "noise5",
                        "noise5_modal",
                        "noise5_n8",
                        "noise5_modal_n8",
                    )
                ],
            ]
        )
    nv = [
        pct(err(group(rows, m, case="noise5", seeds=[2027])))
        for m in ["FNO-small", "UNO", "CoDA-NO", "Strang-FNO"]
    ]
    net_noise = (
        f"**Neuronale Läufe mit 5 % Pixelrauschen und 96 Trainingspaaren.** "
        f"Die gemessenen mittleren Kanalfehler betragen {nv[0]} % für FNO, {nv[1]} % für UNO, "
        f"{nv[2]} % für CoDA-NO und {nv[3]} % für Strang + FNO. "
        "Die saubere Validierung steht auch den verrauscht trainierten Netzen zur Verfügung."
    )
    sensor = []
    for m in [
        "Modal24",
        "Generator3",
        "Strang-R24",
        "FNO-small",
        "UNO",
        "CoDA-NO",
        "Strang-FNO",
    ]:
        structured = m in ("Modal24", "Generator3", "Strang-R24")
        seeds = [42201, 42211, 42221] if structured else [2027]
        sensor.append(
            [
                LABEL.get(m, m),
                *[
                    pct(err(group(rows, m, case=c, seeds=seeds)))
                    for c in ("n96", "noise5", "input5")
                ],
                pct(err(group(rows, m, case="input5_modal", seeds=seeds)))
                if structured
                else "–",
            ]
        )
    fit_seconds = sum(
        r["train_s"]
        for r in rows
        if r["scenario"] == "nominal"
        and r["model"]
        in ["FNO-small", "UNO", "CoDA-NO", "Strang-FNO", "FNO-cond", "Strang-FNO-cond"]
    )
    with (results / "paired_intervals.csv").open(encoding="utf-8") as stream:
        diffs = list(csv.DictReader(stream))
    ri = next(
        r for r in diffs if r["scenario"] == "family_test" and r["baseline"] == "Strang"
    )
    delta = float(ri["gain_pp"])
    lo, hi = float(ri["p025_pp"]), float(ri["p975_pp"])
    ci = (
        f"Die Differenz Strang minus Hybrid beträgt {de(delta)} Prozentpunkte "
        f"(95-%-Bootstrapintervall {de(lo)} bis {de(hi)}). Resampling-Einheit sind die 32 "
        "gepaarten Testfälle, nach Mittelung über die drei Netzstarts. "
        "Das Intervall beschreibt die Streuung der Testfälle bei diesen trainierten Modellen."
    )
    return {
        "ID_TABLE": idtable,
        "TOTAL_COST": de(fit_seconds, 0),
        "SENSOR_TABLE": table(
            ["Modell", "sauber", "Ziel · Pixel", "Eingang · Pixel", "Eingang · modal"],
            sensor,
        ),
        "PAIR_CI": ci,
        "ARCHIVE_TEXT": ar_text,
        "STEPS_TABLE": table(
            [
                "Modell",
                "8 Felder · 40 Schritte",
                "8 Felder · 240 Schritte",
                "96 Felder · 240 Schritte",
            ],
            steps,
        ),
        "MODES_TABLE": table(
            ["Modell", "rein · $u$", "rein · $v$", "gemischt · $u$", "gemischt · $v$"],
            mt,
        ),
        "SHIFT_TABLE": table(
            [
                "Modell",
                "Diffusion",
                "$\\kappa=0{,}45$",
                "$\\kappa=2{,}5$",
                "$T=0{,}2$",
                "$T=0{,}8$",
            ],
            st,
        ),
        "COND_TEXT": cond,
        "NOISE_TABLE": table(
            [
                "Modell",
                "1 % Pixel / 96",
                "5 % Pixel / 96",
                "5 % modal / 96",
                "5 % Pixel / 8",
                "5 % modal / 8",
            ],
            nt,
        ),
        "NOISE_NN_TEXT": net_noise,
    }


def build(pdf=True, results=ROOT / "results", runtime_results=None, vector_dir=None):
    from runtime_benchmark.chapter import runtime_text

    rows = load_rows(results)
    figures(rows, vector_dir)
    md = (CH / "manuskript.in.md").read_text(encoding="utf-8")
    runtime = runtime_results if runtime_results is not None else results / "runtime"
    if runtime_results is None and not runtime.is_dir():
        runtime = ROOT / "results" / "runtime"
    markers = {**contents(rows, results), **runtime_text(runtime)}
    for key, value in markers.items():
        md = md.replace("{{" + key + "}}", value)
    if "{{" in md:
        raise ValueError("unexpanded manuscript marker")
    (CH / "Kapitel9.md").write_text(md, encoding="utf-8")
    if pdf:
        import typst

        sections = []
        for part in md.split("<!-- page -->"):
            proc = subprocess.run(
                ["pandoc", "-f", "markdown", "-t", "typst", "--wrap=none"],
                input=part.replace("{,}", r"\text{,}"),
                text=True,
                capture_output=True,
                check=True,
            )
            # Pandoc 3.1 splits a German decimal comma into three math atoms.
            # Keep the entire decimal numeral together when setting it in Typst.
            section = re.sub(r'(\d+) upright\(","\) (\d+)', r'"\1,\2"', proc.stdout)
            sections.append(section)
        source = (
            (CH / "layout.typ").read_text() + "\n" + "\n#pagebreak()\n".join(sections)
        )
        target = CH / "Kapitel9.typ"
        target.write_text(source, encoding="utf-8")
        typst.compile(
            str(target),
            output=str(CH / "Kapitel9.pdf"),
            root=str(CH),
            timestamp=1795737600,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-pdf", action="store_true")
    parser.add_argument("--results", type=Path, default=ROOT / "results")
    parser.add_argument(
        "--runtime-results",
        type=Path,
        help="directory with both measured timing series",
    )
    parser.add_argument("--vector-dir", type=Path, help="output folder for the book plates (SVG/PDF)")
    args = parser.parse_args()
    build(not args.no_pdf, args.results, args.runtime_results, args.vector_dir)
