import unittest

from argesim_benchmarks.models.c14_supply_chain import (
    c14_task_a1,
    c14_task_a2,
    c14_task_b1,
    c14_task_b2,
    c14_task_c1,
    c14_task_c2,
)

class TestC14SupplyChain(unittest.TestCase):
    def test_task_a1(self):
        history = c14_task_a1(seed=123)
        self.assertTrue(len(history) > 0)
        self.assertTrue(all(len(stock) == 12 for time, stock in history))

    def test_task_a2(self):
        metrics = c14_task_a2(seed=123, runs=2)
        self.assertIn("C", metrics)
        self.assertAlmostEqual(metrics["C"]["mean"], 3429.5, places=2)
        self.assertAlmostEqual(metrics["N"]["mean"], 211.0, places=2)

    def test_task_b1(self):
        history = c14_task_b1(seed=456)
        self.assertTrue(len(history) > 0)
        self.assertTrue(all(len(stock) == 12 for time, stock in history))

    def test_task_b2(self):
        metrics = c14_task_b2(seed=456, runs=2)
        self.assertIn("C", metrics)
        self.assertAlmostEqual(metrics["C"]["mean"], 2331.5, places=2)
        self.assertAlmostEqual(metrics["N"]["mean"], 243.5, places=2)

    def test_task_c1(self):
        metrics = c14_task_c1(seed=789, runs=2)
        self.assertIn("C", metrics)
        self.assertAlmostEqual(metrics["C"]["mean"], 2274.5, places=2)
        self.assertAlmostEqual(metrics["N"]["mean"], 225.5, places=2)

    def test_task_c2(self):
        comparative_metrics = c14_task_c2(seed=101, runs=2)
        self.assertIn("Strategy A", comparative_metrics)
        self.assertIn("Strategy B", comparative_metrics)
        self.assertIn("Strategy C", comparative_metrics)
        self.assertAlmostEqual(comparative_metrics["Strategy A"]["C"]["mean"], 3384.0, places=2)
        self.assertAlmostEqual(comparative_metrics["Strategy B"]["C"]["mean"], 2302.5, places=2)

        # Verify Strategy B and Strategy C yield identical results for these parameters
        # as expected due to D1's specific factory-product lead times mapping
        strat_b = comparative_metrics["Strategy B"]
        strat_c = comparative_metrics["Strategy C"]
        for metric in ["C", "N", "R"]:
            for stat in ["mean", "dev", "min", "max"]:
                self.assertAlmostEqual(strat_b[metric][stat], strat_c[metric][stat], places=2)

if __name__ == "__main__":
    unittest.main()
