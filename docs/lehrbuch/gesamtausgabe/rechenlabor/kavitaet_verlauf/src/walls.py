"""Report post hoc boundary and full-grid errors for the smooth hybrid."""

import argparse
from pathlib import Path

import numpy as np
from design import N
from evaluate import write_csv
from fields import Frozen, raw_field
from switch import SMOOTH, START, weight


def check(inputs, raw, results):
    times = np.loadtxt(inputs / "ticks257.txt", dtype=int)
    net = Frozen(inputs, "korrektur", "hankel")
    rows = []
    mask = np.zeros((N, N), dtype=bool)
    mask[[0, -1], :] = True
    mask[:, [0, -1]] = True
    for re in (
        SMOOTH["calibration_re"],
        SMOOTH["previous_hard_switch_test_re"],
        SMOOTH["prospective_re"],
    ):
        for i in range(0, len(times), 10):
            k = times[i : i + 10]
            need = k[k > START]
            coarse = [raw_field(raw, 65, re, int(t) // 4) for t in need]
            corr = net.predict(need, re, coarse) if len(need) else []
            it = iter(corr)
            for t in k:
                ref = raw_field(raw, N, re, int(t))
                delta = (
                    np.zeros_like(ref) if t <= START else weight(t) * (next(it) - ref)
                )
                e = np.linalg.norm(delta, axis=-1)
                ei = e[1:-1, 1:-1]
                local = float(e.max())
                bmax = float(e[mask].max())
                ix = np.where(mask, e, -1).argmax()
                y, x = np.unravel_index(ix, (N, N))
                rel = float(np.linalg.norm(delta) / np.linalg.norm(ref))
                rows.append(
                    {
                        "re": re,
                        "k": int(t),
                        "interior_max_U": float(ei.max()),
                        "boundary_max_U": bmax,
                        "boundary_x": int(x),
                        "boundary_y": int(y),
                        "full_max_U": local,
                        "full_rel": rel,
                        "full_pass": (local <= 0.01 and rel <= 0.01),
                    }
                )
    write_csv(results / "smooth_alle_knoten.csv", rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    for n in ("inputs", "raw", "results"):
        p.add_argument(n, type=Path)
    a = p.parse_args()
    check(a.inputs, a.raw, a.results)
