import unittest

from argesim_benchmarks.catalog import BenchmarkStatus, benchmark
from argesim_benchmarks.models.c05_two_state import (
    C05_MODE_1,
    C05_REFERENCE_EVENT_TIMES,
    c05_exact_step,
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
        self.assertEqual(benchmark("C05").status, BenchmarkStatus.SPECIFIED)
        result = simulate_c05()
        self.assertEqual(len(result.events), 5)
        for event, reference in zip(result.events, C05_REFERENCE_EVENT_TIMES):
            self.assertAlmostEqual(event.time, reference, delta=2.0e-12)

    def test_task_d_and_final_values(self) -> None:
        validation = c05_validate()
        self.assertEqual(validation.task_d_event_count, 62)
        self.assertLess(validation.task_d_boundary_event_error, 2.0e-11)
        self.assertLess(validation.task_d_final_y1_error, 1.0e-10)

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


if __name__ == "__main__":
    unittest.main()
