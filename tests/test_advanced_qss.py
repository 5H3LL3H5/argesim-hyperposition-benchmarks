import math
import unittest

from argesim_benchmarks import (
    InitialValueProblem,
    cheqss1,
    cheqss2,
    cheqss3,
    eliqss1,
    eliqss2,
    eliqss3,
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
from argesim_benchmarks.solvers.advanced_qss import (
    _difference_coefficients,
    _first_positive_unbounded_root,
)


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
        # The dyadic coefficients represent (t-1/4)^2 (t-3/4) exactly.
        coeffs = (-3/64, 7/16, -5/4, 1.0)
        self.assertAlmostEqual(first_positive_root(
            coeffs, 1.0, time_tolerance=1e-13
        ), 0.25, places=12)
        # The intended decimal example retains its exact rational double
        # root when the same coefficients are supplied in integer units.
        self.assertAlmostEqual(first_positive_root(
            (-28, 320, -1100, 1000), 1.0, time_tolerance=1e-13
        ), 0.2, places=12)
        # Rounding these decimal coefficients removes the supposed double
        # root at 0.2. The represented cubic only crosses near 0.7.
        self.assertAlmostEqual(first_positive_root(
            (-0.028, 0.32, -1.1, 1.0), 1.0, time_tolerance=1e-13
        ), 0.7, places=12)

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

    def test_generalised_liqss_converges_on_a_stiff_triangular_system(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (
                -1000.0 * state[0] + state[1],
                -state[1],
            ),
            0.0,
            (0.0, 1.0),
            1.0,
            name="generalised-liqss-stiff-triangular",
            autonomous=True,
        )
        jacobian = lambda _time, _state: ((-1000.0, 1.0), (0.0, -1.0))
        exact = ((math.exp(-1.0) - math.exp(-1000.0)) / 999.0, math.exp(-1.0))
        for solver in (
            eliqss1,
            eliqss2,
            eliqss3,
            cheqss1,
            cheqss2,
            cheqss3,
        ):
            with self.subTest(solver=solver.__name__):
                result = solver(
                    problem,
                    (1.0e-5, 1.0e-3),
                    jacobian=jacobian,
                    max_events=10_000,
                )
                error = max(
                    abs(actual - expected)
                    for actual, expected in zip(result.final_state, exact)
                )
                self.assertEqual(result.final_time, 1.0)
                self.assertLess(error, 3.0e-4)

    def test_extended_and_chebyshev_policies_reduce_scalar_event_counts(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (1.0 - state[0],),
            0.0,
            (0.0,),
            5.0,
            name="published-generalised-liqss-scalar",
            autonomous=True,
        )
        jacobian = lambda _time, _state: ((-1.0,),)
        standard = [
            solver(problem, 1.0e-2, jacobian=jacobian)
            for solver in (liqss1, liqss2, liqss3)
        ]
        extended = [
            solver(problem, 1.0e-2, jacobian=jacobian)
            for solver in (eliqss1, eliqss2, eliqss3)
        ]
        chebyshev = [
            solver(problem, 1.0e-2, jacobian=jacobian)
            for solver in (cheqss1, cheqss2, cheqss3)
        ]

        self.assertEqual(extended[0].times, chebyshev[0].times)
        self.assertEqual(extended[0].states, chebyshev[0].states)
        for old, new in zip(standard, extended):
            self.assertLess(new.stats.accepted_steps, old.stats.accepted_steps)
        for old, new in zip(standard, chebyshev):
            self.assertLess(new.stats.accepted_steps, old.stats.accepted_steps)
        self.assertLess(
            chebyshev[1].stats.accepted_steps,
            extended[1].stats.accepted_steps,
        )
        self.assertLess(
            chebyshev[2].stats.accepted_steps,
            extended[2].stats.accepted_steps,
        )
        exact = 1.0 - math.exp(-5.0)
        for result in (*extended, *chebyshev):
            self.assertLess(abs(result.final_state[0] - exact), 1.1e-2)

    def test_chebyshev_difference_polynomials_are_uniformly_bounded(self) -> None:
        quantum = 0.25
        horizon = 0.7
        for order in (1, 2, 3):
            with self.subTest(order=order):
                polynomial = _difference_coefficients(
                    "chebyshev", order, quantum, horizon
                )
                errors = [
                    sum(
                        coefficient * (horizon * sample / 1000.0) ** power
                        for power, coefficient in enumerate(polynomial)
                    )
                    for sample in range(1001)
                ]
                self.assertLessEqual(max(map(abs, errors)), quantum + 1.0e-12)
                self.assertAlmostEqual(abs(errors[0]), quantum)
                self.assertAlmostEqual(abs(errors[-1]), quantum)

    def test_horizon_root_keeps_small_root_with_remote_second_root(self) -> None:
        # The second root is about -8e28; scaling the whole interval to that
        # root must not discard the physically relevant root at t=2.
        root = _first_positive_unbounded_root((-16.0, 8.0, 1.0e-28))
        self.assertAlmostEqual(root, 2.0)

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
            "eliqss",
            "eliqss2",
            "eliqss3",
            "cheqss",
            "cheqss2",
            "cheqss3",
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
        self.assertEqual(normalise_solver_name("eLIQSS"), "eliqss1")
        self.assertEqual(normalise_solver_name("EQSS2"), "eliqss2")
        self.assertEqual(normalise_solver_name("CheQSS"), "cheqss1")

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
