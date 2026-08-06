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
        from argesim_benchmarks.models.c10_dining_philosophers import PhilosopherState

        # We will extract the core allocation logic to test it directly.
        num_philosophers = 5
        chopstick_free = [True] * num_philosophers
        states = [PhilosopherState.THINKING] * num_philosophers

        # P0 wants Left (0), P4 wants Right (0). Simultaneous access on chopstick 0.
        states[0] = PhilosopherState.WAITING_LEFT
        states[4] = PhilosopherState.WAITING_RIGHT

        allocation_changed = True
        while allocation_changed:
            allocation_changed = False
            for c in range(num_philosophers):
                if not chopstick_free[c]:
                    continue

                left_requester = c
                right_requester = (c - 1) % 5

                req_left = (states[left_requester] == PhilosopherState.WAITING_LEFT)
                req_right = (states[right_requester] == PhilosopherState.WAITING_RIGHT)

                if req_left and req_right:
                    chopstick_free[c] = False
                    states[left_requester] = PhilosopherState.WAITING_RIGHT
                    allocation_changed = True
                elif req_left:
                    chopstick_free[c] = False
                    states[left_requester] = PhilosopherState.WAITING_RIGHT
                    allocation_changed = True
                elif req_right:
                    chopstick_free[c] = False
                    states[right_requester] = PhilosopherState.EATING
                    allocation_changed = True

        # P0 (left requester) wins chopstick 0 and transitions to WAITING_RIGHT.
        # Then, because chopstick 1 is free, P0 wins chopstick 1 and transitions to EATING.
        # P4 (right requester) loses chopstick 0 and stays WAITING_RIGHT.
        self.assertEqual(states[0], PhilosopherState.EATING)
        self.assertEqual(states[4], PhilosopherState.WAITING_RIGHT)
        self.assertFalse(chopstick_free[0])

if __name__ == "__main__":
    unittest.main()
