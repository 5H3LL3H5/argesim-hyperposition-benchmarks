"""Generate and verify status tables derived from the canonical catalog."""

from __future__ import annotations

from pathlib import Path

from .catalog import BENCHMARKS


COVERAGE_START = "<!-- BEGIN GENERATED BENCHMARK STATUS -->"
COVERAGE_END = "<!-- END GENERATED BENCHMARK STATUS -->"


def benchmark_status_table() -> str:
    """Return the canonical Markdown benchmark status table."""

    lines = [
        "| ID | Official benchmark | Model family | Status |",
        "|---|---|---|---|",
    ]
    for entry in BENCHMARKS:
        lines.append(
            f"| {entry.identifier} | {entry.title} | {entry.coverage_family} | "
            f"{entry.status.value} |"
        )
    return "\n".join(lines)


def replace_generated_section(text: str, generated: str) -> str:
    """Replace the unique generated Markdown section, rejecting malformed markers."""

    if text.count(COVERAGE_START) != 1 or text.count(COVERAGE_END) != 1:
        raise ValueError("generated benchmark status markers must occur exactly once")
    start = text.find(COVERAGE_START)
    end = text.find(COVERAGE_END)
    if end < start:
        raise ValueError("generated benchmark status markers are missing or malformed")
    end += len(COVERAGE_END)
    return (
        text[:start]
        + COVERAGE_START
        + "\n"
        + generated.rstrip()
        + "\n"
        + COVERAGE_END
        + text[end:]
    )


def render_coverage_document(text: str) -> str:
    """Render the canonical catalog status table into ARGESIM_COVERAGE.md."""

    return replace_generated_section(text, benchmark_status_table())


def verify_coverage_document(path: Path) -> None:
    """Raise when the checked-in coverage table differs from the catalog."""

    text = path.read_text(encoding="utf-8")
    rendered = render_coverage_document(text)
    if rendered != text:
        raise AssertionError(
            "ARGESIM_COVERAGE.md benchmark status table is stale; "
            "regenerate it from argesim_benchmarks.catalog"
        )
