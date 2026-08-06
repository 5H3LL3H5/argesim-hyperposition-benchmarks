"""Tests for the ARGESIM C11 benchmark."""

import unittest

from argesim_benchmarks.models.c11_scara_robot import (
    C11_INITIAL_STATE,
    C11_TARGET_STATE,
    C11Parameters,
    solve_c11,
)

class C11Tests(unittest.TestCase):
    def test_invalid_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            solve_c11("unsupported")

    def test_task_b_runs_to_completion(self) -> None:
        result = solve_c11("rk45", t_bound=2.0)
        self.assertEqual(result.times[-1], 2.0)
        q1, q2, q3, dq1, dq2, dq3, I1, I2, I3 = result.states[-1]

        # Verify that it reaches the target reasonably well
        self.assertAlmostEqual(q1, C11_TARGET_STATE[0], places=1)
        self.assertAlmostEqual(q2, C11_TARGET_STATE[1], places=1)
        self.assertAlmostEqual(q3, C11_TARGET_STATE[2], places=1)

    def test_task_c_collision_avoidance(self) -> None:
        result = solve_c11("rk45", t_bound=2.0, task="c")
        self.assertEqual(result.times[-1], 2.0)

        q1, q2, q3, dq1, dq2, dq3, I1, I2, I3 = result.states[-1]
        self.assertAlmostEqual(q1, C11_TARGET_STATE[0], places=1)
        self.assertAlmostEqual(q2, C11_TARGET_STATE[1], places=1)
        self.assertAlmostEqual(q3, C11_TARGET_STATE[2], places=1)

if __name__ == "__main__":
    unittest.main()
