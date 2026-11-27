"""Run the small checks by default; --full recomputes every numerical table."""

import argparse
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

from src.eingaben import prepare

ROOT = Path(__file__).resolve().parent
ENV = {
    **os.environ,
    **{
        key: "1"
        for key in (
            "OPENBLAS_NUM_THREADS",
            "MKL_NUM_THREADS",
            "OMP_NUM_THREADS",
            "NUMEXPR_NUM_THREADS",
        )
    },
}


def run(name, *args, limit):
    subprocess.run(
        [sys.executable, str(ROOT / "src" / name), *map(str, args)],
        check=True,
        env=ENV,
        timeout=limit,
    )


def full(inp, raw, target, cpu):
    target.mkdir(parents=True, exist_ok=True)
    raw.mkdir(parents=True, exist_ok=True)
    build = raw / "build"
    run("native.py", inp, build, limit=60)
    affinity = ["--cpu", cpu] if cpu is not None else []
    for re in (1000, 950, 1050, 975, 1025):
        sizes = (257,) if re in (950, 1050) else (65, 257)
        for n in sizes:
            limit = 480 if n == 257 else 120
            run(
                "simulate.py",
                build / "d2q9",
                inp,
                raw,
                target,
                n,
                re,
                *affinity,
                "--limit",
                limit,
                limit=limit + 15,
            )
    run("check_reference.py", inp, raw, target, limit=60)
    run("stepper.py", inp, raw, target / "stepper.npz", limit=120)
    run("evaluate.py", inp, raw, target, limit=300)
    so = build / "cp2.so"
    run("audit_switch.py", inp, raw, target, so, limit=240)
    run("switch_window.py", inp, target, so, limit=180)
    run("audit_smooth.py", inp, raw, target, so, limit=480)
    run("walls.py", inp, raw, target, limit=120)
    for re in (1000, 975, 1025):
        pairs = [("D2Q9", 2), ("smooth", 3)]
        if re != 1025:
            pairs.append(("switch", 3))
        if re == 1000:
            pairs.extend(
                [("direkt:fourier", 5), ("korrektur:hankel", 5), ("rollout", 5)]
            )
        for method, repeats in pairs:
            run(
                "benchmark.py",
                inp,
                raw,
                target,
                so,
                method,
                *affinity,
                "--re",
                re,
                "--repeats",
                repeats,
                limit=480,
            )

    run("paired.py", inp, raw, target, so, *affinity, limit=480)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--full", action="store_true")
    parser.add_argument(
        "--raw",
        type=Path,
        help="new or empty folder, about 3 GB during full simulation",
    )
    parser.add_argument(
        "--results",
        type=Path,
        help="new output folder, separate from packaged evidence",
    )
    parser.add_argument(
        "--cpu", type=int, help="one permitted logical CPU on Linux; optional"
    )
    parser.add_argument("--input-archive", type=Path, help="complete offline lab ZIP, optional")
    a = parser.parse_args()
    if a.cpu is not None:
        os.sched_setaffinity(0, {a.cpu})
    if a.full:
        if a.raw is None or a.results is None:
            parser.error("--full needs --raw and --results")
        if any(p.exists() and any(p.iterdir()) for p in (a.raw, a.results)):
            parser.error("use empty work folders to preserve previous results")
        raw, results = a.raw.resolve(), a.results.resolve()
        if raw == results or raw.is_relative_to(results) or results.is_relative_to(raw):
            parser.error("--raw and --results must be separate directories")
    with TemporaryDirectory(prefix="cp2-verlauf-") as temp:
        inputs = Path(temp)
        prepare(inputs, a.input_archive)
        if a.full:
            full(inputs, raw, results, a.cpu)
        else:
            ENV["CP2_VERLAUF_INPUTS"] = str(inputs)
            run("test_trajectory.py", limit=60)
