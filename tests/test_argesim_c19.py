import unittest
import math
from unittest.mock import patch

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus
from argesim_benchmarks.models.c19_groundwater import (
    C19Parameters,
    _k0_approx,
    c19_analytical_steady_state,
    c19_analytical_transient,
    c19_problem,
    c19_task_a,
    solve_c19,
)


class C19GroundwaterTests(unittest.TestCase):
    def test_c19r_catalog_status(self) -> None:
        c19r = next(b for b in BENCHMARKS if b.identifier == "C19R")
        self.assertEqual(c19r.status, BenchmarkStatus.IMPLEMENTED)

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

    def test_point_source_singularity_is_not_reported_as_zero(self) -> None:
        self.assertEqual(c19_analytical_steady_state(0.0, 0.0), math.inf)
        self.assertEqual(
            c19_analytical_transient(0.0, 0.0, 3600.0),
            math.inf,
        )

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

    def test_grid_and_transport_parameters_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            c19_problem(nx=1)
        with self.assertRaises(ValueError):
            c19_problem(dx=0.0)
        with self.assertRaises(ValueError):
            c19_problem(facility_mode="sometimes")
        with self.assertRaises(ValueError):
            C19Parameters(porosity=0.0)

    def test_task_a_runs_on_coarse_grid(self) -> None:
        # Run the shared dispatcher on a tiny grid and an independent RK4 backend.
        result = solve_c19(
            "rk4",
            nx=3,
            ny=3,
            t_bound=3600.0,
            options={"step": 900.0},
        )
        self.assertGreaterEqual(len(result.times), 2)
        self.assertEqual(len(result.final_state), 9)

    def test_schedule_task_refuses_non_autonomous_qss(self) -> None:
        with self.assertRaisesRegex(ValueError, "autonomous"):
            solve_c19(
                "qss2",
                nx=3,
                ny=3,
                facility_mode="schedule",
                t_bound=60.0,
                options={"quantum": 1.0e-3},
            )

    def test_continuous_task_covers_controlled_comparison_horizon(self) -> None:
        # C19R Task C requests both Task B and Task C at (50,0), 0..150 days.
        with patch(
            "argesim_benchmarks.models.c19_groundwater.solve_c19",
            return_value=object(),
        ) as solve:
            from argesim_benchmarks.models.c19_groundwater import c19_task_b

            c19_task_b(nx=3, ny=3)
        self.assertEqual(solve.call_args.kwargs["t_bound"], 150 * 24 * 3600)


if __name__ == "__main__":
    unittest.main()
