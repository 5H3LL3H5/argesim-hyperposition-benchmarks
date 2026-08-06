import unittest
import math

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus
from argesim_benchmarks.models.cp2_parallel_and_distributed import (
    CP2MonteCarloParameters,
    cp2_monte_carlo_problem,
    cp2_lbm_initial_state,
    cp2_lbm_step,
    CP2SwingingRopeParameters,
    cp2_swinging_rope_problem,
)


class CP2Tests(unittest.TestCase):
    def test_cp2_catalog_status(self) -> None:
        cp2 = next(b for b in BENCHMARKS if b.identifier == "CP2")
        self.assertEqual(cp2.status, BenchmarkStatus.IMPLEMENTED)

    def test_monte_carlo_parameters_must_be_positive_and_finite(self) -> None:
        with self.assertRaises(ValueError):
            CP2MonteCarloParameters(mass=-1.0)
        with self.assertRaises(ValueError):
            CP2MonteCarloParameters(stiffness=0.0)
        with self.assertRaises(ValueError):
            CP2MonteCarloParameters(damping=math.inf)

    def test_monte_carlo_rhs_evaluates_correctly(self) -> None:
        parameters = CP2MonteCarloParameters(mass=10.0, stiffness=20.0, damping=5.0)
        problem = cp2_monte_carlo_problem(parameters=parameters)
        self.assertEqual(problem.y0, (0.0, 0.1))

        # At (position=1.0, velocity=2.0)
        # expected_derivative = (velocity, -d/m*velocity - k/m*position)
        # = (2.0, -5.0/10.0*2.0 - 20.0/10.0*1.0) = (2.0, -1.0 - 2.0) = (2.0, -3.0)
        derivative = problem.evaluate(0.0, (1.0, 2.0))
        self.assertEqual(derivative, (2.0, -3.0))

    def test_lbm_initial_state_and_step(self) -> None:
        nx = 3
        grid = cp2_lbm_initial_state(nx)
        self.assertEqual(len(grid), nx)
        self.assertEqual(len(grid[0]), nx)
        self.assertEqual(len(grid[0][0]), 9)
        self.assertAlmostEqual(sum(grid[0][0]), 1.0)

        # One step of LBM with omega = 1.0 and u0_x = 0.1
        new_grid = cp2_lbm_step(grid, nx, omega=1.0, u0_x=0.1)
        self.assertEqual(len(new_grid), nx)
        self.assertEqual(len(new_grid[0]), nx)
        self.assertEqual(len(new_grid[0][0]), 9)

        # Mass should be conserved overall
        initial_mass = sum(sum(sum(f) for f in row) for row in grid)
        final_mass = sum(sum(sum(f) for f in row) for row in new_grid)
        self.assertAlmostEqual(initial_mass, final_mass)

        # Check that top boundary is set by moving wall eq (x=1, y=2)
        top_middle = new_grid[2][1]
        rho_tm = sum(top_middle)
        self.assertAlmostEqual(rho_tm, 1.0)

    def test_swinging_rope_parameters_must_be_positive(self) -> None:
        with self.assertRaises(ValueError):
            CP2SwingingRopeParameters(nu=0.0)
        with self.assertRaises(ValueError):
            CP2SwingingRopeParameters(length=-0.5)
        with self.assertRaises(ValueError):
            CP2SwingingRopeParameters(interior_points=0)

    def test_swinging_rope_problem_setup(self) -> None:
        params = CP2SwingingRopeParameters(nu=1.0, length=2.0, h=0.5, interior_points=3)
        problem = cp2_swinging_rope_problem(parameters=params)

        # 3 points -> spacing = 2.0 / 4 = 0.5. Points at x = 0.5, 1.0, 1.5
        # h = 0.5, L = 2.0
        # x = 0.5 (x <= L/2): 2*0.5/2.0 * 0.5 = 0.25
        # x = 1.0 (x <= L/2): 2*0.5/2.0 * 1.0 = 0.5
        # x = 1.5 (x > L/2): 2*0.5 * (1.0 - 1.5/2.0) = 1.0 * 0.25 = 0.25

        expected_u0 = (0.25, 0.5, 0.25)
        expected_v0 = (0.0, 0.0, 0.0)

        self.assertEqual(problem.y0, expected_u0 + expected_v0)
        self.assertEqual(problem.dimension, 6)

if __name__ == "__main__":
    unittest.main()
