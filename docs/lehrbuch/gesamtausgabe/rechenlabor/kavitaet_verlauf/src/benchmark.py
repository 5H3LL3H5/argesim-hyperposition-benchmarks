"""One common output contract in RAM. Run bounds are supplied by the caller."""

import argparse
import json
import os
import platform
import time
from pathlib import Path

import numpy as np
from design import RE, N
from fields import Frozen, raw_field
from native import Lattice
from stepper import Stepper


def chunks(size, block=12):
    return (slice(i, min(i + block, size)) for i in range(0, size, block))


def run_case(name, inputs, raw, results, lib, cpu, repeats, re=RE):
    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
    k = np.r_[0, np.loadtxt(inputs / "ticks257.txt", dtype=int)]
    lattice = Lattice(lib)
    if name == "D2Q9":

        def predict(steps):
            return lattice.fields(N, re, steps)
    elif name in ("switch", "smooth"):
        from switch import Smoothed, Switched

        switched = (Switched if name == "switch" else Smoothed)(inputs, lib)

        def predict(steps):
            return switched.predict(steps, re)
    elif name == "rollout":
        net = Stepper(inputs, results / "stepper.npz")

        def predict(steps):
            z = net.rollout(steps, re)
            output = np.empty((len(steps), N, N, 2))
            for sl in chunks(len(steps)):
                output[sl] = net.fields(z[sl])
            return output
    else:
        group, kind = name.split(":")
        frozen = Frozen(inputs, group, kind)

        def predict(steps):
            coarse = (
                lattice.fields(65, re, steps // 4) if group == "korrektur" else None
            )
            output = np.empty((len(steps), N, N, 2))
            for sl in chunks(len(steps)):
                output[sl] = frozen.predict(
                    steps[sl], re, None if coarse is None else coarse[sl]
                )
            return output

    # Touch models and load native library outside the warm online clock.
    probe = predict(k[:3])
    del probe
    wall, cpu_s = [], []
    for _ in range(repeats):
        a = time.perf_counter()
        b = time.process_time()
        field = predict(k)
        cpu_s.append(time.process_time() - b)
        wall.append(time.perf_counter() - a)
        if (
            field.shape != (len(k), N, N, 2)
            or field.dtype != np.float64
            or not np.isfinite(field).all()
        ):
            raise ArithmeticError("invalid output fields")
        if name == "D2Q9":
            diff = max(
                np.max(np.abs(actual - raw_field(raw, N, re, int(tick))))
                for tick, actual in zip(k, field, strict=True)
            )
            if diff > 1e-10:
                raise ArithmeticError(f"RAM driver vs. saved trajectory: {diff:g}")
        del field
    row = {
        "name": name,
        "re": re,
        "wall_s": wall,
        "cpu_s": cpu_s,
        "median_wall_s": float(np.median(wall)),
        "median_cpu_s": float(np.median(cpu_s)),
        "outputs": len(k),
        "bytes": len(k) * N * N * 2 * 8,
        "threads": 1,
        "affinity": sorted(os.sched_getaffinity(0)),
        "python": platform.python_version(),
        "numpy": np.__version__,
    }
    if name == "D2Q9":
        row["max_reference_delta_all_outputs"] = diff
    (
        results
        / (
            "timing_"
            + name.replace(":", "_")
            + (f"_re{re}" if re != RE else "")
            + ".json"
        )
    ).write_text(json.dumps(row, indent=2) + "\n")
    print(name, wall, flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for x in ("inputs", "raw", "results", "lib"):
        p.add_argument(x, type=Path)
    p.add_argument(
        "name",
        choices=(
            "D2Q9",
            "direkt:fourier",
            "korrektur:hankel",
            "rollout",
            "switch",
            "smooth",
        ),
    )
    p.add_argument("--cpu", type=int)
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--re", type=int, default=RE)
    a = p.parse_args()
    run_case(a.name, a.inputs, a.raw, a.results, a.lib, a.cpu, a.repeats, a.re)
