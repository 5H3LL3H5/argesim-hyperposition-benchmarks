import math
import unittest

from argesim_benchmarks import (
    InitialValueProblem,
    IntegrationError,
    bqss1,
    qss1,
    qss2,
    solve_ivp,
)
from argesim_benchmarks.hybrid import (
    HybridMode,
    HybridReset,
    StateEvent,
    StateThreshold,
    simulate_hybrid,
)


def problem(rhs, initial, end, start=0.0):
    return InitialValueProblem(rhs, start, initial, start + end, autonomous=True)


class BackwardQSSTests(unittest.TestCase):
    def test_stiff_published_first_two_events_and_quantum_refinement(self):
        # Migoni et al., eq. (3). Elimination gives x'' + 100 x' + x = 20.2.
        def rhs(t, y):
            return 0.01 * y[1], -100 * y[0] - 100 * y[1] + 2020

        p = problem(rhs, (0.0, 20.0), 1000)
        slow = -2 / (100 + math.sqrt(9996))
        fast = 1 / slow
        b = (0.2 + 20.2 * slow) / (fast - slow)
        a = -20.2 - b
        previous = math.inf
        for quantum in (1.0, 0.1, 0.01):
            result = bqss1(p, quantum)
            if quantum == 1:
                self.assertAlmostEqual(result.times[1], 1 / 0.21)
                self.assertAlmostEqual(result.times[2], 1 / 0.21 + 1 / 80)
                self.assertEqual(result.states[1], (1, 20))
                self.assertEqual(result.states[2][1], 19)
            errors = []
            for t, (x, y) in zip(result.times, result.states):
                u, v = a * math.exp(slow * t), b * math.exp(fast * t)
                errors.extend(
                    (abs(x - (20.2 + u + v)), abs(y - 100 * (slow * u + fast * v)))
                )
            error = max(errors)
            self.assertLess(error, 5.01 * quantum)
            self.assertLess(error, previous / 3)
            previous = error
            self.assertEqual(result.final_time, 1000)

    def test_freezes_exact_equilibrium_and_counts_actual_rhs_calls(self):
        for initial in ((0.0, 0.0), (1.0, -1.0)):
            calls = []

            def rhs(t, y, calls=calls):
                calls.append(t)
                return -10 * y[0], -10 * y[1]

            p = problem(rhs, initial, 2.0, start=2**24)
            r = solve_ivp(p, "bqss", options={"quantum": (0.125, 0.125)})
            self.assertEqual(r.stats.rhs_evaluations, len(calls))
            self.assertTrue(all(p.t0 <= t <= p.t_bound for t in calls))
            self.assertEqual(r.method, "bqss1")
            self.assertEqual(r.times[-1], p.t_bound)
            if initial == (0, 0):
                self.assertEqual(r.stats.accepted_steps, 0)
                self.assertEqual(r.final_state, initial)
            else:
                self.assertEqual(r.states[1], (0.875, -0.875))
                self.assertAlmostEqual(r.times[1] - p.t0, 0.125 / 8.75, places=7)
                self.assertLessEqual(max(map(abs, r.final_state)), 0.125)

    def test_simultaneous_budget_and_terminal_guard(self):
        p = problem(lambda t, y: (1.0, -1.0), (0.0, 0.0), 1)
        with self.assertRaisesRegex(IntegrationError, "max_events"):
            bqss1(p, 0.1, max_events=1)
        event = StateEvent(
            "stop",
            StateThreshold(0, 0.25),
            lambda t, y: HybridReset(y, terminate=True),
            "ramp",
            1,
        )
        mode = HybridMode("ramp", p.rhs, (event,))
        for method, options in (
            ("bqss1", {"quantum": 0.1}),
            ("qss2", {"quantum": 0.01, "relative_quantum": 0.02}),
        ):
            r = simulate_hybrid(
                {"ramp": mode},
                initial_mode="ramp",
                initial_state=p.y0,
                t_bound=1,
                method=method,
                solver_options=options,
            )
            self.assertEqual(len(r.events), 1)
            self.assertAlmostEqual(r.final_time, 0.25)
            self.assertAlmostEqual(r.final_state[1], -0.25)

    def test_nearly_coincident_opposing_ramps_keep_advancing(self):
        # Repeated additions on opposite grids can leave one hit below the
        # resolution of the clock near t=1 (also occurs in C12 free flight).
        p = problem(lambda t, y: (1.0, -1.0), (0.0, 1.0), 1.01)
        r = bqss1(p, 0.0002)
        self.assertAlmostEqual(r.final_state[0], 1.01, places=10)
        self.assertAlmostEqual(r.final_state[1], -0.01, places=10)
        self.assertTrue(all(a < b for a, b in zip(r.times, r.times[1:])))

    def test_coalescing_does_not_project_a_distant_fast_state(self):
        p = problem(lambda t, y: (1.0, 0.99), (0.0, 0.0), 0.11)
        r = bqss1(p, 0.1, simultaneous_tolerance=0.5)
        self.assertAlmostEqual(r.states[1][1], 0.099)
        self.assertAlmostEqual(r.times[2], 0.1 / 0.99)

    def test_frozen_band_cannot_create_a_hybrid_crossing(self):
        # f(x) = -1 at x=0.1, yet BQSS holds this state because the
        # nearby backward target gives a positive rate. A Hermite curve
        # using f(x) at both ends would cross zero on this long step.
        event = StateEvent("zero", StateThreshold(0), lambda t, y: y, "decay", -1)
        mode = HybridMode("decay", lambda t, y: (-10 * y[0],), (event,))
        r = simulate_hybrid(
            {"decay": mode},
            initial_mode="decay",
            initial_state=(0.1,),
            t_bound=5,
            method="bqss1",
            solver_options={"quantum": 0.2},
        )
        self.assertEqual(r.events, ())
        self.assertEqual(r.final_state, (0.1,))

    def test_invalid_contracts(self):
        with self.assertRaisesRegex(ValueError, "autonomous"):
            bqss1(InitialValueProblem(lambda t, y: (t,), 0, (1.0,), 1), 0.1)
        p = problem(lambda t, y: (1.0, -2.0), (1.0, 0.0), 1)
        for kw in (
            {"quantum": 0},
            {"quantum": (1,)},
            {"quantum": 1, "max_events": 0},
            {"quantum": 1, "simultaneous_tolerance": float("nan")},
        ):
            with self.assertRaises(ValueError):
                bqss1(p, **kw)
        with self.assertRaisesRegex(IntegrationError, "bracket"):
            bqss1(p, 1e-25)


class LogQuantumTests(unittest.TestCase):
    def test_geometric_decay_changes_to_absolute_floor(self):
        for sign in (-1.0, 1.0):
            p = problem(lambda t, y: (-y[0],), (sign * 8,), 1.2)
            r = qss1(p, 1.0, relative_quantum=0.25)
            self.assertEqual(r.times[:4], (0, 0.25, 0.5, 0.75))
            self.assertEqual(
                [y[0] * sign for y in r.states[:5]], [8, 6, 4.5, 3.375, 2.375]
            )
            self.assertAlmostEqual(r.times[4] - r.times[3], 1 / 3.375)

    def test_relative_width_is_latched_per_component(self):
        p = problem(lambda t, y: (4.0, 1.0), (4.0, 10.0), 2.1)
        r = qss1(p, 0.1, relative_quantum=(0.5, 0.2))
        self.assertEqual(r.times, (0, 0.5, 1.25, 2.0, 2.1))

    def test_second_order_event_curvature_and_relatched_width(self):
        # x'' = 1, so each interval starts with zero error and slope error,
        # then hits the band at sqrt(2 * width).
        p = problem(lambda t, y: (y[1], 1.0), (10.0, 0.0), 5.0)
        r = solve_ivp(p, "qss2", options={"quantum": 0.1, "relative_quantum": (0.2, 0)})
        self.assertAlmostEqual(r.times[1], 2.0, places=6)
        self.assertAlmostEqual(r.times[2], 2 + math.sqrt(4.8), places=6)
        self.assertAlmostEqual(r.final_state[0], 22.5, places=6)

    def test_disabled_policy_and_invalid_options(self):
        p = problem(lambda t, y: (y[1], -y[0]), (1.0, 0.0), 1.0)
        for solver in (qss1, qss2):
            self.assertEqual(
                solver(p, 0.02), solver(p, 0.02, relative_quantum=(0.0, 0.0))
            )
            for value in (-0.1, (1.0,), (True, 0.0), math.inf, math.nan):
                with self.assertRaises((TypeError, ValueError)):
                    solver(p, 0.02, relative_quantum=value)
            with self.assertRaisesRegex(IntegrationError, "overflow"):
                solver(
                    problem(lambda t, y: (1.0,), (1e200,), 1.0),
                    1.0,
                    relative_quantum=1e200,
                )
        with self.assertRaisesRegex(TypeError, "unsupported"):
            solve_ivp(p, "liqss2", options={"quantum": 0.01, "relative_quantum": 0.01})
