"""Verify both archived CP2 states and, on request, continue each exactly one segment."""
import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
PDES = Path("rechenlabor/pdes_partitionierung")
ORDERS = (3, 4)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_manifest():
    manifest = json.loads((HERE / "fortsetzungsquellen.json").read_text(encoding="utf-8"))
    contract = json.loads((HERE / "restart_kompatibilitaet.json").read_text(encoding="utf-8"))
    source = HERE / "CP2_Fortsetzungsquellen.zip"
    if sha(source.read_bytes()) != manifest["archive_sha256"]:
        raise ValueError("Invalid frozen CP2 source archive")
    with zipfile.ZipFile(source) as archive:
        if set(archive.namelist()) != manifest["files"].keys() or len(archive.namelist()) != len(manifest["files"]):
            raise ValueError("Frozen source archive members differ from manifest")
        for path, digest in manifest["files"].items():
            if sha(archive.read(path)) != digest:
                raise ValueError(f"Frozen source differs from manifest: {path}")
        archived = (PDES / "qss_langlauf.py").as_posix()
        if sha(archive.read(archived)) != manifest["continuation_integrator_sha256"] or (
            manifest["continuation_integrator_sha256"] != contract["experiment"]["sources"]["integrator"]
        ):
            raise ValueError("Inconsistent frozen integrator identity")
    with zipfile.ZipFile(HERE / "Skalierung_Messdaten.zip") as data:
        recorded = json.loads(data.read("platform.json"))
        if recorded["sources"]["qss_langlauf.py"] != manifest["historical_integrator_sha256"] or any(
            recorded[key] != version for key, version in manifest["runtime"].items()
        ):
            raise ValueError("Inconsistent historical integrator or runtime")
    with zipfile.ZipFile(HERE / "QSS34_Fortsetzung.zip") as seed:
        for order in ORDERS:
            member = f"qss{order}/restart.npz"
            if sha(seed.read(member)) != contract["checkpoints"][str(order)]:
                raise ValueError(f"Invalid CP2 seed bytes: {member}")
    return manifest


def verify_runtime(manifest):
    import numpy as np
    import scipy

    versions = {"python": ".".join(map(str, sys.version_info[:3])), "numpy": np.__version__, "scipy": scipy.__version__}
    if versions != manifest["runtime"]:
        raise RuntimeError(f"Expected CP2 restart runtime {manifest['runtime']}, found {versions}")
    env = {**os.environ, **dict.fromkeys(
        ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"), "1")}
    evidence = {}
    with tempfile.TemporaryDirectory(prefix="cp2-fortsetzungsprobe-") as temporary:
        root = Path(temporary)
        sources, states = root / "sources", root / "states"
        with zipfile.ZipFile(HERE / "CP2_Fortsetzungsquellen.zip") as archive:
            archive.extractall(sources)
        with zipfile.ZipFile(HERE / "QSS34_Fortsetzung.zip") as archive:
            archive.extractall(states)

        for order in ORDERS:
            state = states / f"qss{order}"
            with np.load(state / "restart.npz", allow_pickle=False) as seed:
                meta = json.loads(str(seed["config"]))
                if meta != [257, 1000, 350000, 0.001, order, manifest["historical_integrator_sha256"]]:
                    raise ValueError(f"QSS{order} seed metadata does not identify the historical integrator")
                previous_segment, previous_events, previous_time = (
                    int(seed["segments"]), int(seed["events"]), float(seed["now"]),
                )
            run = subprocess.run(
                [sys.executable, str(sources / PDES / "qss_langlauf.py"), str(sources), str(state),
                 "--order", str(order), "--resume", "--stop-after", str(previous_segment + 1)],
                check=True, text=True, capture_output=True, env=env, timeout=60,
            )
            progress = json.loads(run.stdout.splitlines()[-1])
            with np.load(state / "restart.npz", allow_pickle=False) as replay:
                config = json.loads(str(replay["config"]))
                if (
                    progress["complete"] or progress["order"] != order
                    or progress["segments"] != int(replay["segments"])
                    or progress["segments"] != previous_segment + 1
                    or progress["t_star"] != float(replay["now"])
                    or not previous_time < progress["t_star"]
                    or not previous_events < progress["events"] == int(replay["events"])
                    or config["sources"]["integrator"] != manifest["continuation_integrator_sha256"]
                    or not np.isfinite(replay["q"]).all() or not np.isfinite(replay["x"]).all()
                ):
                    raise ValueError(f"QSS{order} continuation did not produce exactly one valid segment")
                state_sha = sha(replay["x"].astype("<f8").tobytes() + replay["q"].astype("<f8").tobytes())
            evidence[str(order)] = {
                "segments_before": previous_segment, "segments_after": progress["segments"],
                "t_star_before": previous_time, "t_star_after": progress["t_star"],
                "events_before": previous_events, "events_after": progress["events"],
                "polynomials_sha256": state_sha, "complete": False,
            }
    return {"runtime": versions, "integrator_revision": manifest["integrator_revision"], "states": evidence}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume-one", action="store_true", help="run one segment of each frozen QSS seed")
    args = parser.parse_args()
    checked = verify_manifest()
    outcome = verify_runtime(checked) if args.resume_one else {
        "verified_seed_orders": list(ORDERS),
        "integrator_revision": checked["integrator_revision"],
        "historical_integrator_bytes_available": checked["historical_integrator_bytes_available"],
    }
    print(json.dumps(outcome, indent=2))
