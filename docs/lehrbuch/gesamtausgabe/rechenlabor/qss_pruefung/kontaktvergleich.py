"""Compare the primary v9.18 and v9.19 runs by model, method and setting."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

MEASUREMENTS = Path(__file__).resolve().parent / "messung"
SUITES = {"baseline": 399, "extension": 456, "selection": 520, "rk23": 138}
WORK = ("accepted", "rejected", "rhs", "lu")


def read_suite(path, size):
    with path.open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    by_setting = {
        (row["case"], row.get("method", row.get("solver")),
         row.get("level", row.get("quantum_factor"))): row for row in rows
    }
    if len(by_setting) != size or len(rows) != size:
        raise ValueError(f"{path} must contain {size} distinct settings")
    return by_setting


def score(row):
    return row.get("error_over_limit", row.get("error"))


def compare(previous, current):
    comparisons = []
    summaries = {}
    for suite, size in SUITES.items():
        before_path, after_path = (directory / f"{suite}.csv" for directory in (previous, current))
        before, after = read_suite(before_path, size), read_suite(after_path, size)
        if before.keys() != after.keys():
            raise ValueError(f"Unpaired settings in {suite}")
        counts = Counter()
        for (case, method, level), b in sorted(after.items()):
            a = before[case, method, level]
            old, new = score(a), score(b)
            paired = bool(old and new)
            moved = paired and float(old) != float(new)
            switches = a["status"] != b["status"]
            work = [k for k in WORK if a.get(k) and b.get(k) and a[k] != b[k]]
            comparisons.append(dict(suite=suite, case=case, method=method, level=level,
                                    status_before=a["status"], status_after=b["status"],
                                    score_before=old, score_after=new, changed_counters=" ".join(work),
                                    median_ms_before=a["median_ms"], median_ms_after=b["median_ms"]))
            counts.update(configurations=1, paired_scores=int(paired), different_scores=int(moved),
                          status_changes=int(switches), work_changes=bool(work),
                          timeout_changes=int(switches and "timeout" in (a["status"], b["status"])))
            if method in ("qss3", "qss4"):
                counts.update(qss34=1, qss34_paired_scores=int(paired), qss34_different_scores=int(moved),
                              qss34_status_changes=int(switches))
        summaries[suite] = {**counts, "status": dict(sorted(Counter(r["status"] for r in after.values()).items())),
                            "before_sha256": hashlib.sha256(before_path.read_bytes()).hexdigest(),
                            "after_sha256": hashlib.sha256(after_path.read_bytes()).hexdigest()}
    return comparisons, summaries


if __name__ == "__main__":
    current = MEASUREMENTS / "kontakt_v919"
    rows, summary = compare(MEASUREMENTS / "skalenfix_c635504", current)
    with (current / "vergleich.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0], lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    (current / "vergleich.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
