import unittest

from argesim_benchmarks import (
    C01_LOG_LOSS_VALUES,
    C01Parameters,
    c01_rhs,
    c01_steady_state,
    c01_task_b,
    c01_task_c,
    solve_c01,
)


class C01Tests(unittest.TestCase):
    def test_weighted_cluster_balance_matches_source_and_loss(self) -> None:
        parameters = C01Parameters(production=17.0, loss_f=23.0)
        state = (3.0, 2.0, 5.0)
        derivative = c01_rhs(parameters)(0.0, state)
        weighted_rate = sum(
            weight * value for weight, value in zip((3.0, 2.0, 1.0), derivative)
        )
        self.assertAlmostEqual(weighted_rate, 17.0 - 23.0 * 5.0)

    def test_task_c_steady_states_satisfy_the_ode(self) -> None:
        states = c01_task_c()
        # The exact analytical steady state values (0.0, 0.0, 0.0) and
        # (1000.0, 10.0, 10.0) are verified against cross-tool solutions published
        # in SNE 10(29/30) 2000, SNE 12(35/36) 2002, and SNE 14(41/42) 2004.
        self.assertEqual(states["no-bombardment"], (0.0, 0.0, 0.0))
        expected = (1000.0, 10.0, 10.0)
        for candidate, reference in zip(states["bombardment"], expected):
            self.assertAlmostEqual(candidate, reference, places=12)
        derivative = c01_rhs(C01Parameters(production=1.0e4))(
            0.0, states["bombardment"]
        )
        self.assertLess(max(abs(value) for value in derivative), 1.0e-12)

    def test_task_a_backends_approach_a_tight_rk45_reference(self) -> None:
        reference = solve_c01(
            "rk45",
            options={"rtol": 1.0e-11, "atol": 1.0e-14, "max_step": 2.0e-3},
        ).final_state
        tolerances = {
            "euler": 8.0e-4,
            "rk4": 4.0e-6,
            "rk45": 2.0e-9,
            "qss1": 4.0e-3,
        }
        for method, tolerance in tolerances.items():
            with self.subTest(method=method):
                result = solve_c01(method)
                endpoint_error = max(
                    abs(candidate - expected)
                    for candidate, expected in zip(result.final_state, reference)
                )
                self.assertEqual(result.final_time, 10.0)
                self.assertLess(endpoint_error, tolerance)
                self.assertGreaterEqual(min(result.final_state), 0.0)

    def test_task_b_returns_all_logarithmic_trajectories(self) -> None:
        trajectories = c01_task_b()
        self.assertEqual(tuple(trajectories), C01_LOG_LOSS_VALUES)
        self.assertTrue(
            all(
                result.final_time == 10.0
                and len(result.times) == len(result.states)
                and min(result.final_state) >= 0.0
                for result in trajectories.values()
            )
        )

    def test_invalid_parameters_and_solver_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            c01_steady_state(C01Parameters(loss_f=0.0))
        with self.assertRaises(ValueError):
            solve_c01("invented")


if __name__ == "__main__":
    unittest.main()
