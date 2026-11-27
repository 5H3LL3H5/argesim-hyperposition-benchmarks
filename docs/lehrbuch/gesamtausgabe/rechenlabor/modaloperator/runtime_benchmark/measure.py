"""Measure complete jobs, warm sequential service and reference accuracy on one CPU thread."""

import argparse
import csv
import json
import math
import os
import platform
import subprocess
import sys
import tempfile
from pathlib import Path
from time import perf_counter, perf_counter_ns

import numpy as np
from physics import NOMINAL, draw, family, samples, score

from . import cp2_reference
from .native_lbm import FLAGS, Native, build, diffusion_steps
from .worker import ROOT, cavity_densities

JOBS = {
    "diffusion": [
        "D2Q5",
        "FNO-small",
        "UNO",
        "CoDA-NO",
        "Modal24",
        "Generator3",
        "Strang",
        "Strang-R24",
        "Strang-FNO",
    ],
    "family": ["D2Q5", "FNO-cond", "Strang", "Strang-FNO-cond"],
    "cavity": ["D2Q9", "D2Q9-NumPy", "Cavity-FNO"],
}


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as stream:
        w = csv.DictWriter(stream, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)


def fixtures(work):
    refs = {}
    for name, params in [("diffusion", (NOMINAL,) * 32), ("family", family(32, 52203))]:
        x, y = samples(draw(32, 42203), 25, params=params)
        values = [[p.du, p.dv, p.rate, p.time] for p in params]
        np.savez(work / f"inputs_{name}.npz", x=x, params=values)
        refs[name] = y
    _, x = cavity_densities(24, 2)
    np.savez(work / "inputs_cavity.npz", x=x)
    refs["cavity"] = cp2_reference.cavity_snapshots(x, 0.1, [16])[16]
    return refs


def errors(problem, y, t):
    if problem == "cavity":
        yt = t[..., 1:-1, 1:-1].astype(np.float64)
        yp = y[..., 1:-1, 1:-1].astype(np.float64)
        def norm(field):
            return np.linalg.norm(field.reshape(len(field), -1), axis=1)

        vector = float(np.mean(norm(yp - yt) / norm(yt)))
        return vector
    values = score(y, t)
    return (values["u"] + values["v"]) / 2


def run(work, out):
    env = {
        **os.environ,
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
    }
    started = perf_counter()
    tbuild = build(work / "lbm.so")
    refs = fixtures(work)
    raw = {}
    rows = []
    for problem, models in JOBS.items():
        for model in models:
            record = {}
            for mode in ("fresh", "ready", "warm"):
                key = f"{problem}_{model}_{mode}"
                start_ns = perf_counter_ns()
                with (work / (key + ".log")).open("w") as stream:
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "runtime_benchmark.worker",
                            problem,
                            model,
                            mode,
                            str(work),
                        ],
                        cwd=ROOT,
                        env=env,
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                        check=True,
                    )
                elapsed = (perf_counter_ns() - start_ns) * 1e-9
                d = json.loads((work / (key + ".json")).read_text())
                if mode != "warm":
                    d["before_inference_s"] = (
                        d.pop("service_start_ns") - start_ns
                    ) * 1e-9
                    d["first_end_to_end_s"] = (d.pop("first_ns") - start_ns) * 1e-9
                    d["last_in_memory_s"] = (d.pop("last_ns") - start_ns) * 1e-9
                    d["end_to_exit_s"] = elapsed
                    result = np.load(work / (key + ".npy"))
                    d["field_error"] = errors(problem, result, refs[problem])
                record[mode] = d
            raw[f"{problem}/{model}"] = record
            f, r, w = (record[k] for k in ("fresh", "ready", "warm"))
            rows.append(
                {
                    "problem": problem,
                    "model": model,
                    "n": r["count"],
                    "fresh1_s": f["first_end_to_end_s"],
                    "freshN_s": f["end_to_exit_s"],
                    "ready1_s": r["first_end_to_end_s"],
                    "readyN_s": r["end_to_exit_s"],
                    "warmN_s": w["block_median_s"],
                    "warm_ms_each": 1e3 * w["block_median_s"] / r["count"],
                    "fresh_prepare_s": f["setup_s"],
                    "fresh_fixed_s": f["before_inference_s"],
                    "error_ready": r["field_error"],
                    "error_fresh": f["field_error"],
                }
            )
            print(
                problem,
                model,
                round(f["end_to_exit_s"], 4),
                round(w["block_median_s"], 5),
                round(100 * r["field_error"], 6),
                flush=True,
            )
            write_csv(out / "total_jobs.csv", rows)
    checks = numerical_checks(work)
    write_csv(out / "lbm_refinement.csv", checks)
    break_rows = []
    for row in rows:
        base = next(
            q
            for q in rows
            if q["problem"] == row["problem"] and q["model"] in ("D2Q5", "D2Q9")
        )
        gain = (base["warm_ms_each"] - row["warm_ms_each"]) * 1e-3
        # Measured from process launch up to the first forward call. Excludes final file output.
        extra = row["fresh_fixed_s"] - base["fresh_fixed_s"]
        n = max(1, math.floor(extra / gain) + 1) if gain > 0 else None
        break_rows.append(
            {
                "problem": row["problem"],
                "candidate": row["model"],
                "extra_prepare_s": extra,
                "saving_per_field_s": gain,
                "strict_crossover_n": n,
            }
        )
    write_csv(out / "break_even.csv", break_rows)
    report = {
        "environment": {
            "python": platform.python_version(),
            "cpu": next(
                (
                    line.split(":", 1)[1].strip()
                    for line in Path("/proc/cpuinfo").read_text().splitlines()
                    if line.startswith("model name")
                ),
                "unknown",
            ),
            "flags": FLAGS,
            "compiler": subprocess.check_output(
                ["c++", "--version"], text=True
            ).splitlines()[0],
            "thread_limits": {
                k: env[k]
                for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS")
            },
        },
        "build_s": tbuild,
        "comparison_wall_s": perf_counter() - started,
        "jobs": raw,
        "description": "one cold fresh and one cold ready process per model, two warm-up blocks and nine measured blocks; one request at a time",
    }
    (out / "timings.json").write_text(
        json.dumps(report, indent=2, allow_nan=False) + "\n"
    )


def numerical_checks(work):
    native = Native(work / "lbm.so")
    coeff = draw(8, 42203)
    out = []
    for n in (13, 25, 49, 97):
        x, y = samples(coeff, n)
        pred = np.concatenate([native.diffusion(a[None], NOMINAL) for a in x])
        s = score(pred, y)
        out.append(
            {
                "n": n,
                "steps": diffusion_steps(n, NOMINAL),
                "u": s["u"],
                "v": s["v"],
                "boundary_max": s["boundary"],
            }
        )
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, default=ROOT / "results" / "runtime")
    p.add_argument(
        "--work",
        type=Path,
        help="retain inputs, native binary, fields, weights and worker logs",
    )
    args = p.parse_args()
    out = args.out.resolve()
    out.mkdir(exist_ok=True, parents=True)
    if args.work is not None:
        work = args.work.resolve()
        work.mkdir(exist_ok=True, parents=True)
        run(work, out)
    else:
        with tempfile.TemporaryDirectory() as tmp:
            run(Path(tmp), out)


if __name__ == "__main__":
    main()
