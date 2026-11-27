"""Publish or verify the German complete edition and its reproducible QSS lab."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import runpy
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from pathlib import Path

if __package__:
    from . import build_studienbuch_kompakt as compact
else:
    import build_studienbuch_kompakt as compact

ROOT = compact.ROOT
DOCS = compact.DOCS
MATERIAL = compact.MATERIAL
PDF, LAB, RECORD = compact.PDF, compact.LAB, compact.RECORD
EDITION = DOCS / "lehrbuch" / "gesamtausgabe"
PRINT = EDITION / "druck"
PACKAGES = EDITION / "pakete"
AUDIT = Path("rechenlabor/qss_pruefung")
COMPARISON = AUDIT / "messung/revisionsvergleich.csv"
REPLAY = COMPARISON.parent / "skalenfix_c635504"
MANUSCRIPT = "lehrbuch_numerische_simulation.md"
CONTACT = COMPARISON.parent / "kontakt_v919"
PDES = Path("rechenlabor/pdes_partitionierung")
REVISION = "v9.22"
DATE = (2026, 11, 26, 0, 0, 0)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def edition_files():
    return sorted(
        p
        for p in EDITION.rglob("*")
        if p.is_file()
        and not any(
            x == "__pycache__" or x.startswith(".")
            for x in p.relative_to(EDITION).parts
        )
    )


def verify_measurements():
    compact.verify_measurements()
    scaling = runpy.run_path(str(EDITION / PDES / "skalierung_pruefen.py"))
    scaling["summaries"]()
    scaling["verify_field_archives"]()
    runpy.run_path(str(EDITION / PDES / "nachweis.py"))["verify"](EDITION)
    with (EDITION / COMPARISON).open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    counts = Counter(r["reihe"] for r in rows)
    keys = {(r["reihe"], r["fall"], r["verfahren"], r["einstellung"]) for r in rows}
    if counts != {
        "baseline": 399,
        "extension": 456,
        "selection": 520,
        "rk23": 138,
    } or len(keys) != len(rows):
        raise ValueError(
            "The QSS comparison must contain 1,513 distinct configurations across four suites."
        )
    with (EDITION / REPLAY / "skalenvergleich.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        replay_rows = list(csv.DictReader(stream))
    replay_keys = {
        (r["suite"], r["case"], r["method"], r["level"]) for r in replay_rows
    }
    if replay_keys != keys or len(replay_rows) != len(keys):
        raise ValueError(
            "The full replay on the reviewed solver must cover the same configurations."
        )
    summary = json.loads(
        (EDITION / REPLAY / "skalenvergleich.json").read_text(encoding="utf-8")
    )
    for suite, count in counts.items():
        record = summary[suite]
        name = suite + ".csv"
        if (
            record["configurations"] != count
            or record["archived_csv_sha256"]
            != sha256(EDITION / COMPARISON.parent / name)
            or record["repeated_csv_sha256"] != sha256(EDITION / REPLAY / name)
        ):
            raise ValueError(
                f"Replay manifest does not match the primary measurements for {suite}."
            )
    compare = runpy.run_path(str(EDITION / AUDIT / "kontaktvergleich.py"))["compare"]
    paired, totals = compare(EDITION / REPLAY, EDITION / CONTACT)
    current = EDITION / CONTACT
    with (current / "vergleich.csv").open(encoding="utf-8", newline="") as stream:
        if list(csv.DictReader(stream)) != paired:
            raise ValueError(
                "Contact comparison differs from the primary measurements."
            )
    if totals != json.loads((current / "vergleich.json").read_text()):
        raise ValueError("Contact summary differs from the primary measurements.")
    for suite in totals:
        name = "rk23-devs" if suite == "rk23" else "qss-" + suite
        if sha256(EDITION / "daten" / (name + ".csv")) != totals[suite]["after_sha256"]:
            raise ValueError(
                f"Current textbook matrix differs from the replay: {suite}"
            )
    with zipfile.ZipFile(PACKAGES / "Laborquellen.zip") as sources:
        for name in ("_polynomial.py", "advanced_qss.py", "qss.py"):
            path = Path("argesim_benchmarks/solvers") / name
            expected = (ROOT / path).read_bytes()
            for directory in (
                AUDIT / "quellen",
                Path("rechenlabor/messplanung/projekt"),
                Path("rechenlabor/kavitaet_vollgitter/basis/original"),
                Path("rechenlabor/kavitaet_kleingitter/original"),
            ):
                if sources.read((directory / path).as_posix()) != expected:
                    raise ValueError(
                        f"Published solver differs from {path} in {directory}"
                    )
        regression = "test_qss_calendar_regressions.py"
        if (
            sources.read((AUDIT / "programme" / regression).as_posix())
            != (ROOT / "tests" / regression).read_bytes()
        ):
            raise ValueError(
                "Published calendar regression tests differ from the repository."
            )


def distribution_record(out):
    digest = hashlib.sha256()
    digest.update(bytes.fromhex(compact.source_digest(compact.material_files())))
    for path in sorted([*edition_files(), Path(__file__).resolve()]):
        digest.update(path.relative_to(ROOT).as_posix().encode() + b"\0")
        digest.update(bytes.fromhex(sha256(path)))
    return {
        "edition": REVISION,
        "sources_sha256": digest.hexdigest(),
        "outputs_sha256": {name: sha256(out / name) for name in (PDF, LAB)},
    }


def check(out):
    verify_measurements()
    if json.loads((out / RECORD).read_text(encoding="utf-8")) != distribution_record(
        out
    ):
        raise ValueError(
            "Textbook sources, PDF or lab changed. Rebuild and commit the edition together."
        )


def write_entry(archive, name, data):
    info = zipfile.ZipInfo(name, DATE)
    info.external_attr = (0o100755 if name.endswith(".sh") else 0o100644) << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    archive.writestr(info, data, compresslevel=6)


def core_lab(path):
    """Keep the established exercises at the root and the current calendar lab under rechenlabor/."""
    with zipfile.ZipFile(path, "w") as lab:
        for source in compact.material_files():
            write_entry(
                lab, source.relative_to(MATERIAL).as_posix(), source.read_bytes()
            )
        write_entry(lab, "START_v9_22.md", (EDITION / "Labor.md").read_bytes())
        for name in ("kapitel/16.md", MANUSCRIPT):
            write_entry(lab, name, (EDITION / name).read_bytes())
        matrix = Path("daten/qss-extension.csv")
        write_entry(lab, matrix.as_posix(), (EDITION / matrix).read_bytes())
        with zipfile.ZipFile(PACKAGES / "Laborquellen.zip") as source:
            for name in sorted(source.namelist()):
                if name.startswith((AUDIT.as_posix() + "/", "beispiele/")):
                    write_entry(lab, name, source.read(name))
        separate_fields = {
            "D2Q9_Prueffelder.zip",
            "Gruppen_QSS34_Prueffelder.zip",
            "QSS34_Fortsetzung.zip",
        }
        for source in sorted((EDITION / PDES).iterdir()):
            if source.is_file() and source.name not in separate_fields:
                write_entry(
                    lab, source.relative_to(EDITION).as_posix(), source.read_bytes()
                )
        for source in sorted((EDITION / AUDIT).rglob("*")):
            if source.is_file() and "__pycache__" not in source.parts:
                write_entry(
                    lab, source.relative_to(EDITION).as_posix(), source.read_bytes()
                )


def full_lab(target):
    """Reconstruct the complete, self-contained offline lab from the checked-in volumes."""
    target = target.resolve()
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target.parent) as tmp:
        zipped = Path(tmp) / "complete.zip"
        with zipfile.ZipFile(zipped, "w") as lab:
            # Sources and evidence retain the directory layout expected by the original experiments.
            for source in edition_files():
                rel = source.relative_to(EDITION)
                if (
                    rel.parts[0] != "pakete"
                    and rel.as_posix() != "druck/Druckabbildungen.zip"
                ):
                    write_entry(lab, rel.as_posix(), source.read_bytes())
            with zipfile.ZipFile(PRINT / "Druckabbildungen.zip") as figures:
                for name in figures.namelist():
                    write_entry(lab, "druck/" + name, figures.read(name))
            with zipfile.ZipFile(PACKAGES / "Laborquellen.zip") as core:
                for name in core.namelist():
                    write_entry(lab, name, core.read(name))
            index = json.loads(
                (PACKAGES / "Feldpakete.json").read_text(encoding="utf-8")
            )
            for name, record in sorted(index.items()):
                data = b"".join((PACKAGES / p).read_bytes() for p in record["parts"])
                if (
                    len(data) != record["size"]
                    or hashlib.sha256(data).hexdigest() != record["sha256"]
                ):
                    raise ValueError(f"Field archive changed or incomplete: {name}")
                with zipfile.ZipFile(io.BytesIO(data)) as fields:
                    for field in fields.namelist():
                        if field in lab.NameToInfo:
                            raise ValueError(
                                f"Duplicate entry in the full lab: {field}"
                            )
                        write_entry(lab, field, fields.read(field))
        with zipfile.ZipFile(zipped) as assembled:
            if (
                len(assembled.namelist()) != len(set(assembled.namelist()))
                or assembled.testzip()
            ):
                raise ValueError("Invalid full lab archive")
        zipped.replace(target)


def typeset(stage):
    input_dir = stage / "input"
    working = input_dir / "druck"
    working.mkdir(parents=True)
    shutil.copyfile(EDITION / MANUSCRIPT, input_dir / MANUSCRIPT)
    shutil.copyfile(PRINT / "setzen.py", working / "setzen.py")
    subprocess.run([sys.executable, str(working / "setzen.py")], check=True)
    if (working / "buch.tex").read_bytes() != (PRINT / "buch.tex").read_bytes():
        raise ValueError(
            "The print source differs from the Markdown manuscript generated with Pandoc."
        )
    with zipfile.ZipFile(PRINT / "Druckabbildungen.zip") as figures:
        for name in figures.namelist():
            if name != Path(name).name or not name.endswith(".pdf"):
                raise ValueError(f"Invalid print figure: {name}")
            (working / name).write_bytes(figures.read(name))
    env = {
        **os.environ,
        "TZ": "UTC",
        "SOURCE_DATE_EPOCH": "1795651200",
        "FORCE_SOURCE_DATE": "1",
    }
    previous = None
    for _ in range(5):
        proc = subprocess.run(
            [
                "xelatex",
                "-no-pdf",
                "-halt-on-error",
                "-interaction=nonstopmode",
                "buch.tex",
            ],
            cwd=working,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        if proc.returncode:
            raise ValueError(proc.stdout[-4000:])
        aux = (working / "buch.aux").read_bytes()
        if aux == previous:
            break
        previous = aux
    else:
        raise ValueError("LaTeX cross-references did not stabilize.")
    for warning in (
        "undefined references",
        "multiply defined",
        "Missing character",
        "Rerun to get cross-references",
    ):
        if warning in proc.stdout:
            raise ValueError(f"XeLaTeX: {warning}")
    subprocess.run(
        ["xdvipdfmx", "-q", "-o", str(stage / "text.pdf"), "buch.xdv"],
        cwd=working,
        env=env,
        check=True,
    )


def verify_navigation(book):
    toc = book.get_toc()
    chapters = [
        int(match[1])
        for level, title, _ in toc
        if level == 2 and (match := re.match(r"^Kapitel (\d+) ·", title))
    ]
    if (
        chapters != list(range(1, 19))
        or sum(bool(re.match(r"^A\.\d+\b", title)) for _, title, _ in toc) != 24
    ):
        raise ValueError(
            "The book must contain chapters 1–18 and all 24 benchmark entries."
        )
    appendices = [
        m[1]
        for level, title, _ in toc
        if level == 2 and (m := re.match(r"^Anhang ([A-Z]) ·", title))
    ]
    if appendices != list("ABCD") or not all(1 <= p <= len(book) for _, _, p in toc):
        raise ValueError("Invalid appendix or bookmark destination.")
    targets = book.resolve_names()
    for page in book:
        for link in page.get_links():
            if link.get("kind") == 1 and not 0 <= link.get("page", -1) < len(book):
                raise ValueError(f"Invalid page link on page {page.number + 1}")
            name = link.get("nameddest")
            if name and (
                name not in targets or not 0 <= targets[name]["page"] < len(book)
            ):
                raise ValueError(f"Invalid PDF link on page {page.number + 1}: {name}")


def expected_attachments():
    material = compact.material_files()
    attachments = {
        p.name: p.read_bytes()
        for p in material
        if p.parent == MATERIAL and p.name != "START_HIER.txt"
    }
    for folder, name in (
        ("cp2_feldlabor", "CP2_Feldlabor.zip"),
        ("cp2_genauigkeit", "CP2_Genauigkeit.zip"),
    ):
        attachments[name] = compact.zip_bytes(
            [p for p in material if folder in p.relative_to(MATERIAL).parts]
        )
    attachments["QSS_Revisionsvergleich_v9_18.csv"] = (
        EDITION / COMPARISON
    ).read_bytes()
    attachments["QSS_Gegenprobe_c635504.csv"] = (
        EDITION / REPLAY / "skalenvergleich.csv"
    ).read_bytes()
    for name in ("qss-extension.csv", "rk23-devs.csv"):
        attachments["Archiv_" + name] = attachments.pop(name)
        attachments[name] = (EDITION / "daten" / name).read_bytes()
    attachments["QSS_Kontaktvergleich_v9_19.csv"] = (
        EDITION / CONTACT / "vergleich.csv"
    ).read_bytes()
    attachments["CP2_Vollgitter_v9_20.json"] = (
        EDITION / PDES / "vollgitter.json"
    ).read_bytes()
    return attachments


def verify_published_pdf(path, attachments):
    import pymupdf

    with pymupdf.open(path) as book:
        verify_navigation(book)
        names = book.embfile_names()
        if sorted(names) != sorted(attachments) or any(
            book.embfile_get(name) != data for name, data in attachments.items()
        ):
            raise ValueError("Invalid embedded lab files.")
        targets = book.resolve_names()
        for name, words in (
            ("druck-beleglegende", ("Beweis", "Gegenprobe", "Messung")),
            ("druck-c05-entscheidung", ("C05", "Aufwand", "BDF")),
        ):
            dest = targets.get(name)
            if dest is None or not 0 <= dest["page"] < len(book):
                raise ValueError(f"Missing teaching destination: {name}")
            page = book[dest["page"]].get_text()
            if not all(word in page for word in words):
                raise ValueError(f"Unexpected target page for {name}")


def publish_pdf(stage):
    import pymupdf

    attachments = expected_attachments()
    with pymupdf.open(stage / "text.pdf") as book:
        verify_navigation(book)
        if (
            book.metadata["author"] != "Christian Stenzel"
            or REVISION not in book.metadata["title"]
        ):
            raise ValueError("Unexpected title or author")
        for name, data in attachments.items():
            xref = book.embfile_add(
                name, data, filename=name, ufilename=name, desc=name
            )
            for field in ("CreationDate", "ModDate"):
                book.xref_set_key(xref, "Params/" + field, "(D:20261126000000Z)")
        book.save(stage / PDF, garbage=4, deflate=True, no_new_id=True)
    verify_published_pdf(stage / PDF, attachments)


def build(out):
    verify_measurements()
    out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=out) as tmp:
        stage = Path(tmp)
        typeset(stage)
        publish_pdf(stage)
        core_lab(stage / LAB)
        (stage / RECORD).write_text(
            json.dumps(distribution_record(stage), indent=2) + "\n", encoding="utf-8"
        )
        for name in (PDF, LAB, RECORD):
            (stage / name).replace(out / name)
    check(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="verify the publication without typesetting tools",
    )
    mode.add_argument(
        "--verify-pdf",
        action="store_true",
        help="verify published PDF navigation and embedded lab payloads (requires PyMuPDF)",
    )
    mode.add_argument(
        "--full-lab",
        type=Path,
        metavar="ZIP",
        help="assemble all programs, data and weights",
    )
    parser.add_argument("--output-dir", type=Path, default=DOCS)
    args = parser.parse_args()
    try:
        if args.full_lab:
            check(args.output_dir.resolve())
            full_lab(args.full_lab)
        elif args.verify_pdf:
            verify_published_pdf(
                args.output_dir.resolve() / PDF, expected_attachments()
            )
        elif args.check:
            check(args.output_dir.resolve())
        else:
            build(args.output_dir.resolve())
    except (
        OSError,
        ValueError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as exc:
        sys.exit(str(exc))


if __name__ == "__main__":
    main()
