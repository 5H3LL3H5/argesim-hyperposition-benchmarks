import math
import unittest

from argesim_benchmarks import (
    heat_1d_ivp,
    heat_sine_exact,
    heat_sine_initial,
    rk4,
    wave_1d_ivp,
)


class MethodOfLinesTests(unittest.TestCase):
    def test_heat_equation_matches_the_first_analytic_mode(self) -> None:
        points = 15
        t_bound = 0.05
        initial = heat_sine_initial(points)
        problem = heat_1d_ivp(initial, t_bound)
        result = rk4(problem, 0.0001)
        exact = heat_sine_exact(points, t_bound)
        maximum_error = max(
            abs(candidate - reference)
            for candidate, reference in zip(result.final_state, exact)
        )
        self.assertLess(maximum_error, 1.5e-3)

    def test_wave_method_of_lines_has_expected_state_dimension(self) -> None:
        displacement = heat_sine_initial(7)
        problem = wave_1d_ivp(displacement, (0.0,) * 7, 0.1)
        result = rk4(problem, 0.001)
        self.assertEqual(len(result.final_state), 14)
        self.assertTrue(all(math.isfinite(value) for value in result.final_state))

    def test_mismatched_wave_initial_conditions_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            wave_1d_ivp((1.0, 2.0), (0.0,), 1.0)


if __name__ == "__main__":
    unittest.main()

