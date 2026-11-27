"""Independent fine-step audit of the handoff, before subsequent coarse sampling."""

import argparse
from pathlib import Path

import numpy as np
from design import N
from evaluate import write_csv
from fields import Frozen, diagnostics
from native import Lattice
from switch import PROTOCOL, SWITCH


def window(inputs, results, lib):
    ticks = np.r_[0, np.arange(SWITCH, SWITCH + 257, 4)]
    model = Frozen(inputs, "korrektur", "hankel")
    lattice = Lattice(lib)
    table = []
    increments = []
    for re in (PROTOCOL["calibration_re"], PROTOCOL["prospective_re"]):
        fine = lattice.fields(N, re, ticks)
        coarse = lattice.fields(65, re, ticks // 4)
        kt = ticks[1:]
        correction = model.predict(kt, re, coarse[1:])
        truth = fine[1:]
        for i, t in enumerate(kt):
            m = diagnostics(correction[i], truth[i])
            table.append(
                dict(
                    re=re,
                    k=int(t),
                    **m,
                    source="unused hypothetical correction at handoff"
                    if i == 0
                    else "active correction",
                    pass_both=m["rel"] <= 0.01 and m["max_U"] <= 0.01,
                )
            )
        actual_change = correction[1] - truth[0]
        reference_change = truth[1] - truth[0]
        m = diagnostics(actual_change, reference_change)
        increments.append(
            dict(
                re=re,
                k1=int(kt[0]),
                k2=int(kt[1]),
                **m,
                truth_delta_max_U=float(
                    np.max(np.linalg.norm(reference_change[1:-1, 1:-1], axis=-1))
                ),
                forecast_delta_max_U=float(
                    np.max(np.linalg.norm(actual_change[1:-1, 1:-1], axis=-1))
                ),
            )
        )
    write_csv(results / "switch_fenster.csv", table)
    write_csv(results / "switch_viertaktschritt.csv", increments)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("inputs", "results", "lib"):
        p.add_argument(name, type=Path)
    a = p.parse_args()
    window(a.inputs, a.results, a.lib)
