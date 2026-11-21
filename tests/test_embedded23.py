"""Independent order, stability, nonlinear, and retry checks for both RK pairs."""

import itertools
import math
import unittest

from argesim_benchmarks import (
    InitialValueProblem,
    IntegrationError,
    esdirk32,
    rk23,
    solve_ivp,
)


class Embedded23Tests(unittest.TestCase):
    def test_order_three_on_a_nonautonomous_nonlinear_solution(self):
        # y = 1 / (1+t²), y' = -2t y². Binary step sizes give exact mesh points.
        p = InitialValueProblem(lambda t, y: (-2 * t * y[0] ** 2,), 0, (1,), 1)
        for solver in (rk23, esdirk32):
            errors = []
            for n in (32, 64, 128):
                r = solver(p, initial_step=1 / n, max_step=1 / n, rtol=0.02, atol=1e-6)
                self.assertEqual(r.stats.accepted_steps, n)
                errors.append(abs(r.final_state[0] - 0.5))
            with self.subTest(solver=solver.__name__, errors=errors):
                for coarse, fine in itertools.pairwise(errors):
                    self.assertGreater(math.log2(coarse / fine), 2.8)
                    self.assertLess(math.log2(coarse / fine), 3.2)

    def test_embedded_second_order_error_scales_as_h_cubed(self):
        from argesim_benchmarks.solvers.embedded23 import _esdirk_trial, _rk23_trial

        # Integrating y'=t² tests quadrature order independently of the stage solver.
        p = InitialValueProblem(lambda t, y: (t * t,), 0, (0,), 1)
        for trial in (_rk23_trial, _esdirk_trial):
            errors = []
            for h in (0.25, 0.125, 0.0625):
                kw = (
                    {"jacobian": None, "jacobian_step": 1e-6, "iterations": 8}
                    if trial is _esdirk_trial
                    else {}
                )
                high, low, _ = trial(p, 0, (0.0,), h, (0.0,), (1e-9,), 1e-6, **kw)
                self.assertAlmostEqual(high[0], h**3 / 3, places=14)
                errors.append(abs(low[0] - h**3 / 3))
            for coarse, fine in itertools.pairwise(errors):
                self.assertAlmostEqual(coarse / fine, 8, places=10)

    def test_one_step_matches_independent_stability_functions(self):
        gamma = 0.435866521508459
        for z in (-2.0, -100.0, -10000.0):
            p = InitialValueProblem(lambda t, y, z=z: (z * y[0],), 0, (1,), 1)
            implicit = (
                1 + (1 - 3 * gamma) * z + (0.5 - 3 * gamma + 3 * gamma**2) * z**2
            ) / (1 - gamma * z) ** 3
            explicit = 1 + z + z * z / 2 + z**3 / 6
            for solver, ref in ((esdirk32, implicit), (rk23, explicit)):
                kw = (
                    {"jacobian": lambda t, y, z=z: ((z,),)}
                    if solver is esdirk32
                    else {}
                )
                r = solver(p, initial_step=1, rtol=1e6, atol=1, **kw)
                self.assertEqual(r.stats.accepted_steps, 1)
                self.assertTrue(
                    math.isclose(r.final_state[0], ref, rel_tol=2e-9, abs_tol=2e-12)
                )
        self.assertLess(abs(implicit), 0.001)
        self.assertGreater(abs(explicit), 1e9)

    def test_stiff_forced_solution_with_and_without_a_jacobian(self):
        rate = 2e4

        # An attracting nonlinear slow manifold. The exact solution is cos(t).
        def rhs(t, y):
            d = y[0] - math.cos(t)
            return (-math.sin(t) - rate * (d + d**3),)

        def jac(t, y):
            return ((-rate * (1 + 3 * (y[0] - math.cos(t)) ** 2),),)

        p = InitialValueProblem(rhs, 0.5, (math.cos(0.5),), 3)
        for j in (None, jac):
            r = esdirk32(p, jacobian=j, rtol=1e-6, atol=1e-9, max_step=0.25)
            self.assertLess(
                max(abs(y[0] - math.cos(t)) for t, y in zip(r.times, r.states)), 1e-6
            )
            self.assertLess(r.stats.accepted_steps, 100)

    def test_singular_trial_rolls_back_and_charges_a_rejection(self):
        gamma = 0.435866521508459
        h = 0.25
        lam = 1 / (gamma * h)
        times, calls = [], []

        def rhs(t, y):
            calls.append(t)
            return (lam * y[0],)

        def observe(t0, y0, t, y):
            times.append(t)
            return False

        p = InitialValueProblem(rhs, 0, (1,), h, _stop_after_step=observe)
        kw = {
            "initial_step": h,
            "jacobian": lambda t, y: ((lam,),),
            "rtol": 1e-6,
            "atol": 1e-9,
        }
        r = esdirk32(p, **kw)
        self.assertGreater(r.stats.rejected_steps, 0)
        self.assertEqual(r.stats.rhs_evaluations, len(calls))
        self.assertEqual(tuple(times), r.times[1:])
        self.assertLess(abs(r.final_state[0] / math.exp(lam * h) - 1), 1e-5)
        with self.assertRaises(IntegrationError):
            esdirk32(p, max_steps=1, **kw)
        with self.assertRaisesRegex(IntegrationError, "min_step"):
            esdirk32(p, min_step=h, **kw)

    def test_pivoted_stage_matrix_on_a_coupled_system(self):
        # First diagonal entry of I-h*gamma*J is zero; a row exchange is necessary.
        gamma = 0.435866521508459
        a = 1 / gamma
        p = InitialValueProblem(
            lambda t, y: (a * y[0] - 2 * a * y[1], a * y[0] - 2 * a * y[1]),
            0,
            (1, 1),
            1,
        )
        kw = {"initial_step": 1, "rtol": 4.0, "atol": 1.0}
        r = esdirk32(p, jacobian=lambda t, y: ((a, -2 * a), (a, -2 * a)), **kw)
        ref = esdirk32(
            InitialValueProblem(lambda t, y: (-a * y[0],), 0, (1,), 1),
            jacobian=lambda t, y: ((-a,),),
            **kw,
        )
        self.assertEqual(r.stats.accepted_steps, 1)
        for v in r.final_state:
            self.assertAlmostEqual(v, ref.final_state[0], places=12)

    def test_fsal_work_tolerances_dispatch_and_stop(self):
        for name in ("rk23", "esdirk32"):
            calls = []

            def rhs(t, y, calls=calls):
                calls.append(t)
                return (-80 * y[0], y[0])

            p = InitialValueProblem(
                rhs, 0, (1, 0), 2, _stop_after_step=lambda a, b, t, y: t >= 0.3
            )
            r = solve_ivp(
                p,
                name,
                defaults={"rk45": {"initial_step": 1, "rtol": 1e-5}},
                options={"atol": (1e-8, 1e-9)},
            )
            self.assertGreaterEqual(r.final_time, 0.3)
            self.assertLess(r.final_time, 2)
            self.assertEqual(r.stats.rhs_evaluations, len(calls))
            self.assertGreater(r.stats.rejected_steps, 0)
            if name == "rk23":
                self.assertEqual(
                    len(calls),
                    1 + 3 * (r.stats.accepted_steps + r.stats.rejected_steps),
                )
            self.assertLess(abs(r.final_state[0] + 80 * r.final_state[1] - 1), 1e-11)
            with self.assertRaises(ValueError):
                solve_ivp(p, name, options={"atol": (1e-6,)})
        with self.assertRaises(TypeError):
            solve_ivp(p, "rk23", options={"jacobian": lambda t, y: ()})
        with self.assertRaisesRegex(ValueError, "dimensions"):
            esdirk32(p, jacobian=lambda t, y: ((1,),))
        with self.assertRaises(ValueError):
            esdirk32(p, max_newton_iterations=0)

    def test_nonfinite_explicit_trial_recovers_without_an_invalid_accepted_state(self):
        invalid = []

        def rhs(t, y):
            if abs(y[0]) > 3:
                invalid.append(t)
                return (math.inf,)
            return (-30 * y[0] ** 3,)

        r = rk23(
            InitialValueProblem(rhs, 0, (1,), 0.5),
            initial_step=0.5,
            rtol=1e-6,
            atol=1e-9,
        )
        self.assertTrue(invalid)
        self.assertGreaterEqual(r.stats.rejected_steps, 1)
        self.assertLess(abs(r.final_state[0] - 1 / math.sqrt(31)), 1e-6)
        self.assertTrue(all(0 < y[0] <= 1 for y in r.states))

    def test_model_entry_points_align_ramps_and_forcing_switches(self):
        from argesim_benchmarks.models.c03_amplifier import C03Parameters, solve_c03
        from argesim_benchmarks.models.c19_groundwater import C19Parameters, solve_c19

        p = C03Parameters(trf=1e-6, r_off=2.0)
        tref = solve_c03("rk45", parameters=p, t_bound=8e-6)
        hour = 3600
        for method in ("rk23", "esdirk32"):
            actual = solve_c03(method, parameters=p, t_bound=tref.final_time)
            for value, ref in zip(actual.final_state, tref.final_state):
                self.assertAlmostEqual(value, ref, delta=1e-5)
            scheduled = solve_c19(
                method,
                nx=2,
                ny=2,
                x_offset=39,
                y_offset=4,
                initial_state=[1] * 4,
                facility_mode="schedule",
                t_bound=21 * hour,
                max_step=30 * hour,
                options={"rtol": 1e-8, "atol": 1e-10},
            )
            self.assertIn(8 * hour, scheduled.times)
            self.assertIn(20 * hour, scheduled.times)
            for value in scheduled.final_state:
                self.assertAlmostEqual(
                    value, math.exp(-C19Parameters().degradation * 9 * hour), delta=1e-7
                )

    def test_finite_difference_rhs_counts_and_short_final_interval(self):
        for jac in (None, lambda t, y: ((0.0,),)):
            count = []

            def rhs(t, y, count=count):
                count.append(t)
                return (2.0,)

            p = InitialValueProblem(rhs, 2.0, (0,), 2.125)
            r = esdirk32(p, initial_step=1, min_step=0.25, jacobian=jac)
            self.assertEqual(r.final_time, 2.125)
            self.assertAlmostEqual(r.final_state[0], 0.25)
            self.assertEqual(r.stats.rhs_evaluations, len(count))
            if jac is None:
                fd_calls = len(count)
            else:
                self.assertEqual(fd_calls, len(count) + 2)
