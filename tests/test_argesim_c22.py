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
        self.assertEqual(c22.status, BenchmarkStatus.IMPLEMENTED)

    def test_c22_basic_runs_without_errors(self) -> None:
        results = c22_basic()
        self.assertIn("deterministic", results)
        self.assertIn("stochastic", results)
        self.assertEqual(len(results["deterministic"]["ids_out"]), 20)
        self.assertEqual(results["deterministic"]["first_arrival_time"], 1.0)
        self.assertEqual(results["deterministic"]["entities_created"], 100)
        self.assertEqual(results["deterministic"]["entities_terminated"], 100)
        self.assertEqual(results["deterministic"]["active_entities"], 0)
        # Structural check against expected bounds
        self.assertAlmostEqual(results["deterministic"]["tq_avg"], 6.7, places=1)
        self.assertAlmostEqual(results["deterministic"]["tq_max"], 13.5, places=1)

        # Verify large stoch model
        self.assertGreater(results["stochastic_large"]["lqt_max"], 0)

    def test_c22_jockeying_has_events(self) -> None:
        results = c22_jockeying()

        # In jockeying, deterministic might have a small number of events or 0
        # depending on exact event timings, but we expect the dicts to have the key
        self.assertIn("jockey_events", results["deterministic"])
        self.assertIn("jockey_table", results["deterministic"])
        self.assertIn("jockey_events", results["stochastic"])
        # Check standard deterministic trace properties
        self.assertGreaterEqual(results["stochastic"]["jockey_events"], 100)

    def test_c22_reneging_has_events(self) -> None:
        results = c22_reneging()

        self.assertIn("renege_events", results["deterministic"])
        self.assertIn("renege_table", results["deterministic"])
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

        # Classes should have non-negative avg wait times
        for c in range(1, 6):
            self.assertGreaterEqual(det_stats[c]["avg"], 0.0)

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
