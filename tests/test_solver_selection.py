"""Independent checks of the work–precision experiment when SciPy is installed."""

import math
import unittest
from dataclasses import replace
from importlib.util import find_spec
from types import SimpleNamespace


@unittest.skipUnless(
    find_spec("scipy"), "install SciPy for stiff reference comparisons"
)
class SelectionProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from benchmarks import benchmark_solver_selection as selection

        cls.selection = selection

    def test_analytical_probes_against_independent_implicit_collocation(self):
        for case in self.selection.analytic_cases():
            with self.subTest(case=case.name):
                r, samples = case.run("Radau", {"rtol": 1e-10, "atol": 1e-12})
                self.assertEqual(r.final_time, case.end)
                self.assertGreater(r.stats.lu_factorizations, 0)
                self.assertEqual(len(case.tolerances), len(samples))
                for value, exact, limit in zip(
                    samples, case.expected, case.tolerances, strict=True
                ):
                    self.assertLess(abs(value - exact), limit * 1e-4)

    def test_c05_implicit_candidates_reproduce_sequence_and_terminal_states(self):
        case = self.selection.argesim_case(self.selection.study.switches())
        for method in self.selection.IMPLICIT:
            with self.subTest(method=method):
                result, observations = case.run(
                    method, self.selection.configure(case, method, 1)
                )
                self.assertEqual(result.final_time, case.end)
                self.assertEqual(len(observations), 5)
                for value, exact, limit in zip(
                    observations, case.expected, case.tolerances, strict=True
                ):
                    self.assertLessEqual(abs(value - exact), limit)

    def test_native_stiff_pair_recovers_three_c05_switches_and_terminal_states(self):
        case = self.selection.study.switches()
        for level in (1, 2):
            opts = self.selection.configure(case, "esdirk32", level)
            result, samples = case.run("esdirk32", opts)
            self.assertEqual(result.final_time, 3.5)
            self.assertEqual(len(samples), 5)
            for v, ref, limit in zip(
                samples, case.expected, case.tolerances, strict=True
            ):
                self.assertLessEqual(abs(v - ref), limit)
        opts = self.selection.configure(case, "rk23", 1)
        with self.assertRaisesRegex(self.selection.IntegrationError, "max_steps"):
            case.run("rk23", {**opts, "max_steps": 250})

    def test_scoring_rejects_a_nonfinite_later_observable(self):
        base = self.selection.analytic_cases()[0]

        def run(method, opts):
            work = self.selection.Work(1, 0, 1, None)
            return self.selection.Run(base.end, work), (0.0, math.nan)

        case = replace(base, run=run, expected=(0.0, 0.0), tolerances=(1.0, 1.0))
        row = self.selection.study.measure(
            case,
            "rk45",
            None,
            SimpleNamespace(repeat=1, timeout=2),
        )
        self.assertEqual(row["status"], "solver_error")
        self.assertNotIn("error_over_limit", row)
