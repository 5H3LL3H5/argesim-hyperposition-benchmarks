"""Prospective confirmation timing on one CPU, bracketing fine D2Q9 by smooth runs."""

import argparse
import json
import os
import time
from pathlib import Path

import numpy as np
from native import Lattice
from switch import SMOOTH, Smoothed


def paired(inputs, raw, results, lib, cpu):
    from fields import raw_field

    if cpu is not None:
        os.sched_setaffinity(0, {cpu})
    ticks = np.r_[0, np.loadtxt(inputs / "ticks257.txt", dtype=int)]
    re = SMOOTH["prospective_re"]
    lattice = Lattice(lib)
    smooth = Smoothed(inputs, lib)
    smooth.predict(ticks[:3], re)
    lattice.fields(257, re, ticks[:3])
    rows = []
    for tag in ("smooth", "D2Q9", "smooth"):
        start = time.perf_counter()
        proc = time.process_time()
        field = (
            smooth.predict(ticks, re)
            if tag == "smooth"
            else lattice.fields(257, re, ticks)
        )
        elapsed = time.perf_counter() - start
        cpu_s = time.process_time() - proc
        end_error = float(
            np.max(np.abs(field[-1] - raw_field(raw, 257, re, int(ticks[-1]))))
        )
        del field
        if not np.isfinite(end_error) or (tag == "D2Q9" and end_error > 1e-10):
            raise ArithmeticError("invalid paired output")
        rows.append(
            {
                "method": tag,
                "wall_s": elapsed,
                "cpu_s": cpu_s,
                "max_abs_component_end_delta": end_error,
            }
        )
        print(tag, elapsed, flush=True)
    receipt = {
        "re": re,
        "affinity": sorted(os.sched_getaffinity(0)),
        "outputs": len(ticks),
        "rows": rows,
        "speedup": rows[1]["wall_s"] / np.mean([rows[0]["wall_s"], rows[2]["wall_s"]]),
    }
    (results / "paired_1025.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for n in ("inputs", "raw", "results", "lib"):
        p.add_argument(n, type=Path)
    p.add_argument("--cpu", type=int)
    a = p.parse_args()
    paired(a.inputs, a.raw, a.results, a.lib, a.cpu)
