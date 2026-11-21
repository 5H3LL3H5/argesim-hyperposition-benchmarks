import unittest
from pathlib import Path
from unittest.mock import patch

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus, benchmark
from argesim_benchmarks.runner import CONTRACTS, BenchmarkTask
from argesim_benchmarks.status_docs import (
    COVERAGE_END,
    COVERAGE_START,
    SCOPE_END,
    SCOPE_START,
    executable_scope_table,
    render_coverage_document,
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

    def test_benchmark_status_reflects_remaining_definition_gaps(self) -> None:
        expected_groups = {
            BenchmarkStatus.SPECIFIED: {"C18"},
            BenchmarkStatus.IMPLEMENTED: {
                "C02", "C04", "C09", "C10", "C11", "C14", "C19R", "C20",
            },
            BenchmarkStatus.VALIDATED: {
                "C01", "C03", "C05", "C06", "C07", "C08", "C12", "C15", "C16",
                "C13", "C17R", "C21", "C22", "CP1", "CP2",
            },
        }
        expected = {
            identifier: status
            for status, identifiers in expected_groups.items()
            for identifier in identifiers
        }
        self.assertEqual({entry.identifier: entry.status for entry in BENCHMARKS}, expected)

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

    def test_scope_lists_every_registered_task_once_in_its_family(self):
        rows = [line.split("|")[1:3] for line in executable_scope_table().splitlines()[2:]]
        expected = [(identifier, ", ".join(f"`{task}`" for task in case.tasks))
                    for identifier, case in CONTRACTS.items()]
        self.assertEqual([(family.strip(), tasks.strip()) for family, tasks in rows], expected)
        document = (Path(__file__).resolve().parents[1] / "ARGESIM_COVERAGE.md").read_text()
        with patch.dict(CONTRACTS["C01"].tasks, {"new-task": BenchmarkTask("new-task", "")}):
            updated = render_coverage_document(document)
            self.assertNotEqual(updated, document)
            self.assertIn("`new-task`", updated)
            self.assertEqual(render_coverage_document(updated), updated)
        for marker in (SCOPE_START, SCOPE_END):
            with self.subTest(marker=marker), self.assertRaises(ValueError):
                render_coverage_document(document.replace(marker, ""))

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
            with self.subTest(text=text), self.assertRaises(ValueError):
                replace_generated_section(text, "new")

    def test_coverage_families_are_present(self) -> None:
        self.assertTrue(all(entry.coverage_family.strip() for entry in BENCHMARKS))


if __name__ == "__main__":
    unittest.main()
