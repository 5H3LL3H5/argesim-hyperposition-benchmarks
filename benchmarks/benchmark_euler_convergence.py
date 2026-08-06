#!/usr/bin/env python3
"""Print finite convergence evidence for ``(1 - 1/n)**n -> exp(-1)``."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from nsa_devs import convergence_table


def main() -> None:
    step_counts = (10, 100, 1_000, 10_000, 100_000, 1_000_000)
    rows = convergence_table(step_counts)
    report = {
        "experiment": "finite_euler_approximation_to_nsa_standard_part_identity",
        "rows": [
            {
                "steps": row.steps,
                "approximation": row.approximation,
                "exact": row.exact,
                "absolute_error": row.absolute_error,
            }
            for row in rows
        ],
        "interpretation": (
            "All rows use finite n and retain finite error. The NSA statement "
            "describes the standard part at an infinite hyperinteger N."
        ),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
