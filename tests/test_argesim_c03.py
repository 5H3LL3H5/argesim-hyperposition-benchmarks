import unittest
from argesim_benchmarks import (
    C03Parameters,
    c03_rhs,
    c03_task_a,
    c03_task_b,
    c03_task_c,
    solve_c03,
)

class C03Tests(unittest.TestCase):
    def test_task_a_eigenvalues_match_theoretical_roots(self) -> None:
        result = c03_task_a()
        on_roots = result["ON"]
        off_roots = result["OFF"]

        # Test basic properties (number of roots and complex conjugacy)
        self.assertEqual(len(on_roots), 4)
        self.assertEqual(len(off_roots), 4)

        # In the ON state, there are 2 real roots and 1 complex conjugate pair
        real_on = [r for r in on_roots if abs(r.imag) < 1.0]
        self.assertEqual(len(real_on), 2)
        complex_on = [r for r in on_roots if abs(r.imag) >= 1.0]
        self.assertEqual(len(complex_on), 2)

        # Exact values from report (allowing some numerical tolerance)
        self.assertAlmostEqual(min(r.real for r in real_on), -1.117317e9, delta=1e4)
        self.assertAlmostEqual(max(r.real for r in real_on), -6.2578e2, delta=1.0)
        self.assertAlmostEqual(complex_on[0].real, -1.130388e5, delta=2.0)
        self.assertAlmostEqual(abs(complex_on[0].imag), 6.583522e5, delta=2.0)

        # In the OFF state, there are 2 complex conjugate pairs
        real_off = [r for r in off_roots if abs(r.imag) < 1.0]
        self.assertEqual(len(real_off), 0)

        # Check OFF state complex roots
        off_real_parts = sorted(list(set([round(r.real, 0) for r in off_roots])))
        self.assertAlmostEqual(off_real_parts[1], -54708.0, delta=2.0)
        self.assertAlmostEqual(off_real_parts[0], -58228.0, delta=2.0)

        # Both ON and OFF roots must be strictly stable (negative real parts)
        self.assertTrue(all(r.real < 0.0 for r in on_roots))
        self.assertTrue(all(r.real < 0.0 for r in off_roots))


    def test_rhs_initial_state(self) -> None:
        parameters = C03Parameters()
        state = (0.0, 0.0, 0.0, 0.0)
        derivative = c03_rhs(parameters)(0.0, state)
        # dx1 = (vdc - x2) / l1 = 5.0 / 79.9e-6
        self.assertAlmostEqual(derivative[0], 5.0 / 79.9e-6)
        self.assertEqual(derivative[1], 0.0)
        self.assertEqual(derivative[2], 0.0)
        self.assertEqual(derivative[3], 0.0)

    def test_task_b_integration_can_run(self) -> None:
        # We don't run the full 100e-6 with strict tolerances here to save time,
        # just a short burst to ensure the solvers can chew on the stiff logic
        result = solve_c03(
            method="rk45",
            t_bound=1.0e-6,
            options={"rtol": 1.0e-3, "atol": 1.0e-5, "max_step": 1.0e-7}
        )
        self.assertGreater(len(result.times), 2)
        self.assertAlmostEqual(result.times[-1], 1.0e-6)
        self.assertIn(C03Parameters().trf, result.times)


    def test_task_b_contract_reaches_official_horizon(self) -> None:
        result = c03_task_b(
            options={"rtol": 1.0e-4, "atol": 1.0e-6, "max_step": 1.0e-6}
        )
        self.assertAlmostEqual(result.final_time, 100.0e-6)
        self.assertEqual(result.times[0], 0.0)
        self.assertIn(C03Parameters().period * 0.5, result.times)

    def test_task_c_uses_official_rise_fall_parameter_study(self) -> None:
        initial_state = (1.0, 2.0, 3.0, 4.0)
        values = (1.0e-15, 1.0e-9)
        results = c03_task_c(
            values,
            initial_state=initial_state,
            options={"rtol": 1.0e-4, "atol": 1.0e-6, "max_step": 1.0e-6},
        )
        self.assertEqual(tuple(results), values)
        for result in results.values():
            self.assertEqual(result.states[0], initial_state)
            self.assertAlmostEqual(result.final_time, 9.0e-6)

    def test_invalid_parameters_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            C03Parameters(rl=0.0)
        with self.assertRaises(ValueError):
            C03Parameters(trf=6.0e-6)
