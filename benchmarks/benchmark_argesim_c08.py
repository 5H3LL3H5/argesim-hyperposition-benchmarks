#!/usr/bin/env python3
"""Run the complete ARGESIM C08 Task-C statistical protocol."""

from __future__ import annotations

import argparse
import json

from argesim_benchmarks.models.c08_canal_and_lock import c08_task_c


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--duration", type=float, default=14400.0)
    parser.add_argument("--independent-replications", type=int, default=100)
    parser.add_argument("--paired-replications", type=int, default=50)
    parser.add_argument("--starting-seeds", type=int, nargs="+", default=[42, 314159, 271828])
    args = parser.parse_args()

    result = c08_task_c(
        duration=args.duration,
        independent_replications=args.independent_replications,
        paired_replications=args.paired_replications,
        starting_seeds=tuple(args.starting_seeds),
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
