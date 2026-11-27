"""Three Reynolds numbers and two dense, four-tick handoff windows."""

import argparse
from pathlib import Path

import numpy as np
from design import ORIGINAL, N
from evaluate import summary, write_csv
from fields import diagnostics, raw_field
from native import Lattice
from switch import SMOOTH, START, STOP, Smoothed, weight


def audit(inputs, raw, results, lib):
    positive = np.loadtxt(inputs / "ticks257.txt", dtype=int)
    ticks = np.r_[0, positive]
    old = set(np.loadtxt(inputs / "src/zeitpunkte.txt", dtype=int))
    net = Smoothed(inputs, lib)
    lattice = Lattice(lib)
    # At entry include the first 64 increments after the boundary. At exit straddle both sides.
    sets = {
        "entry": np.arange(START, START + 257, 4),
        "exit": np.arange(STOP - 128, STOP + 129, 4),
    }
    local_ticks = np.r_[0, sets["entry"], sets["exit"]]
    all_rows = []
    condensed = []
    local_rows = []
    for re in (
        SMOOTH["calibration_re"],
        SMOOTH["previous_hard_switch_test_re"],
        SMOOTH["prospective_re"],
    ):
        predicted = net.predict(ticks, re)
        rows = []
        for tick, guess in zip(ticks, predicted, strict=True):
            k = int(tick)
            truth = raw_field(raw, N, re, k)
            m = diagnostics(guess, truth)
            rows.append(
                dict(
                    method=f"smooth_{re}",
                    re=re,
                    k=k,
                    t_star=k * 0.1 / 256,
                    book7=k in ORIGINAL,
                    new_time=k > 0 and k not in old,
                    **m,
                    pass_both=(m["rel"] <= 0.01 and m["max_U"] <= 0.01) if k else None,
                )
            )
        condensed.append(summary(rows))
        all_rows.extend(rows)
        del predicted, guess
        fine = lattice.fields(N, re, local_ticks)
        coarse = lattice.fields(65, re, local_ticks // 4)
        base = 1
        for side, kt in sets.items():
            last = base + len(kt)
            actual = fine[base:last]
            corr = net.coarse_net.predict(kt, re, coarse[base:last])
            base = last
            w = weight(kt)[:, None, None, None]
            smooth = actual + w * (corr - actual)
            hard = np.where((kt > START)[:, None, None, None], corr, actual)
            for method, fields in [("smooth", smooth), ("hard", hard)]:
                for i in range(1, len(kt)):
                    ref_inc = actual[i] - actual[i - 1]
                    pred_inc = fields[i] - fields[i - 1]
                    m = diagnostics(fields[i], actual[i])
                    d = diagnostics(pred_inc, ref_inc)
                    local_rows.append(
                        {
                            "re": re,
                            "side": side,
                            "method": method,
                            "k": int(kt[i]),
                            "rel": m["rel"],
                            "max_U": m["max_U"],
                            "pass_both": m["rel"] <= 0.01 and m["max_U"] <= 0.01,
                            "delta_rel": d["rel"],
                            "delta_max_U": d["max_U"],
                            "ref_delta_max_U": float(
                                np.max(np.linalg.norm(ref_inc[1:-1, 1:-1], axis=-1))
                            ),
                            "pred_delta_max_U": float(
                                np.max(np.linalg.norm(pred_inc[1:-1, 1:-1], axis=-1))
                            ),
                        }
                    )
        print(
            re,
            condensed[-1]["n_pass"],
            condensed[-1]["worst_rel"],
            condensed[-1]["worst_max_U"],
            flush=True,
        )
    write_csv(results / "smooth_verlauf.csv", all_rows)
    write_csv(results / "smooth_vergleich.csv", condensed)
    write_csv(results / "smooth_fenster.csv", local_rows)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "raw", "results", "lib"):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    audit(a.inputs, a.raw, a.results, a.lib)
