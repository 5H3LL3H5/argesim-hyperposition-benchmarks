import unittest
import math

from argesim_benchmarks.models.c17_sir_epidemic import (
    C17Parameters,
    c17_rhs,
    c17_problem,
    solve_c17,
    C17_INITIAL_STATE
)

class C17Tests(unittest.TestCase):
    def test_c17_parameters_validation(self) -> None:
        with self.assertRaises(ValueError):
            C17Parameters(n=0.0)
        with self.assertRaises(ValueError):
            C17Parameters(c=-1.0)
        with self.assertRaises(ValueError):
            C17Parameters(alpha=1.0)
        with self.assertRaises(ValueError):
            C17Parameters(beta=2.0)

    def test_c17_rhs_conservation(self) -> None:
        # S' + I' + R' should always be exactly 0
        rhs = c17_rhs()
        state = (100.0, 50.0, 20.0)
        derivative = rhs(0.0, state)
        self.assertAlmostEqual(sum(derivative), 0.0)
        # S should be strictly decreasing
        self.assertLess(derivative[0], 0.0)
        # R should be strictly increasing
        self.assertGreater(derivative[2], 0.0)

    def test_solve_c17(self) -> None:
        result = solve_c17("rk45", t_bound=10.0)
        self.assertEqual(result.final_time, 10.0)
        self.assertAlmostEqual(sum(result.final_state), sum(C17_INITIAL_STATE))
        # At t=10, check some expected movement
        # Since I0 is 500, infection should happen, so S decreases, R increases
        self.assertLess(result.final_state[0], C17_INITIAL_STATE[0])
        self.assertGreater(result.final_state[2], C17_INITIAL_STATE[2])

    def test_qss1_solve_c17(self) -> None:
        result = solve_c17("qss1", t_bound=1.0, options={"quantum": (1.0, 1.0, 1.0)})
        self.assertEqual(result.final_time, 1.0)

    def test_unsupported_solver(self) -> None:
        with self.assertRaises(ValueError):
            solve_c17("unsupported_solver")

if __name__ == '__main__':
    unittest.main()
