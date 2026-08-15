import math
import unittest

from argesim_benchmarks import InitialValueProblem
from argesim_benchmarks.runtime import (
    merge_integration_results,
    solve_ivp,
)


class ContinuousRuntimeTests(unittest.TestCase):
    @staticmethod
    def decay_problem(t0=0.0, y0=(1.0,), t_bound=1.0):
        return InitialValueProblem(
            lambda _time, state: (-state[0],),
            t0,
            y0,
            t_bound,
            autonomous=True,
        )

    def test_dispatches_independent_classical_and_qss_backends(self):
        defaults = {
            "euler": {"step": 1.0e-3},
            "rk4": {"step": 1.0e-2},
            "rk45": {"max_step": 0.1},
            "qss1": {"quantum": 1.0e-3},
            "qss2": {"quantum": 1.0e-3},
        }
        for method in defaults:
            with self.subTest(method=method):
                result = solve_ivp(
                    self.decay_problem(),
                    method,
                    defaults=defaults,
                )
                self.assertTrue(result.method.startswith(method))
                self.assertAlmostEqual(result.final_state[0], math.exp(-1.0), delta=0.003)

    def test_unknown_options_are_not_silently_ignored(self):
        with self.assertRaisesRegex(TypeError, "unsupported rk45 option"):
            solve_ivp(
                self.decay_problem(),
                "rk45",
                options={"max_stpe": 0.1},
            )

    def test_contiguous_segments_merge_once_at_the_boundary(self):
        first = solve_ivp(
            self.decay_problem(t_bound=0.5),
            "rk45",
            options={"max_step": 0.1},
        )
        second = solve_ivp(
            self.decay_problem(0.5, first.final_state, 1.0),
            "rk45",
            options={"max_step": 0.1},
        )
        merged = merge_integration_results((first, second))
        self.assertEqual(merged.times.count(0.5), 1)
        self.assertEqual(
            merged.stats.accepted_steps,
            first.stats.accepted_steps + second.stats.accepted_steps,
        )


if __name__ == "__main__":
    unittest.main()
