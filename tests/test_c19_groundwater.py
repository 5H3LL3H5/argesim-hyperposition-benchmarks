import unittest
import math

from argesim_benchmarks.models.c19_groundwater import (
    C19Parameters,
    _k0_approx,
    c19_analytical_steady_state,
    c19_analytical_transient,
    c19_problem,
    c19_task_a,
)


class C19GroundwaterTests(unittest.TestCase):
    def test_k0_approximation_accuracy(self) -> None:
        # Check against known values of K0
        # K0(0.5) ~ 0.9244, K0(1.0) ~ 0.4210, K0(2.5) ~ 0.0623
        self.assertAlmostEqual(_k0_approx(0.5), 0.9244, places=4)
        self.assertAlmostEqual(_k0_approx(1.0), 0.4210, places=4)
        self.assertAlmostEqual(_k0_approx(2.5), 0.0623, places=4)

    def test_analytical_transient_is_zero_at_t_zero(self) -> None:
        val = c19_analytical_transient(10.0, 5.0, 0.0)
        self.assertEqual(val, 0.0)

    def test_analytical_transient_is_positive(self) -> None:
        val = c19_analytical_transient(10.0, 0.0, 10 * 24 * 3600)
        self.assertGreater(val, 0.0)

    def test_analytical_steady_state_positive(self) -> None:
        val = c19_analytical_steady_state(10.0, 0.0)
        self.assertGreater(val, 0.0)

    def test_c19_problem_creation(self) -> None:
        problem = c19_problem(nx=3, ny=3)
        self.assertEqual(problem.dimension, 9)
        self.assertTrue(problem.autonomous)

        # Check evaluation works
        der = problem.evaluate(0.0, [0.0] * 9)
        self.assertEqual(len(der), 9)

    def test_c19_problem_schedule_is_non_autonomous(self) -> None:
        problem = c19_problem(nx=3, ny=3, facility_mode="schedule")
        self.assertFalse(problem.autonomous)

    def test_task_a_runs_on_coarse_grid(self) -> None:
        # Just run a tiny grid for a short time to verify it doesn't crash
        problem = c19_problem(nx=3, ny=3, t_bound=3600.0)
        from argesim_benchmarks.solvers import rk45
        result = rk45(problem, max_step=3600.0)
        self.assertGreaterEqual(len(result.times), 2)
        self.assertEqual(len(result.final_state), 9)


if __name__ == "__main__":
    unittest.main()
