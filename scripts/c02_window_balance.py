"""Audit closed-population accounting from C02 load/unload events."""

import argparse
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from argesim_benchmarks.models.c02_transport import C02Plant


def window_balance(pallets=25, *, unit_timing="exclusive"):
    plant = C02Plant(pallets, unit_timing=unit_timing, trace=True)
    result = plant.run()
    warm, end = plant.warmup, plant.end
    active = {}
    last = 0
    area = completed = completed_time = 0
    start_age = None
    for event in plant.trace:
        kind = event["event"]
        if kind not in ("load", "unloaded"):
            continue
        now, pallet = event["tick"], event["pallet"]
        if start_age is None and now >= warm:
            # Completions at warm-up are included in the reported cohort.
            start_age = sum(warm - birth for birth in active.values())
        area += max(0, now - max(last, warm)) * len(active)
        last = now
        if kind == "load":
            if pallet in active:
                raise AssertionError("overlapping C02 workpiece lifetimes")
            active[pallet] = now
        else:
            duration = now - active.pop(pallet)
            if now >= warm:
                completed += 1
                completed_time += duration
    if start_age is None:
        start_age = sum(warm - birth for birth in active.values())
    area += (end - max(last, warm)) * len(active)
    end_age = sum(end - birth for birth in active.values())

    residual = area - completed_time - (end_age - start_age)
    if residual != 0 or completed != result["throughput"]:
        raise AssertionError("C02 finite-window conservation failed")
    mean = completed_time * plant.tick_seconds / completed if completed else None
    reported = result["average_including_handling_seconds"]
    if mean is None:
        if reported is not None:
            raise AssertionError("C02 reported a mean for an empty cohort")
    elif reported is None or not math.isclose(
        reported, mean, rel_tol=0.0, abs_tol=1e-9
    ):
        raise AssertionError("C02 reported full-cycle mean differs from trace")

    return {
        "num_pallets": pallets,
        "unit_timing": unit_timing,
        "completed": completed,
        "full_cycle_mean_seconds": mean,
        "mean_active_workpieces": area / (end - warm),
        "age_change_pallet_seconds": (end_age - start_age) * plant.tick_seconds,
        "balance_residual_pallet_ticks": residual,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pallets", type=int, default=25)
    parser.add_argument(
        "--unit-timing", choices=("exclusive", "service-only"), default="exclusive"
    )
    args = parser.parse_args()
    print(
        json.dumps(window_balance(args.pallets, unit_timing=args.unit_timing), indent=2)
    )
