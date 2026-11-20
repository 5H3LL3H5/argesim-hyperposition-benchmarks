import unittest
from dataclasses import replace

from argesim_benchmarks.experiments.c20_audit import audit_flow, audit_result
from argesim_benchmarks.models.c20_complex_production import run_c20_replication
from argesim_benchmarks.models.c20_production import C20Production


class C20AuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.simulation = C20Production(
            "OSc3", "PSc4", seed=1000, order_seed=20, order_count=40, trace=True
        )
        cls.orders = [job.order for job in cls.simulation.jobs.values()]
        cls.result = cls.simulation.run()

    def audit_trace(self, trace):
        flow = self.simulation.flow
        return audit_flow(flow.layout, trace, flow.failures, flow.completed_trips)

    def test_full_trace_and_independently_recomputed_metrics(self):
        audit_result(self.result, self.orders)
        report = self.audit_trace(self.simulation.flow.trace)
        self.assertEqual(report["insertions"], report["removals"])
        self.assertGreater(report["movements"], 1000)

    def test_result_mutations_are_rejected(self):
        for mutation in (
            replace(self.result, makespan=self.result.makespan + 1),
            replace(self.result, orders=self.result.orders[:-1]),
            replace(
                self.result,
                orders=(
                    replace(self.result.orders[0], due_date=-1),
                    *self.result.orders[1:],
                ),
            ),
            replace(
                self.result,
                orders=(
                    replace(self.result.orders[0], throughput_time=float("nan")),
                    *self.result.orders[1:],
                ),
            ),
        ):
            with (
                self.subTest(mutation=mutation.makespan),
                self.assertRaises(ValueError),
            ):
                audit_result(mutation, self.orders)

    def test_corrupt_ownership_occupancy_and_truncated_traces_are_rejected(self):
        original = self.simulation.flow.trace
        index = next(i for i, event in enumerate(original) if event[1] == "exit")
        for field, value in ((2, -999), (4, 100), (0, -1.0)):
            trace = list(original)
            event = list(trace[index])
            event[field] = value
            trace[index] = tuple(event)
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.audit_trace(trace)
        with self.assertRaisesRegex(ValueError, "parts left"):
            self.audit_trace(original[:-1])

    def test_corrupt_reported_path_is_rejected(self):
        flow = self.simulation.flow
        trips = list(flow.completed_trips)
        trips[0] = replace(trips[0], distance=trips[0].distance + 1)
        with self.assertRaisesRegex(ValueError, "trip distance"):
            audit_flow(flow.layout, flow.trace, flow.failures, trips)

    def test_fixed_book_is_independent_of_failure_seed(self):
        first = C20Production("OSc3", "PSc4", seed=10, order_seed=20, order_count=40)
        second = C20Production("OSc3", "PSc4", seed=11, order_seed=20, order_count=40)
        self.assertEqual(
            [job.order for job in first.jobs.values()],
            [job.order for job in second.jobs.values()],
        )
        self.assertNotEqual(
            first.machines[0].next_failure, second.machines[0].next_failure
        )
        first_result = run_c20_replication(
            "OSc1", "PSc1", seed=10, order_seed=20, order_count=20
        )
        second_result = run_c20_replication(
            "OSc1", "PSc1", seed=11, order_seed=20, order_count=20
        )
        self.assertEqual(replace(first_result, seed=11), second_result)

    def test_invalid_order_seed_is_rejected(self):
        for seed in (True, "20", 20.5):
            with self.subTest(seed=seed), self.assertRaises(TypeError):
                run_c20_replication(order_seed=seed, order_count=1)


if __name__ == "__main__":
    unittest.main()
