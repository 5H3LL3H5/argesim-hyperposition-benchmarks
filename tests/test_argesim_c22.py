import itertools
import unittest

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus
from argesim_benchmarks.models import (
    c22_basic,
    c22_classing,
    c22_jockeying,
    c22_reneging,
)
from argesim_benchmarks.models.c22_queuing_policies import ClassingSystem


class C22Tests(unittest.TestCase):
    def test_c22_catalog_status(self) -> None:
        c22 = next(b for b in BENCHMARKS if b.identifier == "C22")
        self.assertEqual(c22.status, BenchmarkStatus.VALIDATED)

    def test_c22_basic_runs_without_errors(self) -> None:
        results = c22_basic()
        self.assertIn("deterministic", results)
        self.assertIn("stochastic", results)
        self.assertEqual(len(results["deterministic"]["ids_out"]), 20)
        self.assertEqual(results["deterministic"]["first_arrival_time"], 1.0)
        self.assertEqual(results["deterministic"]["entities_created"], 100)
        self.assertEqual(results["deterministic"]["entities_terminated"], 100)
        self.assertEqual(results["deterministic"]["active_entities"], 0)
        trace = results["deterministic"]["lqt_trace"]
        self.assertEqual(trace[0], (0.0, 0))
        self.assertEqual(trace[-1][1], 0)
        self.assertTrue(all(a[0] <= b[0] for a, b in itertools.pairwise(trace)))
        self.assertGreater(max(length for _, length in trace), 0)
        integral = sum(
            length * (next_time - time)
            for (time, length), (next_time, _) in itertools.pairwise(trace)
        )
        self.assertAlmostEqual(
            integral / results["deterministic"]["times_out"][-1],
            results["deterministic"]["lqt_avg"],
        )
        # Structural check against expected bounds
        self.assertAlmostEqual(results["deterministic"]["tq_avg"], 6.7, places=1)
        self.assertAlmostEqual(results["deterministic"]["tq_max"], 13.5, places=1)

        # Verify large stoch model
        self.assertGreater(results["stochastic_large"]["lqt_max"], 0)

    def test_c22_jockeying_has_events(self) -> None:
        results = c22_jockeying()

        # Junglas & Pawletta, MatlabGPSS C22, Table 3 (time, ID, source, destination).
        self.assertEqual(results["deterministic"]["jockey_table"], [
            (6.5, 6, 1, 2), (7.5, 7, 1, 3), (8.5, 8, 1, 4),
            (11, 10, 1, 2), (12, 11, 1, 3), (89.5, 89, 2, 4),
            (93, 92, 2, 3), (94, 93, 2, 4), (98.5, 98, 3, 4), (103, 100, 1, 4),
        ])
        self.assertIn("jockey_events", results["deterministic"])
        self.assertIn("jockey_table", results["deterministic"])
        self.assertIn("jockey_events", results["stochastic"])
        # Check standard deterministic trace properties
        self.assertGreaterEqual(results["stochastic"]["jockey_events"], 100)

    def test_c22_reneging_has_events(self) -> None:
        results = c22_reneging()

        self.assertIn("renege_events", results["deterministic"])
        # Table 5 lists every deterministic abandonment (time, ID).
        self.assertEqual(results["deterministic"]["renege_table"],
                         [(77, 68), (86, 77), (95, 86), (104, 95)])
        self.assertIn("renege_events", results["stochastic"])
        self.assertEqual(results["deterministic"]["tq_max"], 9.0)
        self.assertEqual(results["deterministic"]["active_entities"], 0)
        self.assertEqual(results["deterministic"]["entities_terminated"], 100)
        self.assertEqual(len(results["deterministic"]["ids_out"]), 20)
        self.assertEqual(len(set(results["deterministic"]["ids_out"])), 20)

    def test_c22_classing_runs(self) -> None:
        results = c22_classing()

        self.assertIn("class_stats", results["deterministic"])
        self.assertIn("class_stats", results["stochastic"])

        det_stats = results["deterministic"]["class_stats"]
        self.assertEqual(len(det_stats), 5)
        self.assertEqual(results["deterministic"]["first_arrival_time"], 1.0)
        self.assertEqual(results["deterministic"]["active_entities"], 0)

        # Table 7 prints means to two decimal places, with different
        # roundings at an exact half-cent for classes four and five.
        means = (66.80, 60.85, 41.85, 50.98, 60.77)
        maxima = (121.50, 104.00, 77.00, 120.00, 125.50)
        for c, (avg, maximum) in enumerate(zip(means, maxima), start=1):
            self.assertAlmostEqual(det_stats[c]["avg"], avg, delta=0.0050000001)
            self.assertEqual(det_stats[c]["max"], maximum)

    def test_c22_deterministic_classes_ascend_before_first_operator_call(self) -> None:
        # C22 §4: assignment starts at 1; calls start at 5 after t=10.
        system = ClassingSystem("classing")
        from argesim_benchmarks.models.c22_queuing_policies import DevsSimulator

        simulator = DevsSimulator(system)
        simulator.scheduler.run(9.0)
        assigned = {entity.id: entity.entity_class for queue in system.queues for entity in queue}
        self.assertEqual([assigned[i] for i in range(1, 10)], [1, 2, 3, 4, 5, 1, 2, 3, 4])
        self.assertEqual(system.entities_terminated, 0)
        simulator.scheduler.run(10.0)
        self.assertEqual(system.current_class, 5)


if __name__ == "__main__":
    unittest.main()
