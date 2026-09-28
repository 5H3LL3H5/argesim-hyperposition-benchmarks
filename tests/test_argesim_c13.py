"""Tests for the ARGESIM C13 benchmark implementation."""

import unittest
import math

from argesim_benchmarks.models.c13_crane import (
    C13Controller,
    C13Parameters,
    C13_INITIAL_STATE,
    c13_linear_rhs,
    _c13_disturbance_force,
    c13_task_a,
    c13_task_b_study,
    c13_task_c_study,
)
from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus


class C13Tests(unittest.TestCase):
    def test_2006_load_friction_reproduces_old_task_a_scale(self):
        """Independent RK4 stepping guards the identified revision difference."""
        def terminal_load_position(load_friction):
            parameters = C13Parameters(dl=load_friction)
            state = C13_INITIAL_STATE
            dt = 0.1
            for duration, disturbance, drive in (
                (4.0, 0.0, 160.0),
                (3.0, -750.0, 160.0),
                (8.0, 0.0, 160.0),
                (1985.0, 0.0, 0.0),
            ):
                rhs = c13_linear_rhs(parameters, fc_desired=drive,
                                     fd=disturbance)
                for _ in range(round(duration / dt)):
                    k1 = rhs(0.0, state)
                    k2 = rhs(0.0, tuple(x + dt * y / 2 for x, y in zip(state, k1)))
                    k3 = rhs(0.0, tuple(x + dt * y / 2 for x, y in zip(state, k2)))
                    k4 = rhs(0.0, tuple(x + dt * y for x, y in zip(state, k3)))
                    state = tuple(
                        x + dt * (a + 2 * b + 2 * c + d) / 6
                        for x, a, b, c, d in zip(state, k1, k2, k3, k4)
                    )
            return state[0] + parameters.r * state[2]

        old = terminal_load_position(0.01)
        revised = terminal_load_position(0.001)
        self.assertAlmostEqual(old, 294.084453, delta=0.15)
        self.assertAlmostEqual(revised, 299.361523, delta=0.15)
        self.assertGreater(revised - old, 5.0)

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

        # The revised definition asks for the position after about 2000 s.
        # The 2006 solution used d_l=0.01 and reports ~294 m; the 2007
        # definition uses d_l=0.001 and gives ~299 m (see the C13 audit).
        # Net impulse ±150 Ns implies a rough ±300 m scale at d_c=0.5.
        # Check that both models preserve that symmetry and cancel at -800 N.
        for model in ("linear", "nonlinear"):
            self.assertAlmostEqual(result[-750.0][model], 300.0, delta=1.0)
            self.assertAlmostEqual(result[-800.0][model], 0.0, delta=0.02)
            self.assertAlmostEqual(result[-850.0][model], -300.0, delta=1.0)
            self.assertAlmostEqual(
                result[-750.0][model] + result[-850.0][model],
                2 * result[-800.0][model], delta=0.02,
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
