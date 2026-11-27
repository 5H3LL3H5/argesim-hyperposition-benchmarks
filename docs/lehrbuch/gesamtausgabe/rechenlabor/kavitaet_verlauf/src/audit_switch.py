"""Evaluate the fixed switching rule and the first late increment against D2Q9."""

import argparse
import json
from pathlib import Path

import numpy as np
from design import ORIGINAL, N
from evaluate import summary, write_csv
from fields import diagnostics, raw_field
from switch import PROTOCOL, SWITCH, Switched


def audit(inputs, raw, results, lib):
    k = np.r_[0, np.loadtxt(inputs / "ticks257.txt", dtype=int)]
    old = set(np.loadtxt(inputs / "src/zeitpunkte.txt", dtype=int))
    net = Switched(inputs, lib)
    totals = []
    data = []
    increments = {}
    for re in (PROTOCOL["calibration_re"], PROTOCOL["prospective_re"]):
        uv = net.predict(k, re)
        rows = []
        prev_ref = prev_field = None
        first_after = int(k[np.searchsorted(k, SWITCH, side="right")])
        for t, field in zip(k, uv, strict=True):
            tick = int(t)
            ref = raw_field(raw, N, re, tick)
            m = diagnostics(field, ref)
            row = dict(
                method=f"switch_{re}",
                re=re,
                k=tick,
                t_star=tick * 0.1 / 256,
                book7=tick in ORIGINAL,
                new_time=tick > 0 and tick not in old,
                **m,
                pass_both=(m["rel"] <= 0.01 and m["max_U"] <= 0.01) if tick else None,
            )
            rows.append(row)
            if tick == first_after:
                increments[re] = {
                    "last_fine_k": SWITCH,
                    "first_hybrid_k": tick,
                    **diagnostics(field - prev_field, ref - prev_ref),
                }
            prev_field, prev_ref = field, ref
        totals.append(summary(rows))
        data.extend(rows)
        del uv, field, prev_field
    write_csv(results / "switch_verlauf.csv", data)
    write_csv(results / "switch_vergleich.csv", totals)
    (results / "switch_uebergang.json").write_text(
        json.dumps(increments, indent=2) + "\n"
    )
    for t in totals:
        print(t["method"], t["n_pass"], t["worst_rel"], t["worst_max_U"], flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for x in ("inputs", "raw", "results", "lib"):
        p.add_argument(x, type=Path)
    a = p.parse_args()
    audit(a.inputs, a.raw, a.results, a.lib)
