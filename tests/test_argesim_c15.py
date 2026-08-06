import unittest
import math

from argesim_benchmarks.models.c15_clearance import (
    C15Bolus,
    C15Parameters,
    c15_analytical,
    c15_rhs,
    c15_task_a,
    c15_task_b,
    c15_task_c,
    solve_c15,
)


class C15Tests(unittest.TestCase):
    def test_rhs_matches_equations(self) -> None:
        params = C15Parameters(k01=0.1, k21=0.2, k12=0.3, v1=1.0)
        bolus = C15Bolus(d=10.0, tau=2.0)
        rhs = c15_rhs(params, bolus)

        # t < tau
        d_x1, d_x2 = rhs(1.0, (2.0, 3.0))
        # f(t) = 10.0 / 2.0 = 5.0
        # dx1/dt = 5.0 - (0.1 + 0.2)*2.0 + 0.3*3.0 = 5.0 - 0.6 + 0.9 = 5.3
        self.assertAlmostEqual(d_x1, 5.3)
        # dx2/dt = 0.2*2.0 - 0.3*3.0 = 0.4 - 0.9 = -0.5
        self.assertAlmostEqual(d_x2, -0.5)

        # t >= tau
        d_x1, d_x2 = rhs(3.0, (2.0, 3.0))
        # f(t) = 0.0
        # dx1/dt = 0.0 - 0.6 + 0.9 = 0.3
        self.assertAlmostEqual(d_x1, 0.3)
        self.assertAlmostEqual(d_x2, -0.5)

    def test_analytical_matches_numerical(self) -> None:
        params = C15Parameters(k01=0.1, k21=0.2, k12=0.3, v1=1.0)
        bolus = C15Bolus(d=10.0, tau=2.0)
        t_test = 5.0

        ana_x1, ana_x2 = c15_analytical(t_test, params, bolus)

        num_res = solve_c15("rk45", parameters=params, bolus=bolus, t_bound=t_test, options={"max_step": 0.01})
        num_x1, num_x2 = num_res.final_state

        self.assertAlmostEqual(ana_x1, num_x1, places=3)
        self.assertAlmostEqual(ana_x2, num_x2, places=3)

    def test_task_a_returns_all_bolus_configurations(self) -> None:
        results = c15_task_a()
        self.assertEqual(len(results), 3)
        self.assertIn("tau_0_5", results)
        self.assertIn("tau_3_0", results)
        self.assertIn("tau_240", results)

        for name, res in results.items():
            self.assertEqual(res.final_time, 240.0)
            self.assertEqual(len(res.states[0]), 2)
            self.assertGreater(res.final_state[0], 0.0)

    def test_task_b_identifies_parameters_successfully(self) -> None:
        res = c15_task_b()
        self.assertIn("k01", res)
        self.assertIn("k21", res)
        self.assertIn("k12", res)
        self.assertIn("v1", res)
        self.assertIn("clearance", res)
        self.assertIn("residuum", res)

        # Check that it converged to reasonable positive values
        self.assertGreater(res["k01"], 0.0)
        self.assertGreater(res["v1"], 0.0)
        self.assertGreater(res["clearance"], 0.0)

    def test_task_c_monte_carlo_runs_successfully(self) -> None:
        # Run with fewer iterations for test speed
        stats = c15_task_c(iterations=5)
        for param in ["k01", "k21", "k12", "v1"]:
            self.assertIn(param, stats)
            self.assertIn("mean", stats[param])
            self.assertIn("deviation", stats[param])
            self.assertGreater(stats[param]["mean"], 0.0)

    def test_invalid_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            C15Parameters(k01=-0.1)
        with self.assertRaises(ValueError):
            C15Bolus(d=-1.0, tau=1.0)
        with self.assertRaises(ValueError):
            C15Bolus(d=1.0, tau=0.0)


if __name__ == "__main__":
    unittest.main()
