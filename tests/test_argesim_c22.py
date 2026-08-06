import unittest

from argesim_benchmarks.models import (
    c22_basic,
    c22_classing,
    c22_jockeying,
    c22_reneging,
)


class C22Tests(unittest.TestCase):
    def test_c22_basic_runs_without_errors(self) -> None:
        results = c22_basic()
        self.assertIn("deterministic", results)
        self.assertIn("stochastic", results)
        self.assertEqual(len(results["deterministic"]["ids_out"]), 20)

        # Verify large stoch model
        self.assertGreater(results["stochastic_large"]["lqt_max"], 0)

    def test_c22_jockeying_has_events(self) -> None:
        results = c22_jockeying()

        # In jockeying, deterministic might have a small number of events or 0
        # depending on exact event timings, but we expect the dicts to have the key
        self.assertIn("jockey_events", results["deterministic"])
        self.assertIn("jockey_table", results["deterministic"])
        self.assertIn("jockey_events", results["stochastic"])

    def test_c22_reneging_has_events(self) -> None:
        results = c22_reneging()

        self.assertIn("renege_events", results["deterministic"])
        self.assertIn("renege_table", results["deterministic"])
        self.assertIn("renege_events", results["stochastic"])

    def test_c22_classing_runs(self) -> None:
        results = c22_classing()

        self.assertIn("class_stats", results["deterministic"])
        self.assertIn("class_stats", results["stochastic"])

        det_stats = results["deterministic"]["class_stats"]
        self.assertEqual(len(det_stats), 5)

        # Classes should have non-negative avg wait times
        for c in range(1, 6):
            self.assertGreaterEqual(det_stats[c]["avg"], 0.0)


if __name__ == "__main__":
    unittest.main()
