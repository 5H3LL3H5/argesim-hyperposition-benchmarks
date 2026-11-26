"""Scale and sign regressions for quantized-state event calendars."""
import math
import unittest
from decimal import Decimal, localcontext

from argesim_benchmarks import InitialValueProblem, solve_ivp
from argesim_benchmarks.solvers._polynomial import first_positive_root
from argesim_benchmarks.solvers.qss import _smallest_nonnegative_root


class QssCalendarRegressionTests(unittest.TestCase):
    def test_threshold_contacts_are_real_roots_of_the_represented_polynomial(self):
        for sign in (-1, 1):
            for tail in ([], [0.0, 0.0]):
                def root(c, horizon=2.0, sign=sign, tail=tail):
                    return first_positive_root(
                        [sign * c, -2 * sign, sign, *tail], horizon, time_tolerance=1e-13
                    )
                self.assertEqual(_smallest_nonnegative_root(sign, -2*sign, sign*(1+2**-52), 1e-13), math.inf)
                self.assertEqual(root(1 + 2**-52), math.inf)
                self.assertEqual(root(1), 1)
                self.assertAlmostEqual(root(1 - 2**-52), 1 - 2**-26, delta=1e-13)
                self.assertEqual(root(1, math.nextafter(1, 0)), math.inf)
        # An irrational repeated root must survive exact square-free reduction.
        self.assertAlmostEqual(first_positive_root(
            [4, 0, -4, 0, 1], 2, time_tolerance=1e-13
        ), math.sqrt(2), delta=1e-13)

    def test_subnormal_coefficients_preserve_crossings_and_near_misses(self):
        # t² - 3t + 2 crosses at 1 and 2; t² - 3t + 3 stays positive.
        unit = math.ulp(0.0)
        for scale in (unit, -unit, 1.0):
            with self.subTest(scale=scale):
                crossing = first_positive_root(
                    [2 * scale, -3 * scale, scale], 3.0, time_tolerance=1e-13
                )
                self.assertAlmostEqual(crossing, 1.0, delta=1e-13)
                self.assertEqual(first_positive_root(
                    [3 * scale, -3 * scale, scale], 3.0, time_tolerance=1e-13
                ), math.inf)

    def test_reciprocal_horner_keeps_the_earliest_large_root(self):
        # The represented quadratic has roots near 1e100 and 2e100.
        coefficients = [9.88131291682493e-124, -1.4821969375237398e-223, 5e-324]
        root = first_positive_root(coefficients, 3e100, time_tolerance=1e-13)
        self.assertTrue(math.isclose(root, 1e100, rel_tol=2e-15), root)

    def test_mixed_exponents_preserve_the_represented_polynomial(self):
        coefficients = [2.0, -3e-161, 1e-322]
        with localcontext() as context:
            context.prec = 90
            c, b, a = map(Decimal.from_float, coefficients)
            reference = float(2 * c / (-b + (b*b - 4*a*c).sqrt()))
        root = first_positive_root(coefficients, 3e161, time_tolerance=1e-13)
        self.assertTrue(math.isclose(root, reference, rel_tol=2e-15), root)

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
