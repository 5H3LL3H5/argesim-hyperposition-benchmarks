import math
import unittest

from argesim_benchmarks import InitialValueProblem, euler, rk4, rk45


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

    def test_rhs_dimension_mismatch_is_rejected(self) -> None:
        problem = InitialValueProblem(lambda _time, _state: (1.0, 2.0), 0, (0,), 1)
        with self.assertRaises(ValueError):
            euler(problem, 0.1)


if __name__ == "__main__":
    unittest.main()
