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
        self.assertIn("N", metrics)
        self.assertIn("R", metrics)
        self.assertTrue(metrics["C"]["mean"] >= 0)

    def test_task_b1(self):
        history = c14_task_b1(seed=456)
        self.assertTrue(len(history) > 0)
        self.assertTrue(all(len(stock) == 12 for time, stock in history))

    def test_task_b2(self):
        metrics = c14_task_b2(seed=456, runs=2)
        self.assertIn("C", metrics)
        self.assertIn("N", metrics)
        self.assertIn("R", metrics)
        self.assertTrue(metrics["C"]["mean"] >= 0)

    def test_task_c1(self):
        metrics = c14_task_c1(seed=789, runs=2)
        self.assertIn("C", metrics)
        self.assertIn("N", metrics)
        self.assertIn("R", metrics)
        self.assertTrue(metrics["C"]["mean"] >= 0)

    def test_task_c2(self):
        comparative_metrics = c14_task_c2(seed=101, runs=2)
        self.assertIn("Strategy A", comparative_metrics)
        self.assertIn("Strategy B", comparative_metrics)
        self.assertIn("Strategy C", comparative_metrics)
        self.assertIn("C", comparative_metrics["Strategy A"])

if __name__ == "__main__":
    unittest.main()
