import unittest
from unittest.mock import patch

from argesim_benchmarks.models.c20_complex_production import (
    C20OrderResult,
    C20ReplicationResult,
    run_c20_experiment,
)


class C20StatisticsTests(unittest.TestCase):
    def test_task_b_retains_order_spread_and_task_c_unweighted_tardiness(self):
        def replication(osc, psc, *, seed, order_count):
            self.assertEqual(order_count, 2)
            orders = tuple(
                C20OrderResult(
                    i,
                    "A",
                    0.0,
                    duration,
                    5.0,
                    duration,
                    max(0.0, duration - 5.0),
                    0.4 * max(0.0, duration - 5.0),
                    0,
                    0,
                    0,
                )
                for i, duration in enumerate((1.0, 9.0))
            )
            return C20ReplicationResult(
                osc, psc, seed, 9.0, 5.0, 1, 1.6, 0, 0, 2, orders, total_tardiness=4.0
            )

        with patch(
            "argesim_benchmarks.models.c20_complex_production.run_c20_replication",
            side_effect=replication,
        ):
            summaries = run_c20_experiment(replications=10, order_count=2)
        self.assertEqual(len(summaries), 12)
        for summary in summaries:
            self.assertEqual(summary.throughput_time.median, 5.0)
            self.assertEqual(summary.throughput_time.iqr, 8.0)
            self.assertEqual(summary.replication_median_throughput_time.iqr, 0.0)
            self.assertEqual(summary.tardiness.median, 4.0)
            self.assertEqual(summary.weighted_tardiness.median, 1.6)


if __name__ == "__main__":
    unittest.main()
