"""Leite die CP2-Abbildungen und Diagnosetabellen aus den veröffentlichten Protokollen ab."""

import argparse
import csv
import hashlib
import io
import json
from collections import defaultdict
from pathlib import Path
from statistics import median
from zipfile import ZipFile

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
SCAL = "Skalierung_Messdaten.zip"
PART = "PDES_Partitionierung_Messpaket.zip"
SLOW = "CP2_D2Q9_Ursache_Slowdown_257.zip"
PROF = "CP2_Kavitaet_257_QSS_Profil_eb1e551.zip"
COUNTS = (1, 2, 4, 8)


def jsonlines(archive, name):
    return [json.loads(line) for line in archive.read(name).splitlines() if line]


def write_csv(path, rows):
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def metrics(one, parallel, p):
    if min(one, parallel) <= 0 or p < 1:
        raise ValueError("Positive Zeit und Arbeiterzahl erwartet")
    speedup = one / parallel
    overhead = p * parallel - one
    return {
        "speedup": speedup,
        "effizienz_pct": 100 * speedup / p,
        "wand_mehr_s": parallel - one / p,
        "overhead_arbeiter_s": overhead,
        "karp_flatt_pct": None if p == 1 else 100 * overhead / ((p - 1) * one),
    }


def observation(series, scope, clock, p, repeat, value, source):
    return {
        "reihe": series,
        "umfang": scope,
        "uhr": clock,
        "p": p,
        "wiederholung": repeat,
        "t_s": value,
        "quelle": source,
    }


def summarize(samples):
    groups = defaultdict(lambda: defaultdict(list))
    for row in samples:
        groups[row["reihe"], row["umfang"], row["uhr"]][row["p"]].append(row["t_s"])
    points = []
    for (series, scope, clock), by_count in groups.items():
        one = median(by_count[1])
        for p, values in sorted(by_count.items()):
            tp = median(values)
            points.append(
                {
                    "reihe": series,
                    "umfang": scope,
                    "uhr": clock,
                    "p": p,
                    "n": len(values),
                    "n_basis": len(by_count[1]),
                    "t1_s": one,
                    "tp_s": tp,
                    "tp_min_s": min(values),
                    "tp_max_s": max(values),
                    **metrics(one, tp, p),
                    "s_min_feste_basis": 1 if p == 1 else one / max(values),
                    "s_max_feste_basis": 1 if p == 1 else one / min(values),
                }
            )
    return points


def event_owners(row):
    import numpy as np

    p = row["ranks"]
    ny = 2 if row["layout"] == "tiles" and p > 1 else p
    nx = p // ny
    grid = np.arange(255**2).reshape(255, 255)
    domains = [
        tile.ravel()
        for band in np.array_split(grid, ny)
        for tile in np.array_split(band, nx, axis=1)
    ]
    if [len(tile) for tile in domains] != row["rank_sizes"]:
        raise ValueError("Partitionskarte passt nicht zu den aufgezeichneten LP-Größen")
    due = np.concatenate(row["emitted"])
    return [int(np.isin(due, tile).sum()) for tile in domains]


def cavity_and_c19():
    samples, mpi, qss, pdes = [], [], [], []
    baseline = json.loads((LAB / "vollgitter.json").read_text(encoding="utf-8"))
    ref = baseline["runs"]["lbm1"]["field_sha256"]["350000"]
    with ZipFile(LAB / PROF) as archive:
        profile = json.loads(archive.read("auswertung.json"))["orders"]
    with ZipFile(LAB / SCAL) as archive:
        for line in archive.read("SHA256SUMS").decode().splitlines():
            digest, name = line.split("  ", 1)
            if hashlib.sha256(archive.read(name)).hexdigest() != digest:
                raise ValueError(f"Geänderte Quelle: {name}")
        for p in COUNTS:
            name = f"mpi/log-{p}.json"
            row = json.loads(archive.read(name))
            if (row["steps"], row["ranks"], row["field_sha256"]) != (350000, p, ref):
                raise ValueError(f"Endfeld oder Versuchsumfang: {name}")
            t = row["kernel_s"]
            samples.append(
                observation(
                    "D2Q9-MPI",
                    "Voll · 350000 Takte",
                    "MPI-Kern",
                    p,
                    1,
                    t,
                    SCAL + "!" + name,
                )
            )
            updates = 257**2 * row["steps"]
            mpi.append(
                {
                    "p": p,
                    "px": row["px"],
                    "py": row["py"],
                    "populationen_je_takt": row["populations_per_step"],
                    "gerichtete_paare": row["directed_peer_pairs"],
                    "groesstes_gebiet": ((257 + row["px"] - 1) // row["px"])
                    * ((257 + row["py"] - 1) // row["py"]),
                    "halo_byte": 8 * row["steps"] * row["populations_per_step"],
                    "mlups": updates / t / 1e6,
                    "modell_gb_s_144_byte": 144 * updates / t / 1e9,
                    "ausserhalb_kern_s": row["launcher_wall_s"] - t,
                }
            )
        for order in (3, 4):
            name = f"qss{order}-lps.jsonl"
            rows = jsonlines(archive, name)
            if len({r["digest"] for r in rows}) != 1:
                raise ValueError("Abweichende QSS-Zustandsfolgen")
            for p in COUNTS:
                reps = [r for r in rows if r["ranks"] == p]
                if sorted(r["repeat"] for r in reps) != [1, 2, 3]:
                    raise ValueError("Drei Wiederholungen je QSS-Reihe erwartet")
                for row in reps:
                    if not (
                        row["segments"] == 8
                        and len(row["times"]) == 9
                        and row["digest"] == row["oracle_sha256"]
                        and row["distinct_processes"] == p
                    ):
                        raise ValueError(
                            f"QSS-Präfix stimmt nicht mit Referenz überein: {name}"
                        )
                    samples.append(
                        observation(
                            f"QSS{order}",
                            "Präfix · 8 Intervalle",
                            "Wand inkl. Start und Rückgabe",
                            p,
                            row["repeat"],
                            row["wall_s"],
                            SCAL + "!" + name,
                        )
                    )
                rep = reps[0]
                qss.append(
                    {
                        "ordnung": order,
                        "p": p,
                        "karte": rep["layout"],
                        "endzeit": rep["times"][-1],
                        "rhs": rep["rhs"],
                        "poisson_byte": rep["payload_bytes"].get("poisson_fields", 0),
                        "feldnachrichten": rep["messages"].get("poisson_fields", 0),
                        "minimum_nachrichten": rep["messages"].get("event_minimum", 0),
                        "schritt_nachrichten": rep["messages"].get("stencil_bounds", 0),
                        "validierung_byte": rep["payload_bytes"].get(
                            "validation_fields", 0
                        ),
                        "zellen_min": min(rep["rank_sizes"]),
                        "zellen_max": max(rep["rank_sizes"]),
                        "cpu_ids": json.dumps(rep["cpu_ids"]),
                        "aktive_kontakte_je_lp": json.dumps(event_owners(rep)),
                        **{
                            "serienprofil_pct_" + k: v
                            for k, v in profile[str(order)]["median_percent"].items()
                        },
                        "ausserhalb_kern_median_s": median(
                            r["wall_s"] - r["kernel_s"] for r in reps
                        ),
                        "kern_median_s": median(r["kernel_s"] for r in reps),
                    }
                )
        for row in jsonlines(archive, "c19-scaling.jsonl"):
            if not row["verified"] or row["committed"] != 65292:
                raise ValueError("C19R-Ereignisspur")
            mode = row["mode"]
            samples.append(
                observation(
                    "C19R-" + mode,
                    "Voll · 10 Modelltage",
                    "Kern",
                    row["ranks"],
                    row["repeat"],
                    row["wall_s"],
                    SCAL + "!c19-scaling.jsonl",
                )
            )
            pdes.append(pdes_diagnostics("C19R", row))
    with ZipFile(LAB / PART) as archive:
        for case in ("rope_pilot", "rope_pilot_freq"):
            for name in ("cons.jsonl", "opt_short.jsonl"):
                member = case + "/" + name
                for row in jsonlines(archive, member):
                    if row["layout"] != ("one" if row["ranks"] == 1 else "weighted"):
                        continue
                    if not row["verified"]:
                        raise ValueError(member)
                    series = case + "-" + row["mode"]
                    samples.append(
                        observation(
                            series,
                            "Präfix · 4 Modellsekunden",
                            "Kern",
                            row["ranks"],
                            row.get("repeat", 1),
                            row["wall_s"],
                            PART + "!" + member,
                        )
                    )
                    pdes.append(pdes_diagnostics(case, row))
        rows = jsonlines(archive, "d2q9_paired.jsonl")
        base = [r for r in rows if r["ranks"] == 1]
        for px, py in sorted({(r["px"], r["py"]) for r in rows if r["ranks"] > 1}):
            for row in [*base, *(r for r in rows if (r["px"], r["py"]) == (px, py))]:
                if row["steps"] != 1024 or not row["equal_published_solver"]:
                    raise ValueError("D2Q9-Partitionsvergleich")
                samples.append(
                    observation(
                        f"D2Q9-Karte-{px}x{py}",
                        "Präfix · 1024 Takte",
                        "MPI-Kern",
                        row["ranks"],
                        row["repeat"],
                        row["kernel_s"],
                        PART + "!d2q9_paired.jsonl",
                    )
                )
        for row in jsonlines(archive, "c19_paired.jsonl"):
            if row["layout"] == ("one" if row["ranks"] == 1 else "weighted"):
                samples.append(
                    observation(
                        row["case"] + "-Partitionsreihe-" + row["mode"],
                        "Voll · 10 Modelltage",
                        "Kern",
                        row["ranks"],
                        row["repeat"],
                        row["wall_s"],
                        PART + "!c19_paired.jsonl",
                    )
                )
    return samples, mpi, qss, pdes


def pdes_diagnostics(case, row):
    return {
        "versuch": case,
        **{
            key: row[key]
            for key in (
                "ranks",
                "repeat",
                "mode",
                "layout",
                "wall_s",
                "committed",
                "rollbacks",
                "discarded_events",
                "processed",
                "probe_events",
                "safe_cuts",
                "rounds",
                "wire_events",
            )
        },
    }


def historical_csv(name):
    return list(
        csv.DictReader(
            io.StringIO((HERE / "historisch" / name).read_text(encoding="utf-8-sig"))
        )
    )


def openmp():
    pairs = []

    def record(label, scope, repeat, one, four, source):
        pairs.append(
            {
                "versuch": label,
                "umfang": scope,
                "wiederholung": repeat,
                "t1_s": one,
                "t4_s": four,
                "speedup_gepaart": one / four,
                "quelle": source,
            }
        )

    full = [historical_csv(f) for f in ("re1000.csv", "pruef4.csv")]
    pilot = [historical_csv(f) for f in ("pilot1.csv", "pilot4.csv")]
    for label, scope, rows, step, source in (
        ("Intel · Kern", "Voll", full, 350000, "re1000.csv + pruef4.csv"),
        ("Intel · erste 1024", "Präfix", full, 1024, "re1000.csv + pruef4.csv"),
        ("Intel · Pilot 1024", "Präfix", pilot, 1024, "pilot1.csv + pilot4.csv"),
    ):
        t = [
            float(next(r for r in run if int(r["step"]) == step)["wall_s"])
            for run in rows
        ]
        record(label, scope, 1, *t, source)
    total = historical_csv("d2q9_prozesszeit.csv")
    if len(total) != 2:
        raise ValueError("Historisches Paar mit sieben Ausgaben fehlt")
    # The historical process-clock table records one full run per thread count.
    tkey = next(k for k in total[0] if "wall" in k)
    nkey = next(k for k in total[0] if "thread" in k)
    values = {int(r[nkey]): float(r[tkey]) for r in total}
    record(
        "Intel · Gesamt, 7 Ausgaben",
        "Voll",
        1,
        values[1],
        values[4],
        "d2q9_prozesszeit.csv",
    )
    with ZipFile(LAB / SLOW) as archive:
        rows = jsonlines(archive, "messungen/full_runs.jsonl")
        ones = sorted((r for r in rows if r["threads"] == 1), key=lambda r: r["run"])
        fours = sorted((r for r in rows if r["threads"] == 4), key=lambda r: r["run"])
        for rep, (one, four) in enumerate(zip(ones, fours, strict=True), 1):
            if (
                one["field_hashes"] != four["field_hashes"]
                or len(one["field_hashes"]) != 37
            ):
                raise ValueError("OpenMP-Vollfelder")
            record(
                "EPYC · Kern",
                "Voll",
                rep,
                one["kernel_wall_s"],
                four["kernel_wall_s"],
                SLOW + "!messungen/full_runs.jsonl",
            )
        rows = jsonlines(archive, "messungen/contention_runs.jsonl")
        by_key = {(r["competitors"], r["repeat"], r["threads"]): r for r in rows}
        for n in (0, 3):
            for rep in range(1, 6):
                one, four = by_key[n, rep, 1], by_key[n, rep, 4]
                if (
                    one["field_sha256"] != four["field_sha256"]
                    or not one["steps"] == four["steps"] == 4096
                ):
                    raise ValueError("OpenMP-Lastpaar")
                record(
                    f"EPYC · {n} Lastprozesse",
                    "Präfix",
                    rep,
                    one["wall_s"],
                    four["wall_s"],
                    SLOW + "!messungen/contention_runs.jsonl",
                )
        affinity = jsonlines(archive, "messungen/against_1024.jsonl")
        one = {r["repeat"]: r for r in affinity if r["case"] == "1t_1cpu_default"}
        bindings = [
            {
                "fall": r["case"],
                "wiederholung": r["repeat"],
                "cpu_ids": json.dumps(r["allowed_cpus"]),
                "threads": r["threads"],
                "wartepolitik": r["wait_policy"],
                "cpu_s": r["cpu_s"],
                "wand_s": r["wall_s"],
                "speedup_gepaart": one[r["repeat"]]["wall_s"] / r["wall_s"],
            }
            for r in affinity
        ]
    return pairs, bindings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ausgabe", type=Path, required=True)
    out = parser.parse_args().ausgabe
    (out / "ergebnisse").mkdir(parents=True, exist_ok=True)
    (out / "abbildungen").mkdir(exist_ok=True)
    manifest = json.loads((HERE / "quellstand.json").read_text(encoding="utf-8"))
    for name, entry in manifest["dateien"].items():
        path = (HERE if name.startswith("historisch/") else LAB) / name
        if hashlib.sha256(path.read_bytes()).hexdigest() != entry["sha256"]:
            raise ValueError(f"Prüfsumme stimmt nicht: {name}")
    samples, mpi, qss, pdes = cavity_and_c19()
    points = summarize(samples)
    pairs, affinity = openmp()
    tables = {
        "einzelzeiten": samples,
        "kennzahlen": points,
        "diagnose_mpi": mpi,
        "diagnose_qss": qss,
        "diagnose_pdes": pdes,
        "openmp_messpaare": pairs,
        "openmp_affinitaet": affinity,
    }
    for name, rows in tables.items():
        write_csv(out / "ergebnisse" / (name + ".csv"), rows)
    from abbildungen import zeichnen

    zeichnen(out, points, pairs)
    print(
        f"{len(points)} Skalierungspunkte, {len(pairs)} OpenMP-Paare, vier Abbildungen"
    )


if __name__ == "__main__":
    main()
