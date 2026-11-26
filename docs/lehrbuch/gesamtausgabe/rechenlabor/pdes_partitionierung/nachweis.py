"""Check the CP2 observations and derive the two-reference table from the primary data."""
import hashlib
import json
import math
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
METHODS = {
    "lbm1": "D2Q9, 1 Thread",
    "lbm4": "D2Q9, 4 Threads",
    "ab2-s2": "AB2, 2 Takte",
    "ab2-s4": "AB2, 4 Takte",
    "dop853": "DOP853, adaptiv",
    "gqss1": "Gruppen-QSS1",
    "gqss2": "Gruppen-QSS2",
}
TICKS = [256, 4096, 16384, 65536, 131072, 262144, 350000]


def decimal(value, places):
    return f"{value:.{places}f}".replace(".", ",")


def table(rows):
    lines = []
    for method, label in METHODS.items():
        data = rows[method]
        elapsed = decimal(data["history"][-1]["wall_s"], 2)
        errors = []
        for reference in ("vs_lbm", "vs_dop853"):
            error = max(r[reference]["relative_l2"] for r in data["comparisons"])
            errors.append(decimal(100 * error, 5).rstrip("0").rstrip(","))
        lines.append(f"| {label} | {elapsed} | {errors[0]} | {errors[1]} |")
    return "\n".join(lines)


def verify(edition):
    data = json.loads((HERE / "vollgitter.json").read_text())
    setup, runs = data["setup"], data["runs"]
    if setup["reference_ticks"] != TICKS or set(runs) != set(METHODS):
        raise ValueError("Incomplete CP2 methods or reference ticks")
    for name, run in runs.items():
        hist = run["history"]
        if (len(hist) != 37 or [r["step"] for r in hist] != setup["all_ticks"]
                or hist[-1]["t_star"] != 136.71875 or hist[-1]["step"] != 350000
                or list(map(int, run["field_sha256"])) != setup["all_ticks"]
                or [r["step"] for r in run["comparisons"]] != TICKS):
            raise ValueError(f"Incomplete trajectory: {name}")
        times = [0.0, *(r["wall_s"] for r in hist)]
        if any(not a < b for a, b in zip(times, times[1:])):
            raise ValueError(f"Invalid cumulative timing: {name}")
        for r in run["comparisons"]:
            for reference in ("vs_lbm", "vs_ab2_s2", "vs_dop853"):
                if any(not math.isfinite(e) or e < 0 for e in r[reference].values()):
                    raise ValueError(f"Invalid field comparison: {name}")
    if runs["lbm1"]["field_sha256"] != runs["lbm4"]["field_sha256"]:
        raise ValueError("D2Q9 equality failed")
    for name, reference in (("lbm1", "vs_lbm"), ("lbm4", "vs_lbm"),
                            ("ab2-s2", "vs_ab2_s2"), ("dop853", "vs_dop853")):
        if any(any(r[reference].values()) for r in runs[name]["comparisons"]):
            raise ValueError(f"Reference mismatch: {name}")
    with zipfile.ZipFile(HERE / "DOP853_Prueffelder.zip") as fields:
        if set(fields.namelist()) != {f"z_{tick}.bin" for tick in TICKS}:
            raise ValueError("Missing DOP853 reference field")
        for tick in TICKS:
            values = fields.read(f"z_{tick}.bin")
            if (len(values) != 255 * 255 * 8
                    or hashlib.sha256(values).hexdigest() != runs["dop853"]["field_sha256"][str(tick)]):
                raise ValueError(f"Invalid DOP853 reference field at {tick}")
    values = table(runs)
    for doc in ("kapitel/16.md", "lehrbuch_numerische_simulation.md"):
        if (edition / doc).read_text().count(values) != 1:
            raise ValueError(f"Printed full-grid table differs from the measurements: {doc}")
    with zipfile.ZipFile(HERE / "PDES_Partitionierung_Messpaket.zip") as package:
        for line in package.read("SHA256SUMS").decode().splitlines():
            sha, path = line.split("  ", 1)
            if hashlib.sha256(package.read(path)).hexdigest() != sha:
                raise ValueError(f"PDES measurement checksum mismatch: {path}")


if __name__ == "__main__":
    verify(HERE.parents[1])
