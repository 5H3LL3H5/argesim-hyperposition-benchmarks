import unittest
from decimal import ROUND_DOWN, Decimal, localcontext

from argesim_benchmarks.catalog import BenchmarkStatus, benchmark
from argesim_benchmarks.models.c05_two_state import (
    C05_MODE_1,
    C05_REFERENCE_EVENT_TIMES,
    c05_exact_step,
    c05_task_c,
    c05_task_d,
    c05_validate,
    simulate_c05,
)


class C05Tests(unittest.TestCase):
    def test_revised_task_d_switches_at_the_specified_state(self) -> None:
        # Revised definition, July 1992, Task d: c2=-1.25 and y1>4.1.
        # Event times alone cannot distinguish a shifted, incorrect branch.
        result = simulate_c05(task_d=True)
        returns = [event for event in result.events if event.new_mode == "state-1"]
        self.assertEqual(len(returns), 31)
        for event in returns:
            self.assertAlmostEqual(event.state[0], 4.1, places=12)

    def test_published_event_sequences(self) -> None:
        self.assertEqual(benchmark("C05").status, BenchmarkStatus.VALIDATED)
        result = simulate_c05()
        self.assertEqual(len(result.events), 5)
        for event, reference in zip(result.events, C05_REFERENCE_EVENT_TIMES):
            self.assertAlmostEqual(event.time, reference, delta=2.0e-12)

    def test_task_d_and_final_values(self) -> None:
        validation = c05_validate()
        self.assertEqual(validation.task_d_event_count, 62)
        self.assertLess(validation.task_d_boundary_event_error, 2.0e-11)
        self.assertLess(validation.task_d_final_y1_error, 1.0e-10)

    def test_independently_published_task_d_values(self) -> None:
        # Einzinger, SNE 22(1), p. 54, Ptolemy II frequent-events table.
        result = simulate_c05(task_d=True)
        for ordinal, expected in ((1, 1.1083061677768), (2, 1.1217299678991),
                                  (60, 4.8093061100968), (61, 4.9230401079777),
                                  (62, 4.9364639081008)):
            self.assertAlmostEqual(result.events[ordinal - 1].time, expected, delta=2e-9)
        self.assertAlmostEqual(result.final_state[0], 5.7804025201735, delta=1e-9)

    def test_exact_step_has_semigroup_property(self) -> None:
        whole = c05_exact_step((4.2, 0.3), 0.75, C05_MODE_1)
        half = c05_exact_step((4.2, 0.3), 0.25, C05_MODE_1)
        split = c05_exact_step(half, 0.5, C05_MODE_1)
        for left, right in zip(whole, split):
            self.assertAlmostEqual(left, right, delta=1.0e-12)

    def test_event_limit_allows_exactly_the_requested_count(self) -> None:
        self.assertEqual(len(simulate_c05(max_events=5).events), 5)
        with self.assertRaises(RuntimeError):
            simulate_c05(max_events=4)

    def test_trajectory_includes_switches_and_fast_transients(self) -> None:
        result = simulate_c05(output_step=0.1)
        self.assertEqual(result.times[0], 0.0)
        self.assertEqual(result.times[-1], 5.0)
        self.assertEqual(result.states[0], (4.2, 0.3))
        self.assertEqual(result.states[-1], result.final_state)
        self.assertTrue(all(a < b for a, b in zip(result.times, result.times[1:])))
        self.assertEqual(len(result.times), len(result.states))
        for event in result.events:
            index = result.times.index(event.time)
            self.assertAlmostEqual(result.states[index][0], event.state[0], delta=1e-14)
            self.assertEqual(result.modes[index], event.new_mode)
        self.assertLess(result.times[1], 1e-6)
        with self.assertRaises(ValueError):
            simulate_c05(output_step=0.0)

    def test_precision_study_matches_independent_logarithmic_event_reference(
        self,
    ) -> None:
        # Independent mpmath 90-digit calculation uses logarithmic crossings,
        # not decimal bisection. Fast-mode contributions at the next crossing
        # are below 10**(-15000) for these defined modes.
        expected_time = Decimal(
            "4.99999964622030775056258130879993587480312297438666579809431319591712874539"
        )
        expected_y1 = Decimal(
            "5.36931212355610201135438450335692304660102396706634831610002649994569167114"
        )
        report = c05_task_c()
        self.assertEqual(
            [row["requested_relative_accuracy"] for row in report["runs"]],
            [1e-6, 1e-10, 1e-14],
        )
        self.assertTrue(all(row["passed"] for row in report["runs"]))
        with localcontext() as context:
            context.prec = 80
            self.assertLess(
                abs(Decimal(report["reference_event_times"][-1]) - expected_time),
                Decimal("1e-65"),
            )
            self.assertLess(
                abs(Decimal(report["reference_final_state"][0]) - expected_y1),
                Decimal("1e-65"),
            )

    def test_task_d_exposes_all_events_and_requested_accuracy(self) -> None:
        report = c05_task_d()
        self.assertEqual(len(report["trajectory"].events), 62)
        row = report["accuracy"]["runs"][0]
        self.assertEqual(row["requested_relative_accuracy"], 1e-11)
        self.assertTrue(row["passed"])
        self.assertEqual(len(row["event_times"]), 62)

    def test_precision_study_rejects_unachievable_or_invalid_requests(self) -> None:
        for accuracies in ((), (1e-16,), (float("nan"),), (True,), (1.0,)):
            with self.subTest(accuracies=accuracies), self.assertRaises(ValueError):
                c05_task_c(accuracies)

    def test_precision_study_is_independent_of_callers_decimal_context(self) -> None:
        baseline = c05_task_c((1e-6,))
        with localcontext() as context:
            context.prec = 7
            context.rounding = ROUND_DOWN
            self.assertEqual(c05_task_c((1e-6,)), baseline)
            self.assertEqual(context.prec, 7)
            self.assertEqual(context.rounding, ROUND_DOWN)


if __name__ == "__main__":
    unittest.main()
