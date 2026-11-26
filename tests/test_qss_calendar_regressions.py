"""Scale and sign regressions for quantized-state event calendars."""
import math
import unittest

from argesim_benchmarks import InitialValueProblem, solve_ivp
from argesim_benchmarks.solvers._polynomial import first_positive_root


class QssCalendarRegressionTests(unittest.TestCase):
    def test_early_event_is_independent_of_large_terminal_horizon(self):
        for degree, coefficient in ((3, 3492280.285107953), (4, 331313052.57113314)):
            polynomial = [-0.001, *([0.0] * (degree - 1)), coefficient]
            expected = (0.001 / coefficient) ** (1.0 / degree)
            for horizon in (0.1, 1.0, 136.71875, 1.0e8):
                with self.subTest(degree=degree, horizon=horizon):
                    root = first_positive_root(polynomial, horizon, time_tolerance=1e-13)
                    self.assertAlmostEqual(root, expected, delta=1e-13)

    def test_excludes_initial_root_but_finds_later_tangency(self):
        # t (t - 1/8)^2 has a start root and a non-crossing boundary contact.
        root = first_positive_root([0., 1/64, -1/4, 1.], 136.71875, time_tolerance=1e-13)
        self.assertAlmostEqual(root, 1/8, delta=1e-12)

    def test_close_times_do_not_merge_distant_cell_boundaries(self):
        problem = InitialValueProblem(lambda t, y: (1e12, 0.5e12), 0., (0., 0.), 1.5e-12, autonomous=True)
        for method in ('qss1', 'cqss1', 'bqss1', 'qss3', 'qss4'):
            with self.subTest(method=method):
                result = solve_ivp(problem, method, options={'quantum': 1.})
                self.assertLessEqual(math.dist(result.final_state, (1.5, .75)), 2e-12)

    def test_negative_quadratic_root_cannot_schedule_a_zero_time_event(self):
        problem = InitialValueProblem(lambda t, y: (y[1], 2e26), 0., (0., 0.), 1.5e-13, autonomous=True)
        result = solve_ivp(problem, 'qss2', options={'quantum': (1., 1e20), 'max_events': 10})
        self.assertAlmostEqual(result.times[1], 1e-13, delta=1e-26)
        # QSS2 estimates curvature by a finite difference after the event.
        self.assertTrue(math.isclose(result.final_state[0], 2.25, rel_tol=1e-8))
        self.assertAlmostEqual(result.final_state[1], 3e13, delta=.004)
