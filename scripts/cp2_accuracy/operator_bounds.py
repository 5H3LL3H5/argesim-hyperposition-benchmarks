"""Outward interval bounds for fixed binary checkpoint weights, evaluated as real operators."""

from __future__ import annotations

import json
import math
from pathlib import Path

import mpmath as mp
import numpy as np

MAT = Path(__file__).resolve().parents[2] / "docs/lehrbuch/studienbuch/material"
OUT = MAT / "cp2_genauigkeit"


def main():
    iv = mp.iv
    iv.dps = 32
    with np.load(OUT / "saite.npz", allow_pickle=False) as f:
        times, kernels = f["times"], f["kernels"]
    max_err = iv.mpf(0)
    for t, row in zip(times, kernels):
        phase = iv.pi * iv.mpf("0.12") * float(t)
        for k, w in enumerate(row, 1):
            max_err = max(max_err, abs(iv.cos(k * phase) - float(w)).b)
    # Pointwise matrices and each Fourier-mode matrix are bounded in Euclidean
    # operator norm by their Frobenius norms. GELU has |G'| < 1.13.
    with np.load(
        MAT / "cp2_feldlabor/rope/rope-weights.npz", allow_pickle=False
    ) as old:

        def frob(w):
            vals = w.ravel()
            return iv.sqrt(
                sum(
                    iv.mpf(float(z.real)) ** 2 + iv.mpf(float(z.imag)) ** 2
                    for z in vals
                )
            )

        def mlp(prefix):
            return (
                frob(old[prefix + ".fcs.0.weight"])
                * iv.mpf("1.13")
                * frob(old[prefix + ".fcs.1.weight"])
            )

        g = iv.mpf("1.13")
        lip = mlp("lifting")
        for i in range(2):
            spec = old[f"fno_blocks.convs.{i}.weight.tensor"]
            spec_norm = max(frob(spec[..., j]).b for j in range(spec.shape[-1]))
            skip = frob(old[f"fno_blocks.fno_skips.{i}.conv.weight"])
            gate = float(abs(old[f"fno_blocks.channel_mlp_skips.{i}.weight"]).max())
            factors = g if i == 0 else 1
            lip *= factors * (
                mlp(f"fno_blocks.channel_mlp.{i}") * factors * (spec_norm + skip) + gate
            )
        lip *= mlp("projection")
    report = {
        "knot_error_upper": math.nextafter(float(max_err.b), math.inf),
        "old_lipschitz_upper": math.nextafter(float(lip.b), math.inf),
        "dtype_interpretation": "fixed binary coefficients, real arithmetic; discrete sine grid for the reference",
    }
    (OUT / "schranken.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
