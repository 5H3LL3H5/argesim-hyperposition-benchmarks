import math
import unittest

from argesim_benchmarks import InitialValueProblem, euler, rk4, rk45
from argesim_benchmarks.ivp import (
    IntegrationError,
    IntegrationResult,
    SolverStats,
)


def decay_problem(t_bound: float = 1.0) -> InitialValueProblem:
    return InitialValueProblem(
        lambda _time, state: (-state[0],),
        0.0,
        (1.0,),
        t_bound,
        name="exponential-decay",
        autonomous=True,
    )


class ExplicitSolverTests(unittest.TestCase):
    def test_euler_has_first_order_endpoint_convergence(self) -> None:
        exact = math.exp(-1.0)
        errors = [
            abs(euler(decay_problem(), step).final_state[0] - exact)
            for step in (0.1, 0.05, 0.025)
        ]
        self.assertGreater(errors[0] / errors[1], 1.9)
        self.assertGreater(errors[1] / errors[2], 1.9)

    def test_rk4_has_fourth_order_endpoint_convergence(self) -> None:
        exact = math.exp(-1.0)
        coarse = abs(rk4(decay_problem(), 0.2).final_state[0] - exact)
        fine = abs(rk4(decay_problem(), 0.1).final_state[0] - exact)
        self.assertGreater(coarse / fine, 14.0)
        self.assertLess(coarse / fine, 18.0)

    def test_fixed_step_methods_clip_the_last_step_to_t_bound(self) -> None:
        for solve in (euler, rk4):
            result = solve(decay_problem(1.0), 0.3)
            self.assertEqual(result.final_time, 1.0)
            self.assertEqual(result.stats.accepted_steps, 4)

    def test_rk45_controls_error_and_rejects_an_oversized_initial_step(self) -> None:
        result = rk45(
            decay_problem(10.0),
            initial_step=10.0,
            rtol=1e-9,
            atol=1e-12,
        )
        self.assertEqual(result.final_time, 10.0)
        self.assertGreater(result.stats.rejected_steps, 0)
        self.assertAlmostEqual(result.final_state[0], math.exp(-10.0), delta=2e-12)

    def test_rk45_vector_atol_through_dispatcher(self) -> None:
        from argesim_benchmarks.runtime import solve_ivp

        problem = InitialValueProblem(
            lambda t, y: (-y[0], -2.0 * y[1]), 0, (1e6, 1e-6), 2
        )
        result = solve_ivp(problem, "rk45", options={
            "rtol": 1e-9, "atol": (1e-5, 1e-15), "initial_step": 2.0,
        })
        self.assertAlmostEqual(result.final_state[0] / 1e6, math.exp(-2), delta=1e-9)
        self.assertAlmostEqual(result.final_state[1] / 1e-6, math.exp(-4), delta=1e-9)
        scalar = rk45(decay_problem(), atol=1e-10)
        vector = rk45(decay_problem(), atol=(1e-10,))
        self.assertEqual(scalar, vector)

    def test_rk45_invalid_vector_tolerances_fail_before_rhs(self) -> None:
        def forbidden_rhs(t, y):
            self.fail("invalid tolerance must fail before evaluating the RHS")
        problem = InitialValueProblem(forbidden_rhs, 0, (1,), 1)
        for atol in ((), (1e-9, 1e-9), (0,), (-1,), (math.nan,), (math.inf,)):
            with self.subTest(atol=atol), self.assertRaises(ValueError):
                rk45(problem, atol=atol)
        with self.assertRaises(TypeError):
            rk45(problem, atol=(True,))

    def test_rk45_fsal_counts_calls_including_rejected_trials(self) -> None:
        calls = []
        def rhs(t, y):
            calls.append((t, tuple(y)))
            return (-y[0] + math.sin(t),)
        result = rk45(InitialValueProblem(rhs, 0, (1,), 10),
                      initial_step=10, rtol=1e-9, atol=1e-12)
        attempts = result.stats.accepted_steps + result.stats.rejected_steps
        self.assertGreater(result.stats.rejected_steps, 0)
        self.assertEqual(len(calls), 1 + 6 * attempts)
        self.assertEqual(result.stats.rhs_evaluations, len(calls))
        exact = 1.5 * math.exp(-10) + 0.5 * (math.sin(10) - math.cos(10))
        self.assertAlmostEqual(result.final_state[0], exact, delta=2e-9)
        # Cache is local to one integration, even when the same callable is reused.
        before = len(calls)
        again = rk45(InitialValueProblem(rhs, 0, (1,), 10),
                     initial_step=10, rtol=1e-9, atol=1e-12)
        self.assertEqual(again, result)
        self.assertEqual(len(calls) - before, result.stats.rhs_evaluations)

    def test_rk45_integrates_short_final_interval_with_error_control(self) -> None:
        result = rk45(decay_problem(), initial_step=0.3,
                      min_step=0.2, max_step=0.3, rtol=1e-3)
        self.assertEqual(result.final_time, 1.0)
        self.assertEqual(result.stats.accepted_steps, 4)
        self.assertAlmostEqual(result.final_state[0], math.exp(-1), delta=1e-6)
        tiny = rk45(InitialValueProblem(lambda t, y: (1,), 0, (0,), 1e-15))
        # Summation differs by one ULP on Python 3.10/3.11 versus 3.12+.
        # Keep a scale-aware bound that still rejects a skipped/zero interval.
        self.assertAlmostEqual(tiny.final_state[0], 1e-15, delta=2 * math.ulp(1e-15))
        # An inaccurate endpoint trial must not be accepted merely to finish.
        with self.assertRaises(IntegrationError):
            rk45(InitialValueProblem(lambda t, y: (-1e6 * y[0],), 0, (1,), 1e-6),
                 min_step=1e-5, rtol=1e-12, atol=1e-15)

    def test_rk45_error_norm_avoids_intermediate_square_overflow(self) -> None:
        from argesim_benchmarks.solvers.explicit import _rms_error

        norm = _rms_error((1e200, 1e200), (0, 0), (0, 0), (1, 1), 1e-6)
        self.assertTrue(math.isfinite(norm))
        self.assertAlmostEqual(norm / 1e200, 1.0)

    def test_rhs_dimension_mismatch_is_rejected(self) -> None:
        problem = InitialValueProblem(lambda _time, _state: (1.0, 2.0), 0, (0,), 1)
        with self.assertRaises(ValueError):
            euler(problem, 0.1)

    def test_evaluation_rejects_non_finite_inputs(self) -> None:
        problem = decay_problem()
        with self.assertRaises(ValueError):
            problem.evaluate(math.inf, (1.0,))
        with self.assertRaises(ValueError):
            problem.evaluate(0.0, (math.nan,))

    def test_step_limits_must_be_positive_integers(self) -> None:
        with self.assertRaises(TypeError):
            euler(decay_problem(), 0.1, max_steps=True)
        with self.assertRaises(TypeError):
            rk45(decay_problem(), max_steps=10.5)

    def test_non_finite_state_update_is_an_integration_error(self) -> None:
        maximum = float.fromhex("0x1.fffffffffffffp+1023")
        problem = InitialValueProblem(
            lambda _time, _state: (maximum,),
            0.0,
            (maximum,),
            1.0,
        )
        with self.assertRaises(IntegrationError):
            euler(problem, 1.0)

    def test_rk45_rejects_inconsistent_step_bounds(self) -> None:
        with self.assertRaises(ValueError):
            rk45(decay_problem(), min_step=0.5, max_step=0.25)

    def test_result_and_statistics_contracts_reject_invalid_samples(self) -> None:
        with self.assertRaises(TypeError):
            SolverStats(True, 0, 0)
        stats = SolverStats(1, 0, 1)
        with self.assertRaises(ValueError):
            IntegrationResult("test", (0.0, math.inf), ((0.0,), (1.0,)), stats)
        with self.assertRaises(ValueError):
            IntegrationResult("test", (0.0, 1.0), ((0.0,), (math.nan,)), stats)


if __name__ == "__main__":
    unittest.main()
