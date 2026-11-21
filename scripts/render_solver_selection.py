"""Rebuild the solver-selection tables and vector figures from measured evidence."""

import csv
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from argesim_benchmarks import InitialValueProblem, qss1, rk4

DOCS = ROOT / "docs"
ANALYTIC = ("decay", "oscillator", "diagonal", "rotated", "tracking")
ARGESIM = ("C03", "C05", "C07", "C09", "C11", "C12", "C13", "C21")
QUANTIZED = (
    "qss1",
    "qss2",
    "qss3",
    "qss4",
    "cqss1",
    *(
        f"{family}{n}"
        for family in ("liqss", "mliqss", "eliqss", "cheqss")
        for n in (1, 2, 3)
    ),
    "liqss-bdf",
    "bqss1",
    "qss1-log",
    "qss2-log",
)
GROUPS = {
    "Quantized": QUANTIZED,
    "Explicit RK": ("rk4", "rk45"),
    "Implicit": ("Radau", "BDF"),
}
COLORS = ("#006b71", "#be591c", "#523c84")


def rows_and_manifest():
    data = DOCS / "evidence/qss-selection.csv"
    manifest = json.loads(data.with_suffix(".json").read_text())
    if hashlib.sha256(data.read_bytes()).hexdigest() != manifest["csv_sha256"]:
        raise ValueError("selection CSV differs from its manifest")
    with data.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    keys = {(r["case"], r["method"], r["level"]) for r in rows}
    expected = {
        (c, m, str(i))
        for c in ANALYTIC
        for methods in GROUPS.values()
        for m in methods
        for i in range(3)
    }
    for c in ARGESIM:
        expected.update(
            (c, m, str(i))
            for m in ("bqss1", "qss1-log", "qss2-log", "qss1", "qss2")
            for i in range(3)
        )
        expected.update((c, m, "") for m in GROUPS["Explicit RK"])
    expected.update(("C05", m, str(i)) for m in GROUPS["Implicit"] for i in range(3))
    expected.update(("C05", "bqss1", str(i)) for i in range(3, 6))
    if (
        keys != expected
        or len(rows) != len(keys)
        or len(keys) != manifest["configurations"]
    ):
        raise ValueError("incomplete or duplicated experiment grid")
    for row in rows:
        if row["status"] in ("pass", "accuracy_miss"):
            error = float(row["error_over_limit"])
            if not np.isfinite(error) or (error <= 1) != (row["status"] == "pass"):
                raise ValueError(f"score/status mismatch: {row}")
    return rows


def fastest(rows, case, methods):
    return min(
        (
            r
            for r in rows
            if r["case"] == case and r["method"] in methods and r["status"] == "pass"
        ),
        key=lambda r: float(r["median_ms"]),
        default=None,
    )


def table(headers, values):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines.extend("| " + " | ".join(map(str, row)) + " |" for row in values)
    return "\n".join(lines)


def results(rows):
    counts = Counter(r["status"] for r in rows)
    passes = Counter(
        (r["case"], r["method"])
        for r in rows
        if r["status"] == "pass" and r["level"] not in ("3", "4", "5")
    )

    def entry(row):
        if row is None:
            return "—"
        return (
            f"{row['method']} · {float(row['median_ms']):.3g} ms · "
            f"{float(row['error_over_limit']):.3g}"
        )

    speed = table(
        ("Analytical case", *GROUPS),
        (
            (
                c.title(),
                *(entry(fastest(rows, c, methods)) for methods in GROUPS.values()),
            )
            for c in ANALYTIC
        ),
    )
    matrix = table(
        ("Configuration", *(c.title() for c in ANALYTIC)),
        (
            (m, *(passes[c, m] for c in ANALYTIC))
            for methods in GROUPS.values()
            for m in methods
        ),
    )
    repeat_methods = ("bqss1", "qss1-log", "qss2-log", "qss1", "qss2", "rk4", "rk45")
    archive = table(
        ("Case", *repeat_methods),
        ((c, *(passes[c, m] for m in repeat_methods)) for c in ARGESIM),
    )
    return f"""Across {len(rows)} configurations, {counts["pass"]} passed, {counts["accuracy_miss"]} missed the accuracy target, {counts["event_mismatch"]} had an event-count mismatch, {counts["timeout"]} reached the time limit and {counts["solver_error"]} returned a solver error or reached a work limit. The raw CSV retains failed configurations.

### Cost at the analytical target

Each entry gives the fastest passing configuration within its group, its median elapsed time for four solves and its worst error divided by the target. A score of 0.1 uses one tenth of the error allowance. The quantized group has 21 choices at each level, explicit RK has two, and the implicit group has two. This is the observed best of each tested grid.

{speed}

![Fastest passing measured times within each solver group](figures/qss-selection-cost.svg)

### Passing settings by method

Every cell gives the number of settings passing out of three. A zero may reflect accuracy, execution or budget. In the decay probe the one-state LIQSS-BDF entry uses time stepping for the whole state. In the other four probes it uses a mixed partition.

{matrix}

### The eight ARGESIM repeats

BQSS1 and each fixed/logarithmic QSS column have three primary settings. RK4 and RK45 have one each. The C05 adaptive implicit and BQSS1 refinement results are discussed below. The other quantized methods retain the earlier eight-case matrix in the [original study](SOLVER_COMPARISON.md#all-methods-and-cases).

{archive}"""


def finish_figure(fig, filename):
    path = DOCS / "figures" / filename
    fig.savefig(
        path,
        format="svg",
        metadata={"Date": None},
        bbox_inches="tight",
    )
    plt.close(fig)
    # The SVG backend writes spaces before line breaks in path data.
    path.write_text(
        "\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n"
    )


def decay_figure():
    p = InitialValueProblem(lambda t, y: (-y[0],), 0, (1,), 1.7, autonomous=True)
    q, r = qss1(p, 0.2), rk4(p, 0.2)
    x = np.array(q.states)[:, 0]
    t = np.linspace(0, p.t_bound, 300)
    fig, ax = plt.subplots(figsize=(6.8, 2.45), layout="constrained")
    ax.plot(t, np.exp(-t), color="#2e3a45", label="Exact decay")
    ax.step(
        q.times,
        [*x[:-1], x[-2]],
        where="post",
        ls="--",
        color="#648b8e",
        label="Quantized input q",
    )
    ax.plot(q.times, x, marker="o", ms=3, color=COLORS[0], label="QSS1 state x")
    ax.plot(
        r.times,
        np.array(r.states)[:, 0],
        ls="none",
        marker="x",
        ms=4,
        color=COLORS[1],
        label="RK4 samples",
    )
    ax.axhline(0.5, color="#858b8f", ls=":", lw=1)
    ax.text(1.67, 0.52, "guard at 0.5", ha="right", color="#515b63", fontsize=8)
    ax.set(xlabel="Time", ylabel="State", xlim=(0, p.t_bound), ylim=(0.0, 1.06))
    ax.legend(ncol=2, frameon=False, fontsize=8, loc="upper right")
    finish_figure(fig, "qss-decay.svg")


def cost_figure(rows):
    fig, ax = plt.subplots(figsize=(6.8, 2.8), layout="constrained")
    for offset, (label, methods), color, marker in zip(
        (-0.18, 0, 0.18), GROUPS.items(), COLORS, ("o", "s", "D")
    ):
        winners = [fastest(rows, c, methods) for c in ANALYTIC]
        x = [float(row["median_ms"]) if row is not None else np.nan for row in winners]
        ax.scatter(
            x,
            np.arange(len(ANALYTIC)) + offset,
            label=label,
            color=color,
            marker=marker,
            s=29,
        )
    ax.set_xscale("log")
    ax.set_yticks(range(len(ANALYTIC)), [c.title() for c in ANALYTIC])
    ax.invert_yaxis()
    ax.set_xlabel("Median time for four solves (ms, logarithmic scale)")
    ax.grid(axis="x", alpha=0.25)
    ax.legend(
        loc="lower center", bbox_to_anchor=(0.5, 1), ncol=3, frameon=False, fontsize=8.5
    )
    finish_figure(fig, "qss-selection-cost.svg")


def main():
    rows = rows_and_manifest()
    p = DOCS / "SOLVER_SELECTION.md"
    start = "<!-- BEGIN SELECTION RESULTS -->"
    end = "<!-- END SELECTION RESULTS -->"
    before, rest = p.read_text().split(start)
    _, after = rest.split(end)
    p.write_text(before + start + "\n" + results(rows) + "\n" + end + after)
    matplotlib.rcParams.update(
        {
            "svg.hashsalt": "argesim-selection",
            "svg.fonttype": "none",
            "font.size": 9,
            "axes.spines.right": False,
            "axes.spines.top": False,
        }
    )
    (DOCS / "figures").mkdir(exist_ok=True)
    decay_figure()
    cost_figure(rows)


if __name__ == "__main__":
    main()
