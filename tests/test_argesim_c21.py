import unittest

from argesim_benchmarks.models.c21_state_events import (
    C21BouncingBallParameters,
    C21RLCDiodeParameters,
    C21RotatingPendulumParameters,
    c21_bouncing_ball_h_b,
    c21_bouncing_ball_action_b,
    c21_rlc_diode_h_c,
    c21_rlc_diode_h_l_shortcut,
    c21_rotating_pendulum_h_f,
    c21_rotating_pendulum_h_s,
    c21_rotating_pendulum_action_f,
    c21_rotating_pendulum_action_s,
    solve_c21_bouncing_ball_event_contact,
    solve_c21_rotating_pendulum,
)


class C21Tests(unittest.TestCase):
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
        # y = -l*cos(phi) = -1
        # dx = l*dphi*cos(phi) = 10
        # dy = l*dphi*sin(phi) = 0
        self.assertEqual(cartesian, (0.0, 10.0, -1.0, 0.0))

        # Swing event
        self.assertEqual(c21_rotating_pendulum_h_s(cartesian, params), 0.0)
        polar = c21_rotating_pendulum_action_s(cartesian, params)
        self.assertEqual(polar, (0.0, 10.0))

    def test_bouncing_ball_solver_runs(self) -> None:
        times, states = solve_c21_bouncing_ball_event_contact(t_bound=5.0)
        self.assertTrue(len(times) > 0)
        self.assertEqual(len(times), len(states))
        self.assertGreater(times[-1], 0.0)

    def test_pendulum_solver_runs(self) -> None:
        times, states = solve_c21_rotating_pendulum(t_bound=2.0)
        self.assertTrue(len(times) > 0)
        self.assertEqual(len(times), len(states))
        self.assertGreater(times[-1], 0.0)


if __name__ == "__main__":
    unittest.main()
