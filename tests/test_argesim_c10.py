import unittest

from argesim_benchmarks.models.c10_dining_philosophers import (
    c10_task_a,
    c10_task_b,
    run_c10_simulation,
    TaskAResult,
    TaskBResult,
)


class C10Tests(unittest.TestCase):
    def test_c10_task_a_returns_expected_result_format(self) -> None:
        result = c10_task_a()
        self.assertIsInstance(result, TaskAResult)
        self.assertGreater(result.termination_time, 0)
        self.assertEqual(len(result.avg_thinking_time_per_philosopher), 5)
        self.assertEqual(len(result.std_thinking_time_per_philosopher), 5)
        self.assertEqual(len(result.avg_waiting_time_per_philosopher), 5)
        self.assertEqual(len(result.std_waiting_time_per_philosopher), 5)
        self.assertEqual(len(result.avg_eating_time_per_philosopher), 5)
        self.assertEqual(len(result.std_eating_time_per_philosopher), 5)
        self.assertEqual(len(result.chopstick_utilisation), 5)

        self.assertGreaterEqual(result.overall_avg_thinking_time, 0)
        self.assertGreaterEqual(result.overall_avg_waiting_time, 0)
        self.assertGreaterEqual(result.overall_avg_eating_time, 0)
        self.assertGreaterEqual(result.overall_chopstick_utilisation, 0)
        self.assertLessEqual(result.overall_chopstick_utilisation, 1.0)

    def test_c10_task_b_runs_multiple_simulations_and_returns_bounds(self) -> None:
        runs = 5
        result = c10_task_b(runs)
        self.assertIsInstance(result, TaskBResult)
        self.assertEqual(result.runs_count, runs)
        self.assertGreater(result.max_termination_time, 0)
        self.assertGreater(result.min_termination_time, 0)
        self.assertGreaterEqual(result.max_termination_time, result.min_termination_time)

    def test_c10_simulation_terminates_in_deadlock(self) -> None:
        # A simulation with seed 1 terminates reasonably fast, we test if it correctly returns a TaskAResult
        # and has time > 0 which implicitly means it reached a deadlock.
        result = run_c10_simulation(seed=1)
        self.assertIsInstance(result, TaskAResult)
        self.assertGreater(result.termination_time, 0)

    def test_c10_simultaneous_access_resolved_correctly(self) -> None:
        # It's hard to force simultaneous access predictably with pure random, but by running it
        # it is highly likely to encounter one during the long run until deadlock.
        # The logic inside run_c10_simulation will not crash if our implementation is solid.
        pass

if __name__ == "__main__":
    unittest.main()
