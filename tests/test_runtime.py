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

    def test_quantized_states_are_independent_of_absolute_start_time(self):
        methods = (
            "qss1", "cqss1", "qss2", "qss3", "qss4",
            "liqss1", "liqss2", "liqss3", "mliqss1", "mliqss2", "mliqss3",
            "eliqss1", "eliqss2", "eliqss3", "cheqss1", "cheqss2", "cheqss3",
            "liqss-bdf",
        )
        span = 1 / 128
        origin = 2**30
        for rates, quantum in (
            ((1.0, 1.0), (1 / 1024, 1 / 512)),
            ((0.7, 0.9), (0.0003, 0.0007)),
        ):
            def rhs(_time, _state, rates=rates):
                return rates

            for method in methods:
                options = {"quantum": quantum}
                if method == "liqss-bdf":
                    options.update(bdf_partition=(1,), max_step=span / 4)
                with self.subTest(method=method, rates=rates):
                    problem = InitialValueProblem(rhs, 0.0, (0.0, 0.0), span, autonomous=True)
                    absolute = InitialValueProblem(
                        rhs, origin, problem.y0, origin + span, autonomous=True,
                    )
                    reference = solve_ivp(problem, method, options=options)
                    shifted = solve_ivp(absolute, method, options=options)
                    self.assertEqual(shifted.times, tuple(origin + t for t in reference.times))
                    self.assertEqual(shifted.states, reference.states)
                    self.assertEqual(shifted.stats, reference.stats)
                    for actual, derivative in zip(shifted.final_state, rates):
                        self.assertAlmostEqual(actual, span * derivative, delta=1e-10)

    def test_shifted_qss_rhs_jacobian_and_step_observer_see_absolute_time(self):
        origin, span = 2**30, 1 / 128
        rhs_times, jac_times, observed = [], [], []

        def rhs(time, state):
            rhs_times.append(time)
            return (-state[0],)

        def jacobian(time, _state):
            jac_times.append(time)
            return ((-1.0,),)

        def stop(left, _previous, right, _current):
            observed.append((left, right))
            return True

        problem = InitialValueProblem(
            rhs, origin, (1.0,), origin + span, autonomous=True, _stop_after_step=stop,
        )
        result = solve_ivp(problem, "liqss1", options={"quantum": 1 / 1024, "jacobian": jacobian})
        self.assertLess(result.final_time, problem.t_bound)
        self.assertEqual(observed, [(origin, result.final_time)])
        self.assertTrue(rhs_times and min(rhs_times) == origin)
        self.assertTrue(jac_times and min(jac_times) == origin)

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
