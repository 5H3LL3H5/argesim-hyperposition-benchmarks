import unittest
from argesim_benchmarks.models.c06_emergency_department import (
    solve_c06_task_a,
    solve_c06_task_b,
    solve_c06_task_c,
)

class TestArgesimC06(unittest.TestCase):
    def test_task_a(self):
        metrics = solve_c06_task_a()

        self.assertIn("overall", metrics)
        self.assertIn("type_1", metrics)
        self.assertIn("type_2", metrics)
        self.assertIn("type_3", metrics)
        self.assertIn("type_4", metrics)
        self.assertIn("std_dev", metrics)

        for k, v in metrics.items():
            self.assertGreater(v, 0.0)

        self.assertAlmostEqual(metrics["overall"], 175.8378316189382, places=2)
        self.assertAlmostEqual(metrics["std_dev"], 81.96972982260127, places=2)

    def test_task_b(self):
        metrics = solve_c06_task_b()

        self.assertIn("overall", metrics)
        self.assertIn("std_dev", metrics)

        for k, v in metrics.items():
            self.assertGreater(v, 0.0)

        self.assertAlmostEqual(metrics["overall"], 173.5020289750295, places=2)
        self.assertAlmostEqual(metrics["std_dev"], 83.82369840673681, places=2)

    def test_task_c(self):
        metrics = solve_c06_task_c()

        self.assertIn("overall", metrics)
        self.assertIn("std_dev", metrics)

        for k, v in metrics.items():
            self.assertGreater(v, 0.0)

        self.assertAlmostEqual(metrics["overall"], 162.99342624559546, places=2)
        self.assertAlmostEqual(metrics["std_dev"], 76.63747308822325, places=2)
