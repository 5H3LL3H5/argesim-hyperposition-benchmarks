import unittest

from argesim_benchmarks.catalog import BENCHMARKS, BenchmarkStatus
from argesim_benchmarks.models.cp1_parallel import (
    CP1_TASK_B_EQUILIBRIUM,
    CP1_TASK_B_TERMINAL_VALUES,
    cp1_task_a_ivp,
    cp1_task_a_study,
    cp1_task_b_compare_execution,
    cp1_task_b_ivp,
    cp1_task_b_rhs,
    cp1_task_c_ivp,
    cp1_task_c_solve,
)
from argesim_benchmarks.solvers import rk45


class CP1Tests(unittest.TestCase):
    def test_cp1_catalog_status_reflects_external_table_validation(self) -> None:
        cp1 = next(b for b in BENCHMARKS if b.identifier == "CP1")
        self.assertEqual(cp1.status, BenchmarkStatus.VALIDATED)

    def test_task_a_ivp_creation(self) -> None:
        ivp = cp1_task_a_ivp(1000.0)
        self.assertEqual(ivp.dimension, 2)
        self.assertEqual(ivp.t_bound, 2.0)
        self.assertEqual(ivp.y0, (0.1, 0.0))
        # Evaluate RHS at initial state
        derivative = ivp.evaluate(0.0, ivp.y0)
        # x' = v = 0.0
        # v' = (-9000 * 0.1 - 1000 * 0.0) / 450 = -900 / 450 = -2.0
        self.assertEqual(derivative, (0.0, -2.0))

    def test_task_b_ivp_creation(self) -> None:
        ivp = cp1_task_b_ivp()
        self.assertEqual(ivp.dimension, 10)
        self.assertEqual(ivp.t_bound, 100.0)
        self.assertEqual(ivp.y0, (1.0,) * 10)
        derivative = ivp.evaluate(0.0, ivp.y0)
        self.assertEqual(len(derivative), 10)

    def test_task_b_steady_state(self) -> None:
        eq_state = (
            CP1_TASK_B_EQUILIBRIUM["v1"],
            CP1_TASK_B_EQUILIBRIUM["v2"],
            CP1_TASK_B_EQUILIBRIUM["w1"],
            CP1_TASK_B_EQUILIBRIUM["w2"],
            CP1_TASK_B_EQUILIBRIUM["x1"],
            CP1_TASK_B_EQUILIBRIUM["x2"],
            CP1_TASK_B_EQUILIBRIUM["y1"],
            CP1_TASK_B_EQUILIBRIUM["y2"],
            CP1_TASK_B_EQUILIBRIUM["z1"],
            CP1_TASK_B_EQUILIBRIUM["z2"],
        )
        rhs = cp1_task_b_rhs()
        derivative = rhs(0.0, eq_state)
        # Check that derivative at equilibrium is close to 0
        max_drv = max(abs(x) for x in derivative)
        self.assertLess(max_drv, 0.001)

    def test_task_b_integration_approaches_table_values(self) -> None:
        ivp = cp1_task_b_ivp(t_bound=100.0)
        result = rk45(ivp)
        self.assertEqual(result.final_time, 100.0)

        expected_terminal = (
            CP1_TASK_B_TERMINAL_VALUES["v1"],
            CP1_TASK_B_TERMINAL_VALUES["v2"],
            CP1_TASK_B_TERMINAL_VALUES["w1"],
            CP1_TASK_B_TERMINAL_VALUES["w2"],
            CP1_TASK_B_TERMINAL_VALUES["x1"],
            CP1_TASK_B_TERMINAL_VALUES["x2"],
            CP1_TASK_B_TERMINAL_VALUES["y1"],
            CP1_TASK_B_TERMINAL_VALUES["y2"],
            CP1_TASK_B_TERMINAL_VALUES["z1"],
            CP1_TASK_B_TERMINAL_VALUES["z2"],
        )

        for candidate, expected in zip(result.final_state, expected_terminal):
            # Independent table values agree to roughly five decimal places.
            self.assertAlmostEqual(candidate, expected, delta=1.1e-5)

    def test_task_c_ivp_creation(self) -> None:
        # Test with a small N to make it fast
        interior_points = 9  # N = 10
        ivp = cp1_task_c_ivp(interior_points, t_bound=30.0)
        self.assertEqual(ivp.dimension, 18)  # 9 positions, 9 velocities
        self.assertEqual(ivp.t_bound, 30.0)
        self.assertEqual(ivp.y0, (0.0,) * 18)
        derivative = ivp.evaluate(0.0, ivp.y0)
        self.assertEqual(len(derivative), 18)

    def test_complete_parallel_workloads_are_numerically_identical(self) -> None:
        task_a = cp1_task_a_study(
            samples=8,
            t_bound=0.02,
            step=0.001,
            output_step=0.01,
            workers=2,
        )
        self.assertEqual(task_a.execution.maximum_error, 0.0)
        task_b = cp1_task_b_compare_execution(t_bound=0.05, step=0.01, workers=2)
        self.assertEqual(task_b.maximum_error, 0.0)
        serial = cp1_task_c_solve(
            interior_points=9,
            t_bound=0.01,
            step=0.005,
            output_step=0.005,
            workers=1,
        )
        parallel = cp1_task_c_solve(
            interior_points=9,
            t_bound=0.01,
            step=0.005,
            output_step=0.005,
            workers=2,
        )
        self.assertEqual(serial.displacement, parallel.displacement)

if __name__ == "__main__":
    unittest.main()
