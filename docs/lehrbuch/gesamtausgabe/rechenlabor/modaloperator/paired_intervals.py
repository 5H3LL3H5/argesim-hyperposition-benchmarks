"""Paired test-field bootstrap. Training seeds are averaged, never resampled as fields."""

import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

SEEDS = (2027, 73, 3917)
CONTRASTS = (
    ("nominal", ("FNO-small", "n96"), ("Strang-FNO", "n96")),
    ("nominal", ("Strang", "no_fit"), ("Strang-FNO", "n96")),
    ("family_test", ("FNO-cond", "family"), ("Strang-FNO-cond", "family")),
    ("family_test", ("Strang", "no_fit"), ("Strang-FNO-cond", "family")),
)


def intervals(directory, repetitions=10000, seed=9027):
    samples = defaultdict(dict)
    for file in ("neural_samples.csv", "structured_samples.csv"):
        with (directory / file).open(encoding="utf-8") as stream:
            for r in csv.DictReader(stream):
                group = (r["model"], r["case"], r["scenario"], int(r["seed"]))
                samples[group][int(r["sample"])] = 50 * (float(r["u"]) + float(r["v"]))

    def per_field(model, case, scenario):
        seeds = (0,) if model == "Strang" else SEEDS
        fields = []
        for train_seed in seeds:
            values = samples[model, case, scenario, train_seed]
            if set(values) != set(range(32)):
                raise ValueError("the contrast requires all 32 paired test fields")
            fields.append([values[i] for i in range(32)])
        return np.mean(fields, axis=0)

    indices = np.random.default_rng(seed).integers(0, 32, size=(repetitions, 32))
    out = []
    for scenario, base, candidate in CONTRASTS:
        delta = per_field(*base, scenario) - per_field(*candidate, scenario)
        low, high = np.quantile(delta[indices].mean(axis=1), (0.025, 0.975))
        out.append(
            {
                "scenario": scenario,
                "baseline": base[0],
                "candidate": candidate[0],
                "gain_pp": delta.mean(),
                "p025_pp": low,
                "p975_pp": high,
                "test_pairs": 32,
                "replicates": repetitions,
                "seed": seed,
            }
        )
    return out


def write_intervals(directory):
    rows = intervals(directory)
    with (directory / "paired_intervals.csv").open(
        "w", newline="", encoding="utf-8"
    ) as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "directory",
        nargs="?",
        type=Path,
        default=Path(__file__).resolve().parent / "results",
    )
    write_intervals(p.parse_args().directory)
