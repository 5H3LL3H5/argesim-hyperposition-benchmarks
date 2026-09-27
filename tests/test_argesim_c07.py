"""Tests for the ARGESIM C07 benchmark."""

import math
import unittest

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus
from argesim_benchmarks.models.c07_constrained_pendulum import (
    C07Parameters,
    c07_rhs,
    c07_task_a,
    c07_task_b,
    c07_task_c,
)


class TestC07(unittest.TestCase):
    def test_c07_catalog_status(self):
        c07 = next(b for b in BENCHMARKS if b.identifier == "C07")
        self.assertEqual(c07.status, BenchmarkStatus.IMPLEMENTED)

    def test_parameters_validation(self):
        with self.assertRaises(ValueError):
            C07Parameters(m=-1.0)
        with self.assertRaises(ValueError):
            C07Parameters(l=1.0, l_p=1.5)

    def test_rhs_nonlinear(self):
        params = C07Parameters(m=1.0, l=1.0, l_p=0.5, g=10.0, d=0.1, phi_p=0.0)
        rhs = c07_rhs(params)

        # Above pin (phi > 0): l_eff = 1.0
        # phi_ddot = -(10.0 * sin(pi/6) + 0.1 * 1.0 * 2.0) / 1.0 = -(5.0 + 0.2) = -5.2
        res = rhs(0.0, (math.pi/6, 2.0))
        self.assertAlmostEqual(res[0], 2.0)
        self.assertAlmostEqual(res[1], -5.2)

        # Below pin (phi < 0): l_eff = 0.5
        # phi_ddot = -(10.0 * sin(-pi/6) + 0.1 * 0.5 * 2.0) / 0.5 = -(-5.0 + 0.1) / 0.5 = 9.8
        res = rhs(0.0, (-math.pi/6, 2.0))
        self.assertAlmostEqual(res[0], 2.0)
        self.assertAlmostEqual(res[1], 9.8)

    def test_rhs_linear(self):
        params = C07Parameters(m=1.0, l=1.0, l_p=0.5, g=10.0, d=0.1, phi_p=0.0, linear=True)
        rhs = c07_rhs(params)

        # Above pin (phi > 0): l_eff = 1.0
        res = rhs(0.0, (0.1, 2.0))
        self.assertAlmostEqual(res[1], -1.2)

        # Below pin (phi < 0): l_eff = 0.5
        res = rhs(0.0, (-0.1, 2.0))
        self.assertAlmostEqual(res[1], 1.8)

    def test_task_a(self):
        res = c07_task_a()
        self.assertIn("task_a_i", res)
        self.assertIn("task_a_ii", res)

        r1 = res["task_a_i"]
        self.assertGreater(len(r1.times), 10)
        self.assertEqual(r1.times[0], 0.0)
        self.assertAlmostEqual(r1.times[-1], 10.0)

        r2 = res["task_a_ii"]
        self.assertGreater(len(r2.times), 10)

    def test_task_b(self):
        res = c07_task_b()
        self.assertIn("task_b_nonlinear", res)
        self.assertIn("task_b_linear", res)

        r1 = res["task_b_nonlinear"]
        self.assertGreater(len(r1.times), 10)

        r2 = res["task_b_linear"]
        self.assertGreater(len(r2.times), 10)

    def test_task_c(self):
        v = c07_task_c()
        self.assertTrue(math.isfinite(v))
        self.assertLess(v, 0.0)
        self.assertAlmostEqual(v, -2.1846992883, delta=2.0e-8)
