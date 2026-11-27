"""Score dense trajectories and nonforecast controls. The truth enters only here."""

import argparse
import csv
import json
from functools import lru_cache
from pathlib import Path

import numpy as np
from design import ORIGINAL, RE, N
from fields import KINDS, Frozen, diagnostics, lid_value, prolong, raw_field
from stepper import Stepper, coefficients, support_grid


def write_csv(path, rows):
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


class Projection:
    """Small least-squares problem over interior velocity components, not boundary rows."""

    def __init__(self, basis):
        self.basis = basis
        b = basis.reshape(-1, N, N, 2)[:, 1:-1, 1:-1, :].reshape(basis.shape[0], -1)
        self.dual = np.linalg.solve(b @ b.T, b)

    def field(self, target):
        z = target[1:-1, 1:-1].reshape(-1) @ self.dual.T
        return (z @ self.basis).reshape(N, N, 2)


def summary(rows):
    finite = [r for r in rows if r["k"] > 0]
    end = finite[-1]
    bad = [r for r in finite if not r["pass_both"]]
    worst = max(finite, key=lambda r: r["rel"])
    point = max(finite, key=lambda r: r["max_U"])
    k = np.array([r["k"] for r in rows])
    a = np.array([r["error_sq"] for r in rows])
    b = np.array([r["ref_sq"] for r in rows])
    weights = np.diff(k)
    space_time = np.sqrt(
        np.sum((a[:-1] + a[1:]) * weights) / np.sum((b[:-1] + b[1:]) * weights)
    )
    out = {
        "method": end["method"],
        "n_positive": len(finite),
        "n_pass": len(finite) - len(bad),
        "end_rel": end["rel"],
        "end_max_U": end["max_U"],
        "worst_rel": worst["rel"],
        "worst_rel_k": worst["k"],
        "worst_max_U": point["max_U"],
        "worst_max_U_k": point["k"],
        "init_max_U": rows[0]["max_U"],
        "space_time_rel": space_time,
        "first_fail_k": bad[0]["k"] if bad else None,
        "n_book_pass": sum(r["pass_both"] for r in finite if r["book7"]),
        "n_new_pass": sum(r["pass_both"] for r in finite if r["new_time"]),
        "n_start_pass": sum(r["pass_both"] for r in finite if r["k"] <= 4096),
        "from16_worst_rel": max(r["rel"] for r in finite if r["k"] >= 16),
        "from4096_worst_rel": max(r["rel"] for r in finite if r["k"] >= 4096),
        "new_worst_rel": max(r["rel"] for r in finite if r["new_time"]),
        "after_last_failure_k": next(
            (r["k"] for r in finite if bad and r["k"] > bad[-1]["k"]), None
        ),
    }
    return out


def evaluate(inputs, raw, results):
    positive = np.loadtxt(inputs / "ticks257.txt", dtype=int)
    klist = np.r_[0, positive]
    fit_times = set(
        json.loads((inputs / "daten/operatoren/aufbau_direkt.json").read_text())[
            "training_steps"
        ]
    )
    design_times = set(np.loadtxt(inputs / "src/zeitpunkte.txt", dtype=int))
    support = support_grid(positive)
    support_set = set(support)
    frozen = {
        f"{group}_{kind}": Frozen(inputs, group, kind)
        for group in ("direkt", "korrektur")
        for kind in KINDS
    }
    model = Stepper(inputs, results / "stepper.npz")
    rollout = model.rollout(klist)
    head = model.head(RE)
    projectors = {
        g: Projection(frozen[f"{g}_fourier"].basis) for g in ("direkt", "korrektur")
    }
    prev_coeff = np.zeros(rollout.shape[1])
    prev_tick = 0

    @lru_cache(maxsize=12)
    def mean_field(k):
        return 0.5 * (raw_field(raw, N, 950, k) + raw_field(raw, N, 1050, k))

    def baseline(k):
        j = np.searchsorted(support, k)
        if support[j] == k:
            return mean_field(k)
        left, right = int(support[j - 1]), int(support[j])
        w = (k - left) / (right - left)
        return (1 - w) * mean_field(left) + w * mean_field(right)

    groups = {}
    for start in range(0, len(klist), 10):
        times = klist[start : start + 10]
        coarse = [raw_field(raw, 65, RE, int(k) // 4) for k in times]
        outputs = {name: f.predict(times, RE, coarse) for name, f in frozen.items()}
        outputs["rollout"] = model.fields(rollout[start : start + len(times)])
        for i, k_orig in enumerate(times):
            k = int(k_orig)
            truth = raw_field(raw, N, RE, k)
            coarse_f = prolong(coarse[i])
            fields = {name: array[i] for name, array in outputs.items()}
            single_step = (
                model.advance(prev_coeff, prev_tick, k, head) if k else prev_coeff
            )
            fields["one_step_reset"] = model.fields(single_step[None, :])[0]
            prev_coeff = coefficients(truth, model.basis)
            prev_tick = k
            fields["interpolation_same_time"] = mean_field(k)
            fields["interpolation_sparse_time"] = baseline(k)
            fields["coarse_only"] = coarse_f
            fields["pod_oracle_direct"] = lid_value(projectors["direkt"].field(truth))
            fields["pod_oracle_correction"] = coarse_f + projectors["korrektur"].field(
                truth - coarse_f
            )
            for name, field in fields.items():
                metrics = diagnostics(field, truth)
                if not np.isfinite(metrics["max_U"]):
                    raise ArithmeticError(f"{name} produced nonfinite fields at {k}")
                row = dict(
                    method=name,
                    k=k,
                    t_star=k * 0.1 / 256,
                    book7=k in ORIGINAL,
                    train_time=k in fit_times,
                    new_time=k > 0 and k not in design_times,
                    stepper_fit_time=k in support_set,
                    **metrics,
                    pass_both=(metrics["rel"] <= 0.01 and metrics["max_U"] <= 0.01)
                    if k
                    else None,
                )
                groups.setdefault(name, []).append(row)
    write_csv(
        results / "verlauf.csv", [row for series in groups.values() for row in series]
    )
    condensed = [summary(rows) for rows in groups.values()]
    write_csv(results / "vergleich.csv", condensed)
    with (inputs / "daten/operatoren/test.csv").open() as f:
        legacy = list(csv.DictReader(f))
    mismatch = []
    for name in frozen:
        by_tick = {r["k"]: r for r in groups[name]}
        group, kind = name.split("_", 1)
        for row in legacy:
            if (row["art"], row["kern"]) == (group, kind):
                rr = by_tick[int(row["step"])]
                mismatch.append(
                    max(abs(float(row[key]) - rr[key]) for key in ("rel", "max_U"))
                )
    if len(mismatch) != 98 or max(mismatch) > 1e-9:
        raise ArithmeticError(f"archived-model replay failed: {max(mismatch)}")
    facts = {
        "positive": len(positive),
        "new_times": len(set(positive) - design_times),
        "startup": int(sum(positive <= 4096)),
        "stepper_fit_positive": len(support) - 1,
        "stepper_never_fit_positive": len(positive) - len(support) + 1,
        "old_pairs_reproduced": len(mismatch),
        "worst_old_metric_delta": max(mismatch),
        "positions": len(klist),
        "models": len(frozen),
    }
    (results / "design.json").write_text(json.dumps(facts, indent=2) + "\n")
    print(facts, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for x in ("inputs", "raw", "results"):
        p.add_argument(x, type=Path)
    a = p.parse_args()
    evaluate(a.inputs, a.raw, a.results)
