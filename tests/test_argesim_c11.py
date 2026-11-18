"""Tests for the ARGESIM C11 benchmark."""

import unittest

from argesim_benchmarks.models.c11_scara_robot import (
    C11_INITIAL_STATE,
    C11_TARGET_STATE,
    C11Parameters,
    c11_inertia_terms,
    c11_rhs,
    c11_task_a,
    c11_task_b,
    c11_task_c,
    solve_c11,
)

class C11Tests(unittest.TestCase):
    def test_motor_torques_are_limited_to_the_specified_maxima(self) -> None:
        p = C11Parameters()
        # At q=dq=0, M*qdd equals the clamped joint drive torque (plus
        # vertical gravity). Check both current polarities independently.
        theta1, theta2, theta3 = c11_inertia_terms(p)
        for sign in (-1.0, 1.0):
            with self.subTest(sign=sign):
                rhs = c11_rhs(p)(0.0, (0.0,) * 6 + (sign * 100.0,) * 3)
                qdd1, qdd2, qdd3 = rhs[3:6]
                self.assertAlmostEqual(
                    (theta1 + 2 * theta2 + theta3) * qdd1
                    + (theta2 + theta3) * qdd2,
                    sign * p.u1 * p.T1_max,
                )
                self.assertAlmostEqual(
                    (theta2 + theta3) * qdd1 + theta3 * qdd2,
                    sign * p.u2 * p.T2_max,
                )
                self.assertAlmostEqual(
                    (p.m3L + p.Theta3_mot * p.u3**2) * qdd3 + p.m3L * p.g,
                    sign * p.u3 * p.T3_max,
                )

    def test_invalid_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            solve_c11("unsupported")

    def test_task_a_describes_explicit_nine_state_formulation(self) -> None:
        report = c11_task_a()
        self.assertEqual(report.formulation, "explicit-first-order-state-space")
        self.assertEqual(report.state_dimension, 9)
        self.assertEqual(report.algebraic_state_dimension, 0)
        self.assertEqual(
            report.state_order,
            ("q1", "q2", "q3", "dq1", "dq2", "dq3", "I1", "I2", "I3"),
        )

    def test_task_b_runs_to_completion(self) -> None:
        result = c11_task_b("rk45", t_bound=2.0)
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
        study = c11_task_c("rk45", t_bound=2.0)
        result = study.result
        self.assertEqual(result.times[-1], 2.0)
        self.assertEqual(len(study.x_tip), len(result.times))
        self.assertEqual(len(study.vertical_clearance), len(result.times))
        self.assertEqual(len(study.obstacle_x), len(result.times))
        self.assertTrue(
            all(value == C11Parameters().x_obs for value in study.obstacle_x)
        )
        for state, clearance in zip(result.states, study.vertical_clearance):
            self.assertAlmostEqual(clearance, state[2] - C11Parameters().h_obs)

        q1, q2, q3, _dq1, _dq2, _dq3, _i1, _i2, _i3 = result.states[-1]
        self.assertAlmostEqual(q1, C11_TARGET_STATE[0], places=1)
        self.assertAlmostEqual(q2, C11_TARGET_STATE[1], places=1)
        self.assertAlmostEqual(q3, C11_TARGET_STATE[2], places=1)

if __name__ == "__main__":
    unittest.main()
