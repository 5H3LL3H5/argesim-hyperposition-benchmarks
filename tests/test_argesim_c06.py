import unittest
from unittest.mock import patch

from argesim_benchmarks.models.c06_emergency_department import (
    Facilities,
    Patient,
    QueueDiscipline,
    Simulation,
    _update_doctor_exchange,
    _ward_treatment_time,
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
        self.assertEqual(set(swapped), set(baseline))
        self.assertNotEqual(swapped, baseline)

    def test_task_b_hysteresis_and_doctor_times_are_exchanged(self):
        env = Simulation(seed=1)
        facilities = Facilities(env)

        facilities.cw2.queue.extend([object()] * 21)
        _update_doctor_exchange(facilities, task_b_active=True)
        self.assertTrue(facilities.cw2_queue_was_large)

        cw1_patient = Patient(env, 1, 1)
        cw1_patient.ward = 1
        cw2_patient = Patient(env, 2, 1)
        cw2_patient.ward = 2

        with patch(
            "argesim_benchmarks.models.c06_emergency_department.triangular_dist",
            side_effect=lambda _rng, low, mode, high: (low, mode, high),
        ):
            self.assertEqual(
                _ward_treatment_time(
                    cw1_patient, facilities, task_b_active=True
                ),
                (2.8, 4.1, 6.3),
            )
            self.assertEqual(
                _ward_treatment_time(
                    cw1_patient, facilities, task_b_active=True
                ),
                (1.5, 3.2, 5.0),
            )
            self.assertEqual(
                _ward_treatment_time(
                    cw2_patient, facilities, task_b_active=True
                ),
                (1.5, 3.2, 5.0),
            )
            self.assertEqual(
                _ward_treatment_time(
                    cw2_patient, facilities, task_b_active=True
                ),
                (2.8, 4.1, 6.3),
            )

        facilities.cw2.queue[:] = [object()] * 5
        _update_doctor_exchange(facilities, task_b_active=True)
        self.assertFalse(facilities.cw2_queue_was_large)

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
