import unittest
from argesim_benchmarks.models.c06_emergency_department import (
    QueueDiscipline,
    solve_c06,
    solve_c06_task_a,
    solve_c06_task_b,
    solve_c06_task_c,
)

class TestArgesimC06(unittest.TestCase):
    def test_tasks_are_reproducible_and_complete(self):
        baseline = solve_c06_task_a()
        self.assertEqual(baseline, solve_c06_task_a())
        self.assertEqual(
            set(baseline),
            {"overall", "type_1", "type_2", "type_3", "type_4", "std_dev"},
        )
        self.assertTrue(all(value > 0.0 for value in baseline.values()))

    def test_task_b_implements_capacity_preserving_doctor_swap(self):
        baseline = solve_c06_task_a()
        swapped = solve_c06_task_b()

        # The official task replaces one doctor in each ward; it does not turn
        # a 2/2 system into 1/3. The CW2 doctor in CW1 needs 20% longer, so the
        # common-random-number experiment must not improve any patient class.
        for metric in baseline:
            self.assertGreater(swapped[metric], baseline[metric])

    def test_task_c_reduces_dispersion(self):
        baseline = solve_c06_task_a()
        prioritised = solve_c06_task_c()
        self.assertLess(prioritised["overall"], baseline["overall"])
        self.assertLess(prioritised["std_dev"], baseline["std_dev"])

    def test_reusable_runtime_validates_workload(self):
        result = solve_c06(
            discipline=QueueDiscipline.FIFO,
            seed=7,
            num_patients=25,
        )
        self.assertGreater(result["overall"], 0.0)
        with self.assertRaises(ValueError):
            solve_c06(num_patients=0)
        with self.assertRaises(TypeError):
            solve_c06(task_b_active=1)  # type: ignore[arg-type]
