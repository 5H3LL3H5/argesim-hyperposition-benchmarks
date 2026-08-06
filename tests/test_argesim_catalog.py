import unittest

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus, benchmark


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
        implemented = ("C01", "C06", "C13", "C19R", "C22", "CP1")
        for identifier in implemented:
            self.assertEqual(statuses[identifier], BenchmarkStatus.IMPLEMENTED)
        self.assertTrue(
            all(
                status is BenchmarkStatus.CATALOGED
                for identifier, status in statuses.items()
                if identifier not in implemented
            )
        )

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


if __name__ == "__main__":
    unittest.main()
