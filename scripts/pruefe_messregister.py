"""Verify the measurement register against the full ZIP and the typeset PDF."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import re
import subprocess
import zipfile
from collections import Counter
from functools import cache
from itertools import product
from pathlib import Path
from typing import NoReturn

REGISTER = "daten/messregister.csv"
MATRIX_INDEX = "daten/qss-matrix-ausgaben.csv"
KEY = "Studien- oder Tabellenkennung"
SOURCE = "Datei ab Paketwurzel"
HASH = "SHA-256"
PAGE = "Physische PDF-Seite"
EDITION = "PDF-Ausgabe"
ARCHIVE = "Archivfundstelle"
OLD_PAGE = "Druckseite v9.17"
CASE_ORDER = ("C03", "C05", "C07", "C09", "C11", "C12", "C13", "C21")
QUANTA = ("0.005", "0.001", "0.0002")
CLASSIC = ("euler", "rk4", "rk45")
QSS = (
    "qss1",
    "qss2",
    "qss3",
    "qss4",
    "cqss1",
    "liqss1",
    "liqss2",
    "liqss3",
    "mliqss1",
    "mliqss2",
    "mliqss3",
    "eliqss1",
    "eliqss2",
    "eliqss3",
    "cheqss1",
    "cheqss2",
    "cheqss3",
    "liqss-bdf",
)
STATUS = {
    "pass": "B",
    "accuracy_miss": "G",
    "timeout": "T",
    "event_mismatch": "E",
    "solver_error": "F",
}
QSS_LAB = "rechenlabor/qss_pruefung"
CURRENT = f"{QSS_LAB}/messung/kontakt_v919/extension.csv"
MATRIX_COUNTS = {
    f"{QSS_LAB}/vorher/qss-extension.csv": 222,
    f"{QSS_LAB}/messung/extension.csv": 209,
    f"{QSS_LAB}/messung/skalenfix_c635504/extension.csv": 227,
    CURRENT: 224,
}
SCORE = r"[BGTEF](?:\s*-?\d+(?:,\d+)?(?:e[+-]?\d+)?)?"


def invalid(message: str) -> NoReturn:
    raise ValueError(message)


def csv_rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8"), newline="")))


def pdf_destinations(pdf: Path) -> dict[str, int]:
    """Return physical, 1-based page numbers of PDF named destinations."""
    report = subprocess.check_output(["pdfinfo", "-dests", pdf], text=True)
    result: dict[str, int] = {}
    for line in report.splitlines():
        if match := re.fullmatch(r'\s*(\d+)\s+\[.*?\]\s+"([^"]+)"\s*', line):
            name = match[2]
            page = int(match[1])
            if name in result and result[name] != page:
                invalid(f"Mehrdeutiges PDF-Ziel: {name}")
            result[name] = page
    return result


def score_label(row: dict[str, str]) -> str:
    label = STATUS[row["status"]]
    if score := row["error_over_limit"]:
        # Three significant figures; suppress a leading zero in the exponent.
        display = format(float(score), ".3g").replace(".", ",")
        label += re.sub(r"e([+-])0+(\d+)", r"e\1\2", display)
    return label


def verify_matrix(pdf: Path, dests: dict[str, int], lab: zipfile.ZipFile) -> None:
    """Compare all printed summaries and all rounded Appendix B.1 cells."""
    sources = csv_rows(lab.read(MATRIX_INDEX))
    if (
        len(sources) != len(MATRIX_COUNTS)
        or {row[SOURCE]: int(row["Bestanden"]) for row in sources} != MATRIX_COUNTS
    ):
        invalid("Die vier Messausgaben sind nicht eindeutig.")
    expected = set(product(CASE_ORDER, QSS, QUANTA)) | set(
        product(CASE_ORDER, CLASSIC, ("",))
    )
    current: dict[tuple[str, str, str], dict[str, str]] = {}
    for record in sources:
        path = record[SOURCE]
        data = lab.read(path)
        rows = csv_rows(data)
        runs = {(r["case"], r["method"], r["quantum_factor"]): r for r in rows}
        if (
            len(rows) != 456
            or int(record["Zeilen"]) != len(rows)
            or set(runs) != expected
            or sum(r["status"] == "pass" for r in rows) != int(record["Bestanden"])
            or hashlib.sha256(data).hexdigest() != record[HASH]
        ):
            invalid(f"Ungültiger Messstand: {path}")
        if path == CURRENT:
            current = runs
    if not current or lab.read(CURRENT) != lab.read("daten/qss-extension.csv"):
        invalid(
            "Aktuelle Primärdatei stimmt nicht mit der veröffentlichten CSV überein."
        )
    primary = Path(CURRENT).parent
    if any(
        str(primary / (name + ".csv")) not in lab.namelist()
        for name in ("baseline", "extension", "selection", "rk23")
    ):
        invalid("Eine der vier aktuellen Primärdateien fehlt im Labor.")

    @cache
    def page_text(page: int) -> str:
        return subprocess.check_output(
            ["pdftotext", "-f", str(page), "-l", str(page), "-layout", pdf, "-"],
            text=True,
        ).replace("−", "-")

    totals: Counter[tuple[str, str]] = Counter(
        key[:2] for key, row in current.items() if row["status"] == "pass"
    )
    matrix_page = dests["tab-k18-06"]
    matrix = page_text(matrix_page) + page_text(matrix_page + 1)
    lines = re.findall(r"^\s*([a-z0-9-]+)\s+([0-3](?:\s+[0-3]){7})\s*$", matrix, re.M)
    actual_totals = {
        (case, method): int(cell)
        for method, cells in lines
        for case, cell in zip(CASE_ORDER, cells.split())
        if method in QSS + CLASSIC
    }
    if len([name for name, _ in lines if name in QSS + CLASSIC]) != 21:
        invalid(
            "Die 21 gedruckten Zeilen der Acht-Fälle-Matrix fehlen oder sind doppelt."
        )
    for k in product(CASE_ORDER, QSS + CLASSIC):
        if actual_totals.get(k) != totals[k]:
            invalid(f"Matrixzelle stimmt nicht: {k}, Soll {totals[k]}.")

    for index, case in enumerate(CASE_ORDER, 1):
        text = page_text(dests[f"tab-ab-{index:02}"])
        pattern = rf"^\s*([A-Z0-9-]+)\s+({SCORE})\s+({SCORE})\s+({SCORE})\s*$"
        measurements = {}
        for method, *labels in re.findall(pattern, text, re.M):
            if method.lower() in QSS:
                for q, label in zip(QUANTA, labels):
                    measurements[(case, method.lower(), q)] = re.sub(r"\s+", "", label)
        for method in CLASSIC:
            match = re.search(rf"\b{method.upper()}\s+({SCORE})(?:[.,]|\s)", text)
            if match:
                measurements[(case, method, "")] = re.sub(r"\s+", "", match[1])
        if len(measurements) != 57:
            invalid(f"{case}: {len(measurements)}/57 PDF-Werte ausgelesen.")
        for key, printed in measurements.items():
            if printed != (expected_label := score_label(current[key])):
                invalid(
                    f"Einzelwert stimmt nicht: {key}: {printed}, Soll {expected_label}."
                )


def process(pdf: Path, lab_path: Path, edition: str, update: Path | None) -> tuple[int, int]:
    report = subprocess.check_output(["pdfinfo", pdf], text=True)
    title = re.search(r"^Title:\s*(.+)$", report, re.M)
    if not title or not re.search(rf"(?<!\w){re.escape(edition)}(?![\w.])", title[1]):
        invalid(f"PDF-Titel enthält nicht die angegebene Ausgabe {edition}.")
    destinations = pdf_destinations(pdf)
    with zipfile.ZipFile(lab_path) as lab:
        original = lab.read(REGISTER)
        rows = csv_rows(original)
        ids = {row[KEY] for row in rows}
        tables = {key for key in ids if key.startswith("tab-")}
        modal_ids = {f"tab-modal-{i:02d}" for i in range(1, 14)} if "druck-modal-studie" in destinations else set()
        if {key for key in ids if key.startswith("tab-modal-")} != modal_ids:
            invalid("Die dreizehn Tabellen des Modaloperatorlabors und seine Druckfassung stimmen nicht überein.")
        if (len(rows), len(ids), len(tables)) != (104 + len(modal_ids), 104 + len(modal_ids), 80 + len(modal_ids)):
            invalid("Anzahl der eindeutigen Nachweise oder PDF-Tabellenziele stimmt nicht.")
        verify_matrix(pdf, destinations, lab)
        digests: dict[str, str] = {}
        for row in rows:
            key, path = row[KEY], row[SOURCE]
            if path not in digests:
                digests[path] = hashlib.sha256(lab.read(path)).hexdigest()
            if key in tables:
                if key not in destinations:
                    invalid(f"Fehlendes PDF-Tabellenziel: {key}")
                page, label, archived = str(destinations[key]), edition, ""
            else:
                legacy = row.get(OLD_PAGE) or row.get(ARCHIVE)
                if not legacy or not (
                    legacy.isdecimal()
                    or re.fullmatch(
                        r"v9\.17, Druckseite [1-9]\d* \(historische Registerfundstelle\)",
                        legacy,
                    )
                ):
                    invalid(f"Fehlende oder uneindeutige Archivfundstelle: {key}")
                page, label = "", ""
                archived = (
                    f"v9.17, Druckseite {legacy} (historische Registerfundstelle)"
                    if legacy.isdecimal()
                    else legacy
                )
            values = {
                HASH: digests[path],
                PAGE: page,
                EDITION: label,
                ARCHIVE: archived,
            }
            for field, value in values.items():
                if update is None and row.get(field) != value:
                    invalid(f"{key}: {field} stimmt nicht mit PDF oder Labor überein.")
                row[field] = value
        if update is not None:
            if update.read_bytes() != original:
                invalid(
                    "Die zu aktualisierende Registerdatei ist nicht die Version im ZIP."
                )
            fieldnames = [name for name in rows[0] if name != OLD_PAGE]
            with update.open("w", encoding="utf-8", newline="") as fp:
                writer = csv.DictWriter(
                    fp,
                    fieldnames=fieldnames,
                    extrasaction="ignore",
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)
    return len(rows), len(tables)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf", type=Path, required=True)
    parser.add_argument("--lab", type=Path, required=True)
    parser.add_argument(
        "--edition", required=True, help="Ausgabe der übergebenen PDF, z. B. v9.21"
    )
    parser.add_argument(
        "--update",
        type=Path,
        help="Quellregister durch PDF-/ZIP-Nachweis aktualisieren",
    )
    args = parser.parse_args()
    try:
        records, tables = process(args.pdf, args.lab, args.edition, args.update)
    except (
        ValueError,
        KeyError,
        OSError,
        subprocess.CalledProcessError,
        zipfile.BadZipFile,
    ) as exc:
        parser.exit(1, f"{exc}\n")
    print(
        f"{records} Registerzeilen, {tables} PDF-Tabellenziele, 24 Archivfundstellen, 168 Matrixzellen, 456 Einzelwerte geprüft."
    )


if __name__ == "__main__":
    main()
