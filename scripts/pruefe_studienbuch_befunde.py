"""Check findings against the exact textbook edition in a Git checkout."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import runpy
import subprocess
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, replace
from fractions import Fraction
from hashlib import sha256
from pathlib import Path
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
PDF = "docs/ARGESIM_SOLVER_STUDY.pdf"
MANIFEST = "docs/ARGESIM_Buchstand.json"
ARCHIVES = "docs/ARGESIM_Review_Archivindex.csv"
REVIEW_NOTES = "docs/reviews/v922-csv"
EDITION = "docs/lehrbuch/gesamtausgabe"
LAB = f"{EDITION}/pakete/Laborquellen.zip"
CODANO = f"{EDITION}/rechenlabor/codano"
GITHUB = "https://github.com/5H3LL3H5/argesim-hyperposition-benchmarks"
ARCHIVE_PATHS = {
    "Hauptbuch": PDF,
    "Anlage": "docs/lehrbuch/studienbuch/material/Studienanhang_Archiv.pdf",
}
COMMIT = re.compile(r"[a-f0-9]{40}")
FINDING = re.compile(r"[A-Z][A-Z0-9-]+")
INPUTS = (
    PDF,
    MANIFEST,
    ARCHIVES,
    REVIEW_NOTES,
    EDITION,
    "docs/ARGESIM_Bachelor_Rechenlabor.zip",
    "docs/lehrbuch/studienbuch",
    "scripts/build_studienbuch.py",
    "scripts/build_studienbuch_kompakt.py",
    "scripts/pruefe_studienbuch_befunde.py",
    "argesim_benchmarks/solvers",
)


@dataclass(frozen=True)
class Result:
    id: str
    outcome: str
    criterion: str
    path: str
    evidence: tuple[str, ...] = ()
    pdf_page: int | None = None
    kind: str = "test"
    review_status: str | None = None


def git(root: Path, *args: str) -> bytes:
    try:
        return subprocess.run(
            ("git", *args), cwd=root, capture_output=True, check=True
        ).stdout
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode("utf-8", errors="replace").strip()
        raise ValueError(f"Git {' '.join(args)}: {detail or exc.returncode}") from exc


def checkout_commit(root: Path, expected: str | None) -> str:
    commit = git(root, "rev-parse", "HEAD").decode("ascii").strip()
    if expected is not None and expected != commit:
        raise ValueError(f"Prüf-Commit {expected} erwartet, Checkout ist {commit}.")
    if git(root, "status", "--porcelain", "--untracked-files=normal", "--", *INPUTS):
        raise ValueError(
            "Bucheingaben, Prüfquellen oder Ausgaben im Checkout sind geändert."
        )
    return commit


def git_blob(root: Path, commit: str, path: str) -> bytes | None:
    if not COMMIT.fullmatch(commit):
        raise ValueError(f"Ungültige Git-Revision: {commit}")
    if git(root, "cat-file", "-t", commit).strip() != b"commit":
        raise ValueError(f"{commit} ist kein Commit.")
    if not git(root, "ls-tree", "--full-tree", commit, "--", path):
        return None
    return git(root, "cat-file", "blob", f"{commit}:{path}")


def csv_entries(path: Path, separator: str, id_column: str, columns: set[str]):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream, delimiter=separator, strict=True)
        fields = reader.fieldnames or []
        if len(fields) != len(set(fields)) or not columns | {id_column} <= set(fields):
            raise ValueError(f"Fehlende oder doppelte Spalten in {path.name}.")
        entries = {}
        for row in reader:
            ident = row.get(id_column)
            if (
                None in row
                or None in row.values()
                or not ident
                or not FINDING.fullmatch(ident)
                or ident in entries
            ):
                raise ValueError(
                    f"Ungültige oder doppelte ID in {path.name}: {ident!r}"
                )
            entries[ident] = row
        if not entries:
            raise ValueError(f"Keine Befund-IDs in {path.name}.")
        return entries


def check_brent(root: Path) -> tuple[str, ...]:
    with ZipFile(root / LAB) as lab, tempfile.TemporaryDirectory() as directory:
        path = lab.extract("beispiele/ereignis.py", directory)
        module = runpy.run_path(path)
        brent = module["brent"]
        bracket = module["EventBracket"]
        failures = []
        for direction in (1, -1):
            bound = 2.0**-54
            exact = Fraction(-direction, 2**55)
            left, right = (-bound, 2.0) if direction == 1 else (-2.0, bound)

            def residual(t):
                return float(Fraction(t) - exact)

            result = brent(residual, left, right, 1.0)
            if isinstance(result, bracket):
                if (
                    result.diagnosis != "time_resolution"
                    or not left <= result.left <= exact <= result.right <= right
                    or math.nextafter(result.left, math.inf) != result.right
                    or (result.left_value, result.right_value)
                    != (residual(result.left), residual(result.right))
                    or result.left_value * result.right_value >= 0
                ):
                    failures.append(
                        f"Probe {direction:+d} mit ungültiger Vorzeichenklammer."
                    )
            elif not math.isfinite(result):
                failures.append(f"Probe {direction:+d} mit nicht endlicher Rückgabe.")
            else:
                excess = abs(Fraction(result) - exact) - 1
                if excess > 0:
                    failures.append(
                        f"Probe {direction:+d} überschreitet xtol um {excess}."
                    )
        return tuple(failures)


def attachment_keys(node, visited: set[int]) -> list[bytes]:
    node = node.get_object()
    if id(node) in visited:
        raise ValueError("Namensbaum mit wiederholtem Knoten.")
    visited.add(id(node))
    if "/Kids" in node and "/Names" not in node:
        return [
            name for child in node["/Kids"] for name in attachment_keys(child, visited)
        ]
    if "/Names" not in node or "/Kids" in node or len(node["/Names"]) % 2:
        raise ValueError("Ungültiges Blatt im Namensbaum.")
    return [
        bytes(key) if isinstance(key, bytes) else key.original_bytes
        for key in node["/Names"][::2]
    ]


def check_pdf_names(book) -> tuple[str, ...]:
    try:
        node = book.trailer["/Root"]["/Names"]["/EmbeddedFiles"]
        keys = attachment_keys(node, set())
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        return (f"Anlagen-Namensbaum nicht lesbar: {exc}",)
    if not keys:
        return ("Der Anlagen-Namensbaum enthält keine Einträge.",)
    inversions = sum(left >= right for left, right in zip(keys, keys[1:]))
    if inversions:
        return (
            f"{len(keys)} Schlüssel, davon {inversions} nicht aufsteigende Nachbarpaare.",
        )
    return ()


def check_measurement_sources(root: Path) -> tuple[str, ...]:
    failures = []
    for filename, script in (
        ("saite_tfno_messung.json", "saite_tfno.py"),
        ("messung.json", "austausch.py"),
        ("messung_kapazitaet.json", "austausch.py"),
    ):
        data = json.loads((root / CODANO / filename).read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            failures.append(f"{filename} enthält kein JSON-Objekt.")
            continue
        commit = data.get("source_commit")
        if not isinstance(commit, str) or not COMMIT.fullmatch(commit):
            failures.append(f"{filename} hat keinen vollständigen source_commit.")
            continue
        content = git_blob(root, commit, f"{CODANO}/{script}")
        if content is None:
            failures.append(f"{filename} nennt {commit[:8]}, dort fehlt {script}.")
        elif data.get("source_script_sha256") != sha256(content).hexdigest():
            failures.append(f"{filename} hat keinen passenden source_script_sha256.")
    return tuple(failures)


def book_pages(book) -> dict[str, int]:
    """Derive physical page numbers from unique PDF outline titles."""
    hits: dict[str, list[int]] = {}
    stack = list(book.outline)
    while stack:
        entry = stack.pop()
        if isinstance(entry, list):
            stack.extend(entry)
        else:
            page = book.get_destination_page_number(entry)
            if page is not None and page >= 0:
                hits.setdefault(str(entry.title), []).append(page + 1)
    return {title: pages[0] for title, pages in hits.items() if len(pages) == 1}


def finding_checks(root: Path, book) -> list[Result]:
    pages = book_pages(book)
    checks = (
        (
            "R90-K-01",
            "Exakte Brent-Toleranz in beiden Rundungsrichtungen",
            LAB,
            "Wie Brent die Klammer schließt",
            "Beide exakten Gegenproben sind erfüllt.",
            lambda: check_brent(root),
        ),
        (
            "R90-PDF-01",
            "Streng aufsteigende PDF-Anlagenschlüssel",
            PDF,
            "Rechenlabor zur Gesamtausgabe",
            "Alle Anlagenschlüssel sind streng aufsteigend.",
            lambda: check_pdf_names(book),
        ),
        (
            "R91-LAB-01",
            "Quell-Commit und Skript-Hash der Operator-Messdateien",
            CODANO,
            "9.43 · Was bleibt bei ähnlicher Modellgröße?",
            "Die drei Messdateien verweisen auf vorhandene Skripte mit identischem Hash.",
            lambda: check_measurement_sources(root),
        ),
    )
    results = []
    for ident, criterion, path, title, passed, check in checks:
        try:
            problems = check()
            result = Result(
                ident,
                "fail" if problems else "pass",
                criterion,
                path,
                problems or (passed,),
            )
        except (ArithmeticError, OSError, ValueError, KeyError, BadZipFile) as exc:
            result = Result(ident, "error", criterion, path, (str(exc),))
        results.append(replace(result, pdf_page=pages.get(title)))
    return results


def archive_entries(root: Path, read_pdf) -> list[Result]:
    rows = csv_entries(
        root / ARCHIVES,
        ",",
        "id",
        {
            "status",
            "aktuelle_seite",
            "ausgabe",
            "seitenart",
            "archivseiten",
            "archivlinks",
        },
    )
    page_counts: dict[tuple[str, str], int | None] = {}
    results = []
    for ident, row in rows.items():
        path = ARCHIVE_PATHS.get(row["seitenart"])
        commit = row["ausgabe"]
        result = Result(
            ident,
            "pass",
            "Archivfundstelle",
            ARCHIVES,
            kind="archive",
            review_status=row["status"],
        )
        pages = [page.strip() for page in row["archivseiten"].split(",")]
        try:
            if (
                not path
                or not COMMIT.fullmatch(commit)
                or row["status"] not in {"Entfallen", "Nur Archiv"}
                or row["aktuelle_seite"]
                or any(not re.fullmatch(r"[1-9][0-9]*", p) for p in pages)
                or len(pages) != len(set(pages))
            ):
                results.append(
                    replace(
                        result, outcome="fail", evidence=("Ungültige Archivdaten.",)
                    )
                )
                continue
            links = tuple(
                f"{GITHUB}/blob/{commit}/{path}?raw=true#page={p}" for p in pages
            )
            if set(row["archivlinks"].split()) != set(links):
                results.append(
                    replace(
                        result,
                        outcome="fail",
                        evidence=(
                            "Archivlinks weichen von Commit, Pfad oder Seiten ab.",
                        ),
                    )
                )
                continue
            key = (commit, path)
            if key not in page_counts:
                data = git_blob(root, commit, path)
                page_counts[key] = (
                    len(read_pdf(io.BytesIO(data)).pages) if data is not None else None
                )
            count = page_counts[key]
            if count is None or any(int(page) > count for page in pages):
                results.append(
                    replace(
                        result,
                        outcome="fail",
                        evidence=("Archiv-PDF oder angegebene Seite fehlt.", *links),
                    )
                )
                continue
            results.append(replace(result, evidence=links))
        except (OSError, ValueError) as exc:
            results.append(replace(result, outcome="error", evidence=(str(exc),)))
    return results


def coverage(
    root: Path, worklist: Path | None, commit: str
) -> tuple[str, dict[str, Result]]:
    if worklist is None:
        return commit, {
            path.stem: Result(
                path.stem,
                "manual",
                "Fachlicher Einzelbeleg",
                path.relative_to(root).as_posix(),
                kind="manual",
            )
            for path in sorted((root / REVIEW_NOTES).glob("*.md"))
            if FINDING.fullmatch(path.stem)
        }
    rows = csv_entries(worklist, ";", "ID", {"Ausgabe"})
    revisions = {row["Ausgabe"] for row in rows.values()}
    if len(revisions) != 1 or not re.fullmatch(
        r"[a-f0-9]{8}|[a-f0-9]{40}", next(iter(revisions))
    ):
        raise ValueError(
            "Die Arbeitsliste muss genau eine hexadezimale Ausgabe bezeichnen."
        )
    revision = (
        git(root, "rev-parse", "--verify", f"{next(iter(revisions))}^{{commit}}")
        .decode("ascii")
        .strip()
    )
    git(root, "merge-base", "--is-ancestor", revision, commit)
    return revision, {
        ident: Result(
            ident,
            "manual",
            "Kein automatisches Abnahmekriterium registriert",
            "",
            kind="manual",
            review_status=row.get("Aussageart / Delta") or None,
        )
        for ident, row in rows.items()
    }


def run_audit(
    root: Path, expected: str | None, worklist: Path | None, read_pdf
) -> dict:
    commit = checkout_commit(root, expected)
    subprocess.run(
        [sys.executable, str(root / "scripts/build_studienbuch.py"), "--check"],
        cwd=root,
        check=True,
    )
    manifest = json.loads((root / MANIFEST).read_text(encoding="utf-8"))
    source_revision, results = coverage(root, worklist, commit)
    book = read_pdf(root / PDF)
    for result in (*finding_checks(root, book), *archive_entries(root, read_pdf)):
        previous = results.get(result.id)
        if previous is not None:
            if previous.kind != "manual":
                raise ValueError(f"Befund doppelt registriert: {result.id}")
            if result.review_status is None:
                result = replace(result, review_status=previous.review_status)
        results[result.id] = result
    checkout_commit(root, commit)
    counts = Counter(result.outcome for result in results.values())
    return {
        "schema_version": 1,
        "commit": commit,
        "edition": manifest["edition"],
        "pdf_path": PDF,
        "pdf_sha256": manifest["outputs_sha256"][Path(PDF).name],
        "coverage_source": "arbeitsliste" if worklist is not None else "repository",
        "coverage_revision": source_revision,
        "counts": {
            state: counts[state] for state in ("pass", "fail", "error", "manual")
        },
        "results": [asdict(results[ident]) for ident in sorted(results)],
    }


def exit_status(report: dict, strict: bool) -> int:
    counts = report["counts"]
    if counts["error"]:
        return 2
    return int(strict and bool(counts["fail"]))


def write_report(report: dict, output: Path | None) -> None:
    data = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if output is None:
        print(data, end="")
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=output.parent) as directory:
        staged = Path(directory) / output.name
        staged.write_text(data, encoding="utf-8")
        staged.replace(output)
    counts = report["counts"]
    print(f"### Lehrbuchbefunde · `{report['commit'][:8]}`\n")
    archived = sum(
        item["kind"] == "archive" and item["outcome"] == "pass"
        for item in report["results"]
    )
    print(
        f"{counts['pass']} bestanden · {counts['fail']} fehlgeschlagen · "
        f"{counts['error']} Prüffehler · {counts['manual']} fachliche Belege\n"
    )
    print(f"Bestätigte Archivfundstellen: {archived}\n")
    for result in report["results"]:
        if result["outcome"] in {"fail", "error"}:
            evidence = " ".join(result["evidence"])
            print(f"- `{result['id']}` · {result['criterion']}. {evidence}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--expected-commit", help="Prüfung auf diesen vollständigen Git-SHA begrenzen"
    )
    parser.add_argument(
        "--arbeitsliste", type=Path, help="Optionale lokale CSV mit Altbefund-IDs"
    )
    parser.add_argument(
        "--output", type=Path, help="JSON-Bericht in diese Datei schreiben"
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exitcode 1 bei fehlgeschlagenem Abnahmetest",
    )
    args = parser.parse_args()
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError:
        print("Für die Befundprüfung wird pypdf benötigt.", file=sys.stderr)
        return 2
    try:
        report = run_audit(ROOT, args.expected_commit, args.arbeitsliste, PdfReader)
        write_report(report, args.output)
    except (
        OSError,
        ValueError,
        KeyError,
        csv.Error,
        PdfReadError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"Befundprüfung abgebrochen: {exc}", file=sys.stderr)
        return 2
    return exit_status(report, args.strict)


if __name__ == "__main__":
    sys.exit(main())
