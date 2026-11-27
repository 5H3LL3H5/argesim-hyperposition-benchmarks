"""Evaluate stored checkpoints and fit baselines. All output errors are fractions."""

import argparse
import csv
import json
import os
import platform
import sys
import time
from contextlib import redirect_stdout
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from statistics import median

import numpy as np

from physics import (
    KNOWN,
    NEW,
    NOMINAL,
    Generator,
    Modal,
    Physics,
    StrangModal,
    add_training_noise,
    counter_probe,
    fixed_split,
    probe_score,
    reference_matrix,
    scenario_sets,
    score,
    strang,
)

ROOT = Path(__file__).resolve().parent
FIT_SEEDS = (42201, 42211, 42221)
STRUCT_CASES = {
    "n2": (2, 0.0, False),
    "n4": (4, 0.0, False),
    "n8": (8, 0.0, False),
    "n24": (24, 0.0, False),
    "n96": (96, 0.0, False),
    "noise1": (96, 0.01, False),
    "noise5": (96, 0.05, False),
    "input5": (96, 0.05, False),
    "input5_modal": (96, 0.05, True),
    "noise5_n8": (8, 0.05, False),
    "noise5_modal": (96, 0.05, True),
    "noise5_modal_n8": (8, 0.05, True),
}


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def latency_ms(predict, x, repeats=21):
    for _ in range(3):
        predict(x)
    values = []
    for _ in range(repeats):
        tic = time.perf_counter_ns()
        predict(x)
        values.append((time.perf_counter_ns() - tic) / 1e6)
    return median(values)


def metrics(predict, info, scenarios, *, timing=True):
    rows, individual = [], []
    lat = latency_ms(predict, scenarios["nominal"][0][:1]) if timing else None
    for scenario, (x, y, p, modes) in scenarios.items():
        pred = predict(x, p)
        stat = score(pred, y)
        probe = {"response": None, "response_abs_l2": None}
        probe_mode = ""
        if isinstance(p, Physics):
            k = NEW[0] if scenario == "pure_new" else KNOWN[0]
            probe_mode = f"{k[0]},{k[1]}"
            px, py = counter_probe(p, k, x.shape[-1])
            probe = probe_score(predict(px, p), py)
        rows.append(
            dict(
                **info,
                scenario=scenario,
                **stat,
                **probe,
                probe_mode=probe_mode,
                latency_ms=lat,
            )
        )
        err = np.linalg.norm(
            (pred.astype(np.float64) - y).reshape(len(y), 2, -1), axis=-1
        )
        den = np.linalg.norm(y.astype(np.float64).reshape(len(y), 2, -1), axis=-1)
        for index, (eu, ev) in enumerate(err / den):
            individual.append(
                {
                    "model": info["model"],
                    "case": info["case"],
                    "seed": info["seed"],
                    "scenario": scenario,
                    "sample": index,
                    "u": eu,
                    "v": ev,
                }
            )
    return rows, individual


def structured(output, timing=True):
    scenarios = scenario_sets()
    all_rows, all_fields, block_info, generator_fits = [], [], [], []
    common = {"epochs": 0, "steps": 0, "selected_epoch": None}
    for name, fn in [
        ("Strang", strang),
        ("Strang-fixed", lambda x, p=NOMINAL: strang(x, NOMINAL)),
    ]:
        info = dict(
            model=name, case="no_fit", seed=0, n=0, parameters=0, train_s=0.0, **common
        )
        rows, fields = metrics(fn, info, scenarios, timing=timing)
        all_rows.extend(rows)
        all_fields.extend(fields)
    for case, (n, rho, modal_noise) in STRUCT_CASES.items():
        for seed in FIT_SEEDS:
            x, y = fixed_split(n, seed, 13)
            if case.startswith("input5"):
                x = add_training_noise(x, rho, seed + 3, modal_noise)
            else:
                y = add_training_noise(y, rho, seed + 3, modal_noise)
            for name, cls in [
                ("Modal24", Modal),
                ("Strang-R24", StrangModal),
                ("Generator3", Generator),
            ]:
                fit = cls.fit(x, y)
                seconds = []
                for _ in range(21 if timing else 1):
                    start = time.perf_counter_ns()
                    fit = cls.fit(x, y)
                    seconds.append((time.perf_counter_ns() - start) * 1e-9)
                info = dict(
                    model=name,
                    case=case,
                    seed=seed,
                    n=n,
                    parameters=3 if name == "Generator3" else 24,
                    train_s=median(seconds),
                    **common,
                )
                rows, fields = metrics(fit.predict, info, scenarios, timing=timing)
                all_rows.extend(rows)
                all_fields.extend(fields)
                if name == "Generator3":
                    generator_fits.append(
                        {
                            "case": case,
                            "seed": seed,
                            "du": fit.coeff[0],
                            "dv": fit.coeff[1],
                            "rate": fit.coeff[2],
                        }
                    )
                if name == "Modal24":
                    ref = reference_matrix(KNOWN, NOMINAL)[0, 0, 1]
                    learned = float(fit.blocks[0, 0, 1])
                    block_info.append(
                        {
                            "case": case,
                            "seed": seed,
                            "reference": ref,
                            "fitted": learned,
                            "relative": abs(learned / ref - 1),
                            "blocks": fit.blocks.tolist(),
                        }
                    )
    write_csv(output / "generator_fits.csv", generator_fits)
    write_csv(output / "structured.csv", all_rows)
    write_csv(output / "structured_samples.csv", all_fields)
    (output / "blocks.json").write_text(json.dumps(block_info, indent=2) + "\n")


def networks(output, weightdir, timing=True):
    from neural import Network, configure

    configure()
    scenarios = scenario_sets()
    items = sorted(weightdir.glob("*.pt"))
    if not items:
        raise FileNotFoundError(f"no trained checkpoints in {weightdir}")
    rows, all_fields = [], []
    for path in items:
        with redirect_stdout(sys.stderr):
            net = Network(path)
        info = {
            k: net.info[k]
            for k in (
                "model",
                "case",
                "seed",
                "n",
                "parameters",
                "train_s",
                "epochs",
                "steps",
                "selected_epoch",
            )
        }
        r, f = metrics(net.predict, info, scenarios, timing=timing)
        rows.extend(r)
        all_fields.extend(f)
    write_csv(output / "neural.csv", rows)
    write_csv(output / "neural_samples.csv", all_fields)


def environment(output):
    cpu = platform.processor()
    path = Path("/proc/cpuinfo")
    if path.exists():
        cpu = next(
            (
                line.partition(":")[2].strip()
                for line in path.read_text().splitlines()
                if line.startswith("model name")
            ),
            cpu,
        )
    packages = {}
    for pkg in (
        "numpy",
        "scipy",
        "torch",
        "neuraloperator",
        "tensorly",
        "tensorly-torch",
        "matplotlib",
    ):
        try:
            packages[pkg] = version(pkg)
        except PackageNotFoundError:
            packages[pkg] = None
    record = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "cpu": cpu,
        "packages": packages,
        "thread_limits": {
            k: os.getenv(k)
            for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
        },
        "archive_commit": "72d670b51c94c8366ca5f1e070fc4730c78d0d52",
        "timing": "perf_counter; per-sample inference: 3 warmups, median of 21, 25x25, CPU",
    }
    (output / "environment.json").write_text(json.dumps(record, indent=2) + "\n")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--part", choices=("all", "structured", "neural"), default="all")
    p.add_argument("--output", type=Path, default=ROOT / "results")
    p.add_argument("--weights", type=Path, default=ROOT / "results" / "weights")
    args = p.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    if args.part != "neural":
        structured(args.output)
    if args.part != "structured":
        networks(args.output, args.weights)
    if args.part == "all":
        from paired_intervals import write_intervals

        write_intervals(args.output)
    environment(args.output)


if __name__ == "__main__":
    main()
