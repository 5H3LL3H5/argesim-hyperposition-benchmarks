#!/usr/bin/env python3
"""Regenerate generated status sections from the canonical catalog."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from argesim_benchmarks.status_docs import render_coverage_document

COVERAGE = ROOT / "ARGESIM_COVERAGE.md"


def main() -> None:
    text = COVERAGE.read_text(encoding="utf-8")
    rendered = render_coverage_document(text)
    COVERAGE.write_text(rendered, encoding="utf-8")


if __name__ == "__main__":
    main()
