import math
import unittest

from argesim_benchmarks import (
    InitialValueProblem,
    liqss1,
    liqss2,
    liqss3,
    mliqss1,
    mliqss2,
    mliqss3,
    qss3,
    qss4,
)
from argesim_benchmarks.runtime import normalise_solver_name, solve_ivp
from argesim_benchmarks.solvers._polynomial import first_positive_root


class AdvancedQssTests(unittest.TestCase):
    @staticmethod
    def decay_problem(t_bound: float = 1.0) -> InitialValueProblem:
        return InitialValueProblem(
            lambda _time, state: (-state[0],),
            0.0,
            (1.0,),
            t_bound,
            name="advanced-qss-decay",
            autonomous=True,
        )

    def test_qss3_and_qss4_converge_with_smaller_quanta(self) -> None:
        exact = math.exp(-1.0)
        for solver in (qss3, qss4):
            with self.subTest(solver=solver.__name__):
                coarse = abs(solver(self.decay_problem(), 0.05).final_state[0] - exact)
                fine = abs(
                    solver(self.decay_problem(), 0.003125).final_state[0] - exact
                )
                self.assertLess(fine, coarse)
                self.assertLess(fine, 2.0e-4)

    def test_low_degree_root_isolator_detects_tangential_roots(self) -> None:
        # (t - 0.2)^2 * (t - 0.7)
        coefficients = (-0.028, 0.32, -1.1, 1.0)
        root = first_positive_root(
            coefficients, 1.0, time_tolerance=1.0e-13
        )
        self.assertAlmostEqual(root, 0.2, places=10)

    def test_root_isolator_keeps_a_simple_root_before_a_close_double_root(self) -> None:
        first = 0.4
        repeated = 0.4001
        # (t - first) * (t - repeated)^2
        coefficients = (
            -first * repeated**2,
            repeated**2 + 2.0 * first * repeated,
            -(first + 2.0 * repeated),
            1.0,
        )
        root = first_positive_root(
            coefficients, 1.0, time_tolerance=1.0e-13
        )
        self.assertAlmostEqual(root, first, places=8)

    def test_liqss_orders_converge_on_a_stiff_triangular_system(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (
                -1000.0 * state[0] + state[1],
                -state[1],
            ),
            0.0,
            (0.0, 1.0),
            1.0,
            name="stiff-triangular",
            autonomous=True,
        )
        jacobian = lambda _time, _state: ((-1000.0, 1.0), (0.0, -1.0))
        exact = ((math.exp(-1.0) - math.exp(-1000.0)) / 999.0, math.exp(-1.0))
        for solver in (liqss1, liqss2, liqss3):
            with self.subTest(solver=solver.__name__):
                result = solver(
                    problem,
                    (1.0e-5, 1.0e-3),
                    jacobian=jacobian,
                    max_events=10_000,
                )
                self.assertEqual(result.final_time, 1.0)
                error = max(
                    abs(actual - expected)
                    for actual, expected in zip(result.final_state, exact)
                )
                self.assertLess(
                    error,
                    6.0e-4,
                )

    def test_modified_liqss_suppresses_pairwise_oscillation(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (
                -state[0] - state[1] + 0.2,
                state[0] - state[1] + 1.2,
            ),
            0.0,
            (-4.0, 4.0),
            20.0,
            name="mliqss-coupled-pair",
            autonomous=True,
        )
        jacobian = lambda _time, _state: ((-1.0, -1.0), (1.0, -1.0))
        for solver in (mliqss1, mliqss2, mliqss3):
            with self.subTest(solver=solver.__name__):
                result = solver(problem, 0.2, jacobian=jacobian)
                error = max(
                    abs(result.final_state[0] + 0.5),
                    abs(result.final_state[1] - 0.7),
                )
                self.assertLess(error, 0.01)
                self.assertLess(result.stats.accepted_steps, 50)

    def test_jacobian_free_liqss_matches_exact_linear_jacobian(self) -> None:
        problem = self.decay_problem(0.25)
        numerical = liqss2(problem, 0.01)
        exact = liqss2(
            problem,
            0.01,
            jacobian=lambda _time, _state: ((-1.0,),),
        )
        self.assertAlmostEqual(numerical.final_state[0], exact.final_state[0])

    def test_dispatch_supports_full_family_and_inherits_qss_defaults(self) -> None:
        defaults = {"qss2": {"quantum": 1.0e-3}}
        methods = (
            "qss3",
            "qss4",
            "liqss",
            "liqss2",
            "liqss3",
            "mliqss",
            "mliqss2",
            "mliqss3",
        )
        for method in methods:
            with self.subTest(method=method):
                result = solve_ivp(
                    self.decay_problem(0.1), method, defaults=defaults
                )
                self.assertEqual(result.final_time, 0.1)
        self.assertEqual(normalise_solver_name("LIQSS"), "liqss1")
        self.assertEqual(normalise_solver_name("mLIQSS"), "mliqss1")

    def test_invalid_advanced_controls_are_rejected(self) -> None:
        with self.assertRaises(TypeError):
            qss3(self.decay_problem(), 0.1, derivative_step=True)
        with self.assertRaises(ValueError):
            liqss1(
                self.decay_problem(),
                0.1,
                jacobian=lambda _time, _state: ((-1.0, 0.0),),
            )
        with self.assertRaises(TypeError):
            mliqss1(self.decay_problem(), 0.1, coupling_tolerance=True)


if __name__ == "__main__":
    unittest.main()
