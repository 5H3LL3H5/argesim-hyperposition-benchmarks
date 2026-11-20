#!/usr/bin/env python3
"""Optional NumPy/LAPACK cross-check of C18's dependency-free ARX estimator.

The input is synthetic with a known recurrence. It verifies the estimator and
regularization, not the missing original muscle-measurement experiment.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np

from argesim_benchmarks.models.c18_nonlinear_identification import (
    C18DataSet,
    fit_c18_linear,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rng = random.Random(18)
    signal = np.array([rng.uniform(-1, 1) for _ in range(500)])
    force = np.zeros_like(signal)
    for i in range(2, len(signal)):
        force[i] = (
            1.2 * force[i - 1]
            - 0.35 * force[i - 2]
            + 0.4 * signal[i]
            - 0.1 * signal[i - 1]
            + rng.gauss(0.0, 0.01)
        )
    checks = []
    for scale in (1e-12, 1.0, 1e12):
        x, y = scale * signal, scale * force
        matrix = np.column_stack((y[1:-1], y[:-2], x[2:], x[1:-1]))
        for ridge in (0.0, 1e-10):
            augmented = np.vstack((matrix, np.sqrt(ridge) * np.eye(4)))
            target = np.concatenate((y[2:], np.zeros(4)))
            reference, _, rank, _ = np.linalg.lstsq(augmented, target, rcond=None)
            actual = np.array(
                fit_c18_linear(C18DataSet(x, y), ridge=ridge).coefficients
            )
            error = float(np.max(np.abs(actual - reference)))
            passed = bool(rank == 4 and error <= 1e-10)
            checks.append(
                {
                    "signal_scale": scale,
                    "ridge": ridge,
                    "actual": actual.tolist(),
                    "lapack_reference": reference.tolist(),
                    "maximum_absolute_error": error,
                    "tolerance": 1e-10,
                    "passed": passed,
                }
            )
    report = {
        "benchmark": "C18",
        "scope": "synthetic ARX numerical verification",
        "original_measurement_validation": False,
        "numpy": np.__version__,
        "source_sha256": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in (
                ROOT / "argesim_benchmarks/models/c18_nonlinear_identification.py",
                Path(__file__),
            )
        },
        "checks": checks,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n")
    print(f"{sum(check['passed'] for check in checks)}/{len(checks)} checks passed")
    if not all(check["passed"] for check in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
