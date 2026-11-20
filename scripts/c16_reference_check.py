"""Compare the week-260 restaurant counts in a C16 Task A JSON run with published studies."""

import json
import math
import statistics
import sys

# Both publications report the week-260 mean and variance of 50 replications.
PUBLISHED = {"AnyLogic": (6.34, 1.98), "Java OO": (6.06, 2.02)}


def main() -> int:
    study = json.load(sys.stdin)
    counts = study["restaurants_at_year_5"]
    if len(counts) != 50 or any(type(n) is not int or n < 0 for n in counts):
        raise ValueError("expected 50 restaurant counts from the end of year five")
    mean = statistics.mean(counts)
    variance = statistics.variance(counts)
    if mean != study["mean_at_year_5"]:
        raise ValueError("reported mean differs from the individual counts")
    comparisons = {}
    for source, (reference_mean, reference_variance) in PUBLISHED.items():
        standard_error = math.sqrt(variance / len(counts) + reference_variance / 50)
        tolerance = 3 * standard_error + 0.005
        comparisons[source] = {
            "published_mean": reference_mean, "published_variance": reference_variance,
            "difference": mean - reference_mean, "tolerance": tolerance,
            "passed": abs(mean - reference_mean) <= tolerance,
        }
    print(json.dumps({
        "week_260_counts": counts, "mean": mean, "sample_variance": variance,
        "comparisons": comparisons,
    }, indent=2))
    return 0 if all(row["passed"] for row in comparisons.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
