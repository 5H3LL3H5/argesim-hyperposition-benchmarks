"""Tests for the ARGESIM C13 benchmark implementation."""

import unittest
import math

from argesim_benchmarks.models.c13_crane import (
    C13Controller,
    C13Parameters,
    _c13_disturbance_force,
    c13_task_a,
    c13_task_b_study,
    c13_task_c_study,
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

        references = {
            -750.0: {"linear": 294.075, "nonlinear": 294.041},
            -800.0: {"linear": -0.005, "nonlinear": 0.008},
            -850.0: {"linear": -294.096, "nonlinear": -294.112},
        }
        for disturbance, expected in references.items():
            for model, reference in expected.items():
                self.assertAlmostEqual(
                    result[disturbance][model],
                    reference,
                    delta=0.15,
                )

    def test_revised_parameters_and_controller_sampling(self) -> None:
        self.assertEqual(C13Parameters().dl, 0.001)
        self.assertEqual(C13Controller().dt, 0.1)

    def test_revised_task_b_c_disturbance_scenarios(self) -> None:
        self.assertEqual(
            _c13_disturbance_force(42.5, with_diagnosis=False),
            -200.0,
        )
        self.assertEqual(
            _c13_disturbance_force(46.5, with_diagnosis=False),
            0.0,
        )
        self.assertEqual(
            _c13_disturbance_force(42.5, with_diagnosis=True),
            -200.0,
        )
        self.assertEqual(
            _c13_disturbance_force(46.5, with_diagnosis=True),
            200.0,
        )

    def test_task_b_runs_and_returns_complete_trajectory(self):
        study = c13_task_b_study()
        res = study.result
        self.assertEqual(res.method, "rk45-dormand-prince-5(4)")
        self.assertGreater(len(res.times), 10)
        self.assertAlmostEqual(res.times[-1], 60.0, places=5)
        self.assertEqual(len(res.states[0]), 5)
        self.assertEqual(len(study.load_position), len(res.times))
        self.assertEqual(len(study.brake_active), len(res.times))
        self.assertEqual(len(study.emergency_stop), len(res.times))
        self.assertFalse(any(study.emergency_stop))

    def test_task_c_runs_and_returns_diagnosis_trajectory(self):
        study = c13_task_c_study()
        res = study.result
        self.assertEqual(res.method, "rk45-dormand-prince-5(4)")
        self.assertGreater(len(res.times), 10)
        self.assertAlmostEqual(res.times[-1], 60.0, places=5)
        self.assertEqual(len(res.states[0]), 5)
        self.assertEqual(len(study.load_position), len(res.times))
        self.assertEqual(len(study.brake_active), len(res.times))
        self.assertEqual(len(study.emergency_stop), len(res.times))


if __name__ == "__main__":
    unittest.main()
