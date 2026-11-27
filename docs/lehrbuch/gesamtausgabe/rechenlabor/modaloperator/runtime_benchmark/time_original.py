"""Time the complete published comparison in an independent unpacked working directory."""

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import time
import zipfile
from pathlib import Path


def check_published_input(lab):
    """Confirm the actual source, reference data and published weights before timing."""
    archive = Path(__file__).with_name("archived") / "study_before_runtime.zip"
    sha = hashlib.sha256(archive.read_bytes()).hexdigest()
    if sha != "7cc19709cb531a55d748a6487f4541981e37e89c6c8d7f9b7f3906b3194f5daf":
        raise ValueError("unexpected reference archive")
    with zipfile.ZipFile(archive) as files:
        for entry in files.namelist():
            relative = Path(entry).relative_to("ARGESIM_Operatorenlabor")
            timed_input = (
                relative.suffix in {".py", ".sh"}
                or relative.parts[:1] == ("reference",)
                or relative.parts[:2] == ("results", "weights")
            )
            if timed_input and (lab / relative).read_bytes() != files.read(entry):
                raise ValueError(f"input differs from the published study: {relative}")
    return sha


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("lab", type=Path, help="fresh extraction of the original laboratory")
    p.add_argument("record", type=Path)
    args = p.parse_args()
    lab = args.lab.resolve()
    record = args.record.resolve()
    record.parent.mkdir(parents=True, exist_ok=True)
    source_sha = check_published_input(lab)
    env = {
        **os.environ,
        "PYTHON": sys.executable,
        "OMP_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
    }
    phases = {}
    commands = (
        ("replication", ["sh", "reproduce.sh", "repeat-clock"]),
        ("chapter", [sys.executable, "report.py", "--results", "repeat-clock"]),
    )
    start = time.perf_counter()
    for name, command in commands:
        tick = time.perf_counter()
        with (record.parent / (name + ".log")).open("w") as log:
            subprocess.run(
                command,
                cwd=lab,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
            )
        phases[name] = time.perf_counter() - tick
    total = time.perf_counter() - start
    fits = [
        json.loads(p.read_text())["train_s"]
        for p in (lab / "repeat-clock" / "weights").glob("*.json")
    ]
    if len(fits) != 42:
        raise ValueError("expected 42 complete fits")
    record.write_text(
        json.dumps(
            {
                "original_archive_sha256": source_sha,
                "phases_seconds": phases,
                "wall_seconds": total,
                "sum_inner_fits_seconds": sum(fits),
                "trained_networks": len(fits),
                "python": platform.python_version(),
                "notes": "Wall time around subprocesses; includes startup, tests, generation, fitting, scoring, file I/O and chapter rendering. Excludes installation and archive transfer.",
            },
            indent=2,
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
