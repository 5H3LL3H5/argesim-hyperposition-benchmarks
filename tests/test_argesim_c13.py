"""Tests for the ARGESIM C13 benchmark implementation."""

import unittest
import math

from argesim_benchmarks.models.c13_crane import (
    c13_task_a,
    c13_task_b,
    c13_task_c,
)
from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus


class C13Tests(unittest.TestCase):
    def test_c13_catalog_status(self):
        c13 = next(b for b in BENCHMARKS if b.identifier == "C13")
        self.assertEqual(c13.status, BenchmarkStatus.IMPLEMENTED)

    def test_task_a_returns_all_results(self):
        result = c13_task_a()
        self.assertIn(-750.0, result)
        self.assertIn(-800.0, result)
        self.assertIn(-850.0, result)

        self.assertTrue(math.isfinite(result[-750.0]["linear"]))
        self.assertTrue(math.isfinite(result[-750.0]["nonlinear"]))

        self.assertAlmostEqual(result[-750.0]["linear"], 294.08445, places=4)
        self.assertAlmostEqual(result[-750.0]["nonlinear"], 294.08414, places=4)

    def test_task_b_runs_and_returns_trajectory(self):
        res = c13_task_b()
        self.assertEqual(res.method, "rk45-dormand-prince-5(4)")
        self.assertTrue(len(res.times) > 10)
        self.assertAlmostEqual(res.times[-1], 60.0, places=5)
        self.assertEqual(len(res.states[0]), 5)
        self.assertAlmostEqual(res.states[-1][0], 3.70588, places=4)
        self.assertAlmostEqual(res.states[-1][2], 0.00843, places=4)

    def test_task_c_runs_and_returns_trajectory(self):
        res = c13_task_c()
        self.assertEqual(res.method, "rk45-dormand-prince-5(4)")
        self.assertTrue(len(res.times) > 10)
        self.assertAlmostEqual(res.times[-1], 60.0, places=5)
        self.assertEqual(len(res.states[0]), 5)
        self.assertAlmostEqual(res.states[-1][0], 5.00606, places=4)
        self.assertAlmostEqual(res.states[-1][2], -0.18938, places=4)


if __name__ == "__main__":
    unittest.main()
