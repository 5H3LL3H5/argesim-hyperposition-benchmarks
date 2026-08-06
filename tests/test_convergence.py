import unittest
from itertools import pairwise

from nsa_devs import convergence_table, decay_euler_endpoint, decay_exact


class ConvergenceTests(unittest.TestCase):
    def test_finite_approximations_converge_without_claiming_zero_error(self) -> None:
        rows = convergence_table((10, 100, 1_000, 10_000))
        errors = [row.absolute_error for row in rows]

        self.assertTrue(all(error > 0.0 for error in errors))
        self.assertTrue(
            all(later < earlier for earlier, later in pairwise(errors))
        )
        self.assertLess(errors[-1], 2e-5)

    def test_endpoint_remains_below_exact_solution(self) -> None:
        exact = decay_exact()
        for steps in (2, 10, 100, 10_000):
            self.assertLess(decay_euler_endpoint(steps), exact)

    def test_invalid_step_count_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            decay_euler_endpoint(1)


if __name__ == "__main__":
    unittest.main()

