"""Run one frozen D2Q9 executable with a wall timeout and keep both clocks."""

import argparse
import csv
import json
import os
import platform
import resource
import subprocess
import time
from pathlib import Path


def simulate(exe, inputs, raw, results, n, re, cpu, limit):
    tag = f"n{n}_re{re}"
    output = raw / tag
    args = [
        str(exe.resolve()),
        str(n),
        str(re),
        "1",
        str(output),
        str(inputs / f"ticks{n}.txt"),
    ]
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
    results.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    before = resource.getrusage(resource.RUSAGE_CHILDREN)
    subprocess.run(args, check=True, timeout=limit)
    elapsed = time.perf_counter() - start
    after = resource.getrusage(resource.RUSAGE_CHILDREN)
    with (output / "zeiten.csv").open() as file:
        times = list(csv.DictReader(file))
    model = next(
        (
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ),
        "unknown",
    )
    clock = {
        "n": n,
        "re": re,
        "outputs": len(times),
        "last_step": int(times[-1]["step"]),
        "threads": 1,
        "cpu_model": model,
        "affinity": sorted(os.sched_getaffinity(0)),
        "platform": platform.platform(),
        "wall_limit_s": limit,
        "process_wall_s": elapsed,
        "process_cpu_s": after.ru_utime
        - before.ru_utime
        + after.ru_stime
        - before.ru_stime,
        "kernel_wall_s": float(times[-1]["wall_s"]),
        "kernel_cpu_s": float(times[-1]["cpu_s"]),
    }
    (results / (tag + ".json")).write_text(json.dumps(clock, indent=2) + "\n")
    (results / (tag + ".csv")).write_bytes((output / "zeiten.csv").read_bytes())
    print(tag, f"{elapsed:.3f} s wall", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exe", "inputs", "raw", "results"):
        parser.add_argument(name, type=Path)
    parser.add_argument("n", type=int, choices=(65, 257))
    parser.add_argument("re", type=int)
    parser.add_argument("--cpu", type=int)
    parser.add_argument("--limit", type=int, default=480)
    a = parser.parse_args()
    simulate(a.exe, a.inputs, a.raw, a.results, a.n, a.re, a.cpu, a.limit)
