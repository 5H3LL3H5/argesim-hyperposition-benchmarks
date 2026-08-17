import unittest

from argesim_benchmarks.catalog import BenchmarkStatus, benchmark

from argesim_benchmarks.models.c21_state_events import (
    C21BouncingBallParameters,
    C21RLCDiodeParameters,
    C21RotatingPendulumParameters,
    C21DiodeModel,
    c21_bouncing_ball_h_b,
    c21_bouncing_ball_action_b,
    c21_compare_diode_models,
    c21_compare_diode_realtime,
    c21_dynamic_contact_study,
    c21_event_contact_study,
    c21_last_bounce_time,
    c21_rlc_diode_h_c,
    c21_rlc_diode_h_l_shortcut,
    c21_rotating_pendulum_h_f,
    c21_rotating_pendulum_h_s,
    c21_rotating_pendulum_action_f,
    c21_rotating_pendulum_action_s,
    c21_rotating_pendulum_basic_study,
    c21_rotating_pendulum_kick_study,
    solve_c21_bouncing_ball_event_contact,
    solve_c21_rotating_pendulum,
    c21_shockley_algebraic,
    c21_shockley_algebraic_current,
    c21_validate_bounce_times,
    simulate_c21_bouncing_ball_dynamic_contact,
    simulate_c21_rlc_diode,
)


class C21Tests(unittest.TestCase):
    def test_catalog_status(self) -> None:
        self.assertEqual(benchmark("C21").status, BenchmarkStatus.VALIDATED)

    def test_bouncing_ball_event_functions(self) -> None:
        state_before = (0.0, -10.0)
        self.assertEqual(c21_bouncing_ball_h_b(state_before), 0.0)
        state_after = c21_bouncing_ball_action_b(
            state_before, C21BouncingBallParameters()
        )
        self.assertEqual(state_after, (0.0, 9.0))

    def test_rlc_diode_event_functions(self) -> None:
        params = C21RLCDiodeParameters()
        state = (1.0, -10.0, 0.0)  # i, uc, ud
        # h_c = R2 * i + uc = 20 * 1 - 10 = 10
        self.assertEqual(c21_rlc_diode_h_c(state, params), 10.0)

        # shortcut locking
        # h_l = -(R2 * i + u_c) = -(10) = -10
        self.assertEqual(c21_rlc_diode_h_l_shortcut(state, params), -10.0)

    def test_rotating_pendulum_event_functions(self) -> None:
        params = C21RotatingPendulumParameters()
        # Fall event
        state = (0.0, 10.0)  # phi, dphi
        # h_f = -m*g*cos(phi) + m*l*dphi**2 = -1.5*9.81*1 + 1.5*1*100
        self.assertAlmostEqual(
            c21_rotating_pendulum_h_f(state, params), -1.5 * 9.81 + 150.0
        )

        cartesian = c21_rotating_pendulum_action_f(state, params)
        # x = l*sin(phi) = 0
        # y = l*cos(phi) = 1 (phi is measured from the upper point)
        # dx = l*dphi*cos(phi) = 10
        # dy = l*dphi*sin(phi) = 0
        self.assertEqual(cartesian, (0.0, 10.0, 1.0, 0.0))

        # Swing event
        self.assertEqual(c21_rotating_pendulum_h_s(cartesian, params), 0.0)
        polar = c21_rotating_pendulum_action_s(cartesian, params)
        self.assertEqual(polar, (0.0, 10.0))

    def test_bouncing_ball_solver_runs(self) -> None:
        times, states = solve_c21_bouncing_ball_event_contact(t_bound=5.0)
        self.assertTrue(len(times) > 0)
        self.assertEqual(len(times), len(states))
        self.assertGreater(times[-1], 0.0)

    def test_first_100_linear_bounces_match_analytical_times(self) -> None:
        validation = c21_validate_bounce_times(100)
        self.assertEqual(len(validation.numerical_times), 100)
        self.assertLess(validation.maximum_error, 2.0e-9)
        self.assertGreater(c21_last_bounce_time(), validation.numerical_times[-1])

    def test_dynamic_contact_has_finite_contact_phase(self) -> None:
        result = simulate_c21_bouncing_ball_dynamic_contact(t_bound=2.0)
        self.assertEqual(
            [event.name for event in result.events[:3]],
            ["contact", "maximum-deformation", "fly"],
        )
        self.assertGreater(
            float(result.events[2].time.macro),
            float(result.events[0].time.macro),
        )

    def test_event_and_dynamic_contact_studies_match_published_values(self) -> None:
        event = c21_event_contact_study()
        self.assertAlmostEqual(event.linear_limit, 27.129019, places=5)
        self.assertAlmostEqual(event.nonlinear_limit, 25.589465, places=4)
        contact = c21_dynamic_contact_study()
        self.assertLess(contact.maximum_height_error, 1.0e-7)
        self.assertLess(contact.maximum_deformation_error, 1.0e-9)

    def test_pendulum_solver_runs(self) -> None:
        times, states = solve_c21_rotating_pendulum(t_bound=2.0)
        self.assertTrue(len(times) > 0)
        self.assertEqual(len(times), len(states))
        self.assertGreater(times[-1], 0.0)

    def test_pendulum_stop_and_all_kick_factors_match_publication(self) -> None:
        basic = c21_rotating_pendulum_basic_study()
        self.assertLess(basic.absolute_error, 1.0e-6)
        kick = c21_rotating_pendulum_kick_study()
        self.assertEqual(len(kick.entries), 3)
        self.assertLess(max(entry.absolute_error for entry in kick.entries), 5.0e-5)

    def test_rlc_diode_formulations_preserve_algebraic_constraint(self) -> None:
        for model in C21DiodeModel:
            result = simulate_c21_rlc_diode(
                model,
                t_bound=5.0e-6,
                options={"max_step": 2.0e-8, "rtol": 1.0e-7, "atol": 1.0e-10},
            )
            self.assertEqual(result.times[-1], 5.0e-6)
            self.assertLess(result.maximum_algebraic_residual, 1.0e-8)

    def test_shockley_algebraic_root(self) -> None:
        voltage, diode_current, residual = c21_shockley_algebraic(1.0e-4, 0.01)
        self.assertGreater(voltage, 0.0)
        self.assertGreaterEqual(diode_current, 0.0)
        self.assertLess(abs(residual), 1.0e-12)
        current_form = c21_shockley_algebraic_current(1.0e-4, 0.01)
        for left, right in zip((voltage, diode_current), current_form[:2]):
            self.assertAlmostEqual(left, right, delta=1.0e-14)

    def test_complete_diode_study(self) -> None:
        study = c21_compare_diode_models()
        entries = {entry.label: entry for entry in study.entries}
        self.assertEqual(
            set(entries),
            {
                "shortcut",
                "shockley-uD",
                "shockley-iD",
                "interpolated-3",
                "interpolated-5",
                "interpolated-10",
                "shockley-explicit",
            },
        )
        self.assertLess(entries["shockley-iD"].maximum_current_deviation, 1.0e-12)
        self.assertLess(
            entries["interpolated-10"].maximum_current_deviation,
            entries["interpolated-3"].maximum_current_deviation,
        )

    def test_fixed_step_no_backtracking_diode_study(self) -> None:
        study = c21_compare_diode_realtime(t_bound=1.0e-6, step=2.0e-9)
        self.assertEqual(len(study.entries), 3)
        self.assertTrue(
            all(entry.maximum_algebraic_residual < 1.0e-8 for entry in study.entries)
        )


if __name__ == "__main__":
    unittest.main()
