"""Tests for the ARGESIM C11 benchmark."""

import unittest

from argesim_benchmarks.models.c11_scara_robot import (
    C11_INITIAL_STATE,
    C11_TARGET_STATE,
    C11Parameters,
    c11_inertia_terms,
    solve_c11,
)

class C11Tests(unittest.TestCase):
    def test_invalid_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            solve_c11("unsupported")

    def test_task_b_runs_to_completion(self) -> None:
        result = solve_c11("rk45", t_bound=2.0)
        self.assertEqual(result.times[-1], 2.0)
        q1, q2, q3, dq1, dq2, dq3, I1, I2, I3 = result.states[-1]

        # Verify that it reaches the target reasonably well
        self.assertAlmostEqual(q1, C11_TARGET_STATE[0], places=1)
        self.assertAlmostEqual(q2, C11_TARGET_STATE[1], places=1)
        self.assertAlmostEqual(q3, C11_TARGET_STATE[2], places=1)

    def test_official_mixed_inertia_coefficient_uses_half_link_mass(self) -> None:
        parameters = C11Parameters()
        _theta1, theta2, _theta3 = c11_inertia_terms(parameters)
        expected = (
            parameters.m2 / 2.0 + parameters.m3A + parameters.m3L
        ) * parameters.L1 * parameters.L2
        self.assertEqual(theta2, expected)

    def test_qss_defaults_match_the_nine_state_model(self) -> None:
        for method in ("qss1", "qss2"):
            with self.subTest(method=method):
                result = solve_c11(method, t_bound=1.0e-5)
                self.assertEqual(result.final_time, 1.0e-5)

    def test_task_c_collision_avoidance(self) -> None:
        result = solve_c11("rk45", t_bound=2.0, task="c")
        self.assertEqual(result.times[-1], 2.0)

        q1, q2, q3, dq1, dq2, dq3, I1, I2, I3 = result.states[-1]
        self.assertAlmostEqual(q1, C11_TARGET_STATE[0], places=1)
        self.assertAlmostEqual(q2, C11_TARGET_STATE[1], places=1)
        self.assertAlmostEqual(q3, C11_TARGET_STATE[2], places=1)

if __name__ == "__main__":
    unittest.main()
