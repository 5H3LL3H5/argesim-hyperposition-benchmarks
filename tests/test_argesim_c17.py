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

    def test_solve_c17_long_term_equilibrium(self) -> None:
        # At very large t, I(t) should -> 0
        result = solve_c17("rk45", t_bound=300.0, options={"max_step": 1.0})
        self.assertEqual(result.final_time, 300.0)
        self.assertAlmostEqual(sum(result.final_state), sum(C17_INITIAL_STATE))

        S_final, I_final, R_final = result.final_state
        # Infections should have died out
        self.assertLess(I_final, 1.0)
        # R should make up the vast majority of the population
        self.assertGreater(R_final, 9000.0)
        # S should be the remainder
        self.assertAlmostEqual(S_final + I_final + R_final, sum(C17_INITIAL_STATE))

    def test_qss1_solve_c17(self) -> None:
        result = solve_c17("qss1", t_bound=1.0, options={"quantum": (1.0, 1.0, 1.0)})
        self.assertEqual(result.final_time, 1.0)

    def test_unsupported_solver(self) -> None:
        with self.assertRaises(ValueError):
            solve_c17("unsupported_solver")

if __name__ == '__main__':
    unittest.main()
