import unittest
from pathlib import Path

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus, benchmark
from argesim_benchmarks.status_docs import (
    COVERAGE_END,
    COVERAGE_START,
    replace_generated_section,
    verify_coverage_document,
)


class ArgesimCatalogTests(unittest.TestCase):
    def test_current_catalog_includes_c01_to_c22_and_parallel_cases(self) -> None:
        expected = {f"C{number:02d}" for number in range(1, 23)}
        expected.remove("C17")
        expected.remove("C19")
        expected.update(("C17R", "C19R", "CP1", "CP2"))

        identifiers = {entry.identifier for entry in BENCHMARKS}
        self.assertEqual(identifiers, expected)
        self.assertEqual(len(BENCHMARKS), 24)

    def test_implemented_benchmarks_status(self) -> None:
        statuses = {entry.identifier: entry.status for entry in BENCHMARKS}
        implemented = (
            "C01",
            "C03",
            "C04",
            "C09",
            "C10",
            "C12",
            "C06",
            "C07",
            "C11",
            "C13",
            "C14",
            "C15",
            "C16",
            "C17R",
            "C18",
            "C19R",
            "C20",
            "C22",
        )
        for identifier in implemented:
            self.assertEqual(statuses[identifier], BenchmarkStatus.IMPLEMENTED)
        self.assertEqual(statuses["C02"], BenchmarkStatus.VALIDATED)
        self.assertEqual(statuses["C08"], BenchmarkStatus.VALIDATED)
        self.assertEqual(statuses["C21"], BenchmarkStatus.VALIDATED)
        self.assertEqual(statuses["CP2"], BenchmarkStatus.VALIDATED)
        self.assertTrue(
            all(
                status is BenchmarkStatus.CATALOGED
                for identifier, status in statuses.items()
                if identifier not in implemented
                and identifier
                not in {"C02", "C05", "C08", "C21", "CP1", "CP2"}
            )
        )
        self.assertEqual(statuses["C05"], BenchmarkStatus.VALIDATED)
        self.assertEqual(statuses["CP1"], BenchmarkStatus.VALIDATED)

    def test_sources_are_official_and_lookup_is_strict(self) -> None:
        self.assertTrue(
            all(
                entry.primary_source.startswith("https://www.argesim.org/benchmarks/")
                for entry in BENCHMARKS
            )
        )
        self.assertEqual(benchmark("C22").title, "Non-standard Queuing Policies")
        with self.assertRaises(KeyError):
            benchmark("C17")

    def test_coverage_document_is_generated_from_catalog(self) -> None:
        root = Path(__file__).resolve().parents[1]
        verify_coverage_document(root / "ARGESIM_COVERAGE.md")

    def test_generated_section_rejects_bad_markers(self) -> None:
        valid = f"prefix\n{COVERAGE_START}\nold\n{COVERAGE_END}\nsuffix\n"
        self.assertEqual(
            replace_generated_section(valid, "new"),
            f"prefix\n{COVERAGE_START}\nnew\n{COVERAGE_END}\nsuffix\n",
        )
        malformed = (
            valid.replace(COVERAGE_START, ""),
            valid.replace(COVERAGE_END, ""),
            f"{COVERAGE_END}\n{COVERAGE_START}",
            valid + f"{COVERAGE_START}\nextra\n{COVERAGE_END}\n",
            valid.replace(COVERAGE_END, f"{COVERAGE_START}\n{COVERAGE_END}"),
        )
        for text in malformed:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    replace_generated_section(text, "new")

    def test_coverage_families_are_present(self) -> None:
        self.assertTrue(all(entry.coverage_family.strip() for entry in BENCHMARKS))


if __name__ == "__main__":
    unittest.main()
