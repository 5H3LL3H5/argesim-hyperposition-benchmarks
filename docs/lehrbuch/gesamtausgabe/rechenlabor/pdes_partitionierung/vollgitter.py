"""Reproduce the 257 x 257 CP2 comparison using the published cavity and C++ solvers."""
from __future__ import annotations

import argparse
from contextlib import nullcontext
import csv
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import zipfile
from pathlib import Path

import numpy as np
from scipy.integrate import DOP853

N = 257
RE = 1000
DT = 0.1 / (N - 1)
CHECKS = (256, 4096, 16384, 65536, 131072, 262144, 350000)
END = CHECKS[-1]
RTOL = 1e-7
ATOL = 1e-10
PREFIX = "rechenlabor/kavitaet_vollgitter/"
NATIVE = {
    "lbm1": ("d2q9", ["1"]),
    "lbm4": ("d2q9", ["4"]),
    "ab2-s2": ("wirbel", ["2"]),
    "ab2-s4": ("wirbel", ["4"]),
    "gqss1": ("gruppen_qss", ["1", "0.001"]),
    "gqss2": ("gruppen_qss", ["2", "0.001"]),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_cavity(work):
    path = work / "basis" / "kavitaet.py"
    spec = importlib.util.spec_from_file_location("cp2_cavity", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Cavity(N, RE)


def prepare(repo, work):
    work.mkdir(parents=True, exist_ok=True)
    archive = repo / "docs/lehrbuch/gesamtausgabe/pakete/Laborquellen.zip"
    source = zipfile.ZipFile(archive) if archive.is_file() else nullcontext()
    with source as package:
        root = zipfile.Path(package, at=PREFIX) if package is not None else repo / PREFIX
        for member in ("basis/kavitaet.py", "src/zeitpunkte.txt",
                       "src/d2q9.cpp", "src/wirbel.cpp", "src/gruppen_qss.cpp"):
            path = work / member
            path.parent.mkdir(exist_ok=True)
            path.write_bytes((root / member).read_bytes())
    marks = np.loadtxt(work / "src/zeitpunkte.txt", dtype=int)
    if not set(CHECKS).issubset(marks) or len(marks) != 37 or marks[-1] != END:
        raise ValueError("Unexpected book observation times")
    flags = ["-std=c++20", "-O3", "-march=native", "-ffp-contract=off", "-Wall", "-Wextra", "-Werror"]
    for program in ("d2q9", "wirbel", "gruppen_qss"):
        link = ["-fopenmp"] if program == "d2q9" else ["-Wl,-l:libfftw3.so.3"]
        subprocess.run(["g++", *flags, str(work / "src" / (program + ".cpp")), *link,
                        "-o", str(work / program)], check=True)
    info = {
        "grid": [N, N], "reynolds": RE, "end_tick": END, "end_t_star": END * DT,
        "reference_ticks": CHECKS, "all_ticks": marks.tolist(), "archive_sha256": digest(archive) if archive.is_file() else None,
        "kernel_sha256": {p.name: digest(p) for p in sorted((work / "src").glob("*.cpp"))},
        "python": platform.python_version(), "numpy": np.__version__,
        "scipy": importlib.metadata.version("scipy"), "kernel": platform.release(),
        "cpu": next((s.split(":", 1)[1].strip() for s in Path("/proc/cpuinfo").read_text().splitlines()
                     if s.startswith("model name")), "unknown"),
        "compiler": subprocess.check_output(["g++", "-dumpfullversion"], text=True).strip(),
        "flags": flags, "dop853_rtol": RTOL, "dop853_atol": ATOL,
    }
    (work / "platform.json").write_text(json.dumps(info, indent=2) + "\n")


def pin(cpus):
    available = os.sched_getaffinity(0)
    want = set(cpus)
    if not want or len(cpus) != len(want) or not want.issubset(available):
        raise ValueError(f"CPUs {cpus} are unavailable; available: {sorted(available)}")
    os.sched_setaffinity(0, want)


def native(work, method, cpus):
    program, options = NATIVE[method]
    expected = 4 if method == "lbm4" else 1
    if len(cpus) != expected:
        raise ValueError(f"{method} needs exactly {expected} CPUs")
    pin(cpus)
    directory = work / method
    directory.mkdir(exist_ok=True)
    args = [str(work / program), str(N), str(RE), *options,
            str(directory), str(work / "src/zeitpunkte.txt")]
    env = dict(os.environ, OMP_NUM_THREADS=str(expected), OMP_DYNAMIC="FALSE",
               OMP_PROC_BIND="TRUE", OMP_PLACES=",".join("{%d}" % cpu for cpu in cpus))
    start = time.perf_counter()
    subprocess.run(args, env=env, check=True)
    save_run(directory, cpus, time.perf_counter() - start)


def save_run(directory, cpus, whole):
    (directory / "run.json").write_text(json.dumps({"cpus": cpus, "total_s": whole}) + "\n")


def dop853(work, cpus):
    if len(cpus) != 1:
        raise ValueError("DOP853 is single-threaded in this comparison")
    pin(cpus)
    model = read_cavity(work)
    directory = work / "dop853"
    directory.mkdir(exist_ok=True)
    marks = np.loadtxt(work / "src/zeitpunkte.txt", dtype=int)
    target_index = 0
    steps = 0
    total_start = time.perf_counter()
    cpu_start = time.process_time()
    io_wall = io_cpu = 0.0
    solver = DOP853(model.rhs, 0.0, np.zeros(model.dim), END * DT, rtol=RTOL, atol=ATOL)
    with (directory / "zeiten.csv").open("w", newline="") as stream:
        log = csv.writer(stream)
        log.writerow(["step", "t_star", "wall_s", "cpu_s", "accepted_steps", "rhs_calls"])
        while solver.status == "running":
            message = solver.step()
            if solver.status == "failed":
                raise RuntimeError(message)
            steps += 1
            interpolant = None
            while target_index < len(marks) and marks[target_index] * DT <= solver.t:
                tick = int(marks[target_index])
                target = tick * DT
                if target == solver.t:
                    state = solver.y
                else:
                    if interpolant is None:
                        interpolant = solver.dense_output()
                    state = interpolant(target)
                stamp = time.perf_counter()
                cpu_stamp = time.process_time()
                if not np.isfinite(state).all():
                    raise ValueError(f"Non-finite DOP853 state at {target}")
                np.asarray(state, dtype="<f8").tofile(directory / f"z_{tick}.bin")
                log.writerow([tick, target, stamp - total_start - io_wall,
                              cpu_stamp - cpu_start - io_cpu, steps, solver.nfev])
                stream.flush()
                io_wall += time.perf_counter() - stamp
                io_cpu += time.process_time() - cpu_stamp
                target_index += 1
    if target_index != len(marks):
        raise ValueError("DOP853 missed an observation")
    save_run(directory, cpus, time.perf_counter() - total_start)


def velocity(work, name, tick, model):
    folder = work / name
    if name.startswith("lbm"):
        raw = np.fromfile(folder / f"feld_{tick}.bin", dtype="<f8").reshape(3, N, N)
        return raw[1:, 1:-1, 1:-1].transpose(1, 2, 0)
    return model.field(np.fromfile(folder / f"z_{tick}.bin", dtype="<f8"))[1:-1, 1:-1]


def difference(values, ref):
    delta = values - ref
    return {"relative_l2": float(np.linalg.norm(delta) / np.linalg.norm(ref)),
            "max_vector_U": float(np.linalg.norm(delta, axis=-1).max())}


def summarize(work, output):
    model = read_cavity(work)
    info = json.loads((work / "platform.json").read_text())
    runs = {}
    for name in [*NATIVE, "dop853"]:
        directory = work / name
        with (directory / "zeiten.csv").open() as f:
            history = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]
        if [r["step"] for r in history] != info["all_ticks"] or history[-1]["t_star"] != END * DT:
            raise ValueError(f"Incomplete {name} trajectory")
        prefix = "feld" if name.startswith("lbm") else "z"
        hashes = {tick: digest(directory / f"{prefix}_{tick}.bin") for tick in info["all_ticks"]}
        runs[name] = {**json.loads((directory / "run.json").read_text()), "history": history,
                      "field_sha256": hashes, "comparisons": []}
    if runs["lbm1"]["field_sha256"] != runs["lbm4"]["field_sha256"]:
        raise ValueError("OpenMP and single-thread macroscopic fields differ")
    for tick in CHECKS:
        fields = {name: velocity(work, name, tick, model) for name in runs}
        for name, v in fields.items():
            runs[name]["comparisons"].append(
                {"step": tick, "vs_lbm": difference(v, fields["lbm1"]),
                 "vs_ab2_s2": difference(v, fields["ab2-s2"]),
                 "vs_dop853": difference(v, fields["dop853"])}
            )
    with zipfile.ZipFile(output.with_name("DOP853_Prueffelder.zip"), "w") as archive:
        for tick in CHECKS:
            name = f"z_{tick}.bin"
            entry = zipfile.ZipInfo(name, (2026, 11, 26, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(entry, (work / "dop853" / name).read_bytes())
    output.write_text(json.dumps({"setup": info, "runs": runs}, indent=2, allow_nan=False) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "evaluate", "dop853", *NATIVE])
    parser.add_argument("work", type=Path)
    parser.add_argument("--repo", type=Path, default=Path("."),
                        help="Root of the repository or the unpacked complete lab")
    parser.add_argument("--cpus", nargs="+", type=int)
    parser.add_argument("--output", type=Path, default=Path("vollgitter.json"))
    args = parser.parse_args()
    work = args.work.resolve()
    repo = args.repo.resolve()
    offline_sources = repo / PREFIX / "basis/original"
    sys.path.insert(0, str(offline_sources if offline_sources.is_dir() else repo))
    if args.action == "prepare":
        prepare(repo, work)
    elif args.action == "evaluate":
        summarize(work, args.output)
    elif args.action == "dop853":
        dop853(work, args.cpus or [min(os.sched_getaffinity(0))])
    else:
        amount = 4 if args.action == "lbm4" else 1
        native(work, args.action, args.cpus or sorted(os.sched_getaffinity(0))[:amount])


if __name__ == "__main__":
    main()
