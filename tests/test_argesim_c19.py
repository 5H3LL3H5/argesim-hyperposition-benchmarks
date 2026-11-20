import math
import unittest
from unittest.mock import patch

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus
from argesim_benchmarks.ivp import IntegrationError
from argesim_benchmarks.models.c19_groundwater import (
    C19Parameters,
    _scaled_k0,
    c19_analytical_steady_state,
    c19_analytical_transient,
    c19_homogeneous_transient,
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
        self.assertAlmostEqual(math.exp(-0.5) * _scaled_k0(0.5), 0.9244, places=4)
        self.assertAlmostEqual(math.exp(-1.0) * _scaled_k0(1.0), 0.4210, places=4)
        self.assertAlmostEqual(math.exp(-2.5) * _scaled_k0(2.5), 0.0623, places=4)

    def test_table_one_parameters_and_independent_downstream_reference(self) -> None:
        # Revised definition, Table 1. Reference values use SciPy special.k0e.
        self.assertEqual(C19Parameters().pore_velocity_x, 1e-5)
        for x, y, expected in ((0.1, 0, 291435.13013990654), (50, 0, 14269.428686931555),
                               (100, 3, 6433.68184913152), (100000, 50, 281.6522108020774)):
            self.assertAlmostEqual(c19_analytical_steady_state(x, y) / expected, 1.0, delta=2e-7)
        self.assertAlmostEqual(c19_analytical_transient(50, 0, 50 * 86400), 0.02650022277315)
        self.assertEqual(c19_analytical_transient(50, 0, 100 * 86400, C19Parameters(retardation=2)),
                         c19_analytical_transient(50, 0, 50 * 86400))

    def test_homogeneous_breakthrough_matches_independent_heat_kernel_integral(self) -> None:
        # Independently integrated with SciPy quad after a Gaussian substitution.
        for day, expected in ((50, 7.606567833086095), (100, 14269.428686931553)):
            self.assertAlmostEqual(c19_homogeneous_transient(50, 0, day * 86400), expected, places=8)
        rows = c19_task_a(nx=7, ny=3, dx=10, dy=10, y_offset=-10, profiles=True)
        self.assertEqual(len(rows), 9)
        self.assertAlmostEqual(rows[1]["infinite_plane"], 7.606567833086095, places=10)
        self.assertEqual(rows[1]["mol_minus_printed"], rows[1]["mol"] - rows[1]["printed_approximation"])

    def test_source_only_enters_its_cell_and_injects_the_specified_mass(self) -> None:
        for offset, expected in ((-2.0, 1), (0.5, 0), (1.01, None), (-6.0, None)):
            with self.subTest(offset=offset):
                problem = c19_problem(nx=3, ny=2, dx=2, dy=3, x_offset=offset,
                                      y_offset=0, parameters=C19Parameters(retardation=2))
                rates = problem.evaluate(0, problem.y0)
                active = [i for i, rate in enumerate(rates) if rate]
                self.assertEqual(active, [] if expected is None else [expected])
                self.assertAlmostEqual(sum(rates) * 2 * 3 * 10 * .25 * 2,
                                       0 if expected is None else 2)

    def test_limited_flux_conserves_mass_across_internal_faces(self) -> None:
        p = c19_problem(nx=5, ny=2, dx=1, dy=1, x_offset=10, y_offset=10)
        values = (0, 2, 4, 5, 0, 0, 7, 5, 1, 0)
        self.assertAlmostEqual(sum(p.evaluate(0, values)), 0, delta=1e-18)

    def test_discrete_facility_area_matches_both_disks(self) -> None:
        # Shift the mesh so neither disk aligns with the grid. Uniform concentration
        # has zero transport RHS, so total loss measures the integrated disk areas.
        p = c19_problem(nx=12, ny=15, dx=1.5, dy=2, x_offset=32.4, y_offset=-13.3,
                        facility_mode="continuous")
        loss = -sum(p.evaluate(0, [1] * p.dimension)) * 1.5 * 2
        self.assertAlmostEqual(loss / C19Parameters().degradation, 2 * math.pi * 25)

    def test_schedule_hits_weekday_switches_and_integrates_through_the_weekend(self) -> None:
        hour = 3600
        args = {"nx": 2, "ny": 2, "x_offset": 39, "y_offset": 4, "initial_state": [1] * 4,
                "facility_mode": "schedule", "t_bound": 180 * hour}
        result = solve_c19(**args, max_step=100 * hour, options={"rtol": 1e-10, "atol": 1e-12})
        switches = [day * 24 + h for day in range(5) for h in (8, 20)] + [176]
        for t in switches:
            self.assertEqual(result.times.count(t * hour), 1)
        # Five weekday nights, two complete weekend days, next Monday morning.
        expected = math.exp(-C19Parameters().degradation * 116 * hour)
        for value in result.final_state:
            self.assertAlmostEqual(value, expected, delta=1e-9)
        with self.assertRaisesRegex(IntegrationError, "max_steps"):
            solve_c19("rk4", **args, options={"step": 100 * hour, "max_steps": 2})

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
