import math
import statistics
import unittest
from unittest.mock import patch

from argesim_benchmarks.models.c06_emergency_department import (
    Doctor,
    Facilities,
    Patient,
    QueueDiscipline,
    Simulation,
    _ward_treatment_time,
    open_facilities,
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
            {"overall", "type_1", "type_2", "type_3", "type_4", "std_dev", "closing_minutes"},
        )
        self.assertTrue(all(value > 0.0 for value in baseline.values()))

    def test_published_daily_statistics_for_all_three_policies(self):
        # STROBOSCOPE C6, Table 1. Both experiments comprise 100 independent
        # days, with 250 arrivals per day. Published values are whole minutes.
        metrics = ("overall", "type_1", "type_2", "type_3", "type_4", "std_dev", "closing_minutes")
        for policy, reference in (
            ({}, (174, 237, 136, 252, 127, 82, 378)),
            ({"task_b_active": True}, (184, 252, 144, 266, 136, 95, 420)),
            ({"discipline": QueueDiscipline.PRIORITY}, (161, 164, 162, 175, 156, 75, 382)),
        ):
            days = [solve_c06(seed=seed, **policy) for seed in range(100)]
            for metric, target in zip(metrics, reference):
                values = [day[metric] for day in days]
                # Equal-variance estimate of uncertainty of two sample means.
                se = statistics.stdev(values) * math.sqrt(2 / len(days))
                with self.subTest(policy=policy, metric=metric):
                    self.assertAlmostEqual(statistics.mean(values), target, delta=3.5 * se + 0.5)

    def test_task_b_implements_capacity_preserving_doctor_swap(self):
        baseline = solve_c06_task_a()
        swapped = solve_c06_task_b()
        self.assertEqual(set(swapped), set(baseline))
        self.assertNotEqual(swapped, baseline)

    def test_treatment_distribution_follows_doctor_identity(self):
        env = Simulation(seed=1)
        patient = Patient(env, 1, 1)
        with patch(
            "argesim_benchmarks.models.c06_emergency_department.triangular_dist",
            side_effect=lambda _rng, low, mode, high: (low, mode, high),
        ):
            for home, ward, expected in (
                (1, 1, (1.5, 3.2, 5.0)),
                (1, 2, (1.5, 3.2, 5.0)),
                (2, 2, (2.8, 4.1, 6.3)),
                (2, 1, tuple(1.2 * value for value in (2.8, 4.1, 6.3))),
            ):
                patient.ward = ward
                doctor = Doctor(0, home, ward, busy=True)
                # Consecutive treatments by the same doctor must not alternate
                # between experienced/inexperienced distributions.
                for _ in range(3):
                    self.assertEqual(_ward_treatment_time(patient, doctor), expected)

    def test_doctor_exchange_waits_for_treatments_and_returns_at_low_queue(self):
        env = Simulation(seed=1)
        facilities = Facilities(env, task_b_active=True)
        open_facilities(facilities)
        started = []
        completed = []

        def submit(ward, label, duration):
            def begin(doctor):
                started.append((env.now, label, doctor.identifier, doctor.ward))

                def finish():
                    # Identity and ward cannot change during a treatment.
                    self.assertEqual(doctor.ward, ward.number)
                    completed.append(label)
                    ward.release(doctor)

                env.schedule(duration, finish)

            ward.request()(begin)

        submit(facilities.cw1, "cw1-exchange", 2.0)
        submit(facilities.cw1, "cw1-stationary", 4.0)
        submit(facilities.cw2, "cw2-exchange", 3.0)
        submit(facilities.cw2, "cw2-stationary", 5.0)
        for i in range(21):
            submit(facilities.cw2, f"waiting-{i}", 1.0)
        env.run(2.5)
        self.assertFalse(facilities.doctors_exchanged)
        self.assertFalse(facilities.doctors[0].busy)
        self.assertTrue(facilities.doctors[2].busy)
        env.run(3.1)
        self.assertEqual(facilities.exchange_history, [(3.0, True)])
        self.assertEqual((facilities.cw1.capacity, facilities.cw2.capacity), (2, 2))
        self.assertIn((3.0, "waiting-0", 0, 2), started)
        env.run()
        self.assertEqual(len(completed), 25)
        self.assertFalse(facilities.doctors_exchanged)
        self.assertEqual(
            [active for _, active in facilities.exchange_history], [True, False]
        )
        self.assertTrue(
            all(d.ward == d.home_ward and not d.busy for d in facilities.doctors)
        )

    def test_servers_take_work_when_free_instead_of_alternating_starts(self):
        env = Simulation(seed=1)
        facilities = Facilities(env)
        open_facilities(facilities)
        assignments = []

        def begin(doctor):
            assignments.append(doctor.identifier)
            delay = 1.0 if doctor.identifier == 0 else 10.0
            env.schedule(delay, lambda: facilities.cw1.release(doctor))

        for _ in range(6):
            facilities.cw1.request()(begin)
        env.run()
        self.assertEqual(assignments, [0, 1, 0, 0, 0, 0])

    def test_pending_exchange_is_cancelled_when_queue_recovers(self):
        env = Simulation(seed=1)
        facilities = Facilities(env, task_b_active=True)
        open_facilities(facilities)

        def begin(doctor):
            delay = 100.0 if doctor.identifier == 2 else 0.1
            env.schedule(delay, lambda: facilities.cw2.release(doctor))

        for _ in range(23):
            facilities.cw2.request()(begin)
        env.run(3.0)
        self.assertFalse(facilities.cw2_queue_was_large)
        self.assertEqual(facilities.exchange_history, [])
        self.assertTrue(facilities.doctors[2].busy)
        self.assertTrue(
            all(doctor.ward == doctor.home_ward for doctor in facilities.doctors)
        )
        env.run()

    def test_returning_patient_priority_is_applied_to_actual_free_doctor(self):
        env = Simulation(seed=1)
        facilities = Facilities(env, discipline=QueueDiscipline.PRIORITY)
        open_facilities(facilities)
        order = []

        def submit(label, priority):
            def begin(doctor):
                order.append(label)
                env.schedule(1.0, lambda: facilities.cw1.release(doctor))

            facilities.cw1.request(priority)(begin)

        submit("active-1", 0)
        submit("active-2", 0)
        submit("first-visit", 0)
        submit("return", -1)
        env.run()
        self.assertEqual(order, ["active-1", "active-2", "return", "first-visit"])

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
