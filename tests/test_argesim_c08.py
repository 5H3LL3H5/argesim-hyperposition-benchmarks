import unittest

from argesim_benchmarks.models.c08_canal_and_lock import (
    Barge,
    CanalAndLock,
    Direction,
    c08_task_c,
    run_c08_replication,
)
from nsa_devs.hypertime import HyperTime


class TestC08(unittest.TestCase):
    def test_departure_does_not_reopen_a_full_cycle(self):
        """Eastmax/Westmax limit cumulative admissions, not current occupancy."""
        for direction in Direction:
            with self.subTest(direction=direction):
                opposite = next(value for value in Direction if value != direction)
                model = CanalAndLock(2, 2)
                for identifier, heading, arrival in (
                    (0, direction, 0.0),
                    (1, direction, 0.0),
                    (2, opposite, 1.0),
                    (3, direction, 55.0),
                ):
                    model.schedule_arrival(
                        Barge(identifier, heading, HyperTime.at(arrival))
                    )
                model.run(250.0)
                self.assertEqual(
                    [barge.id for barge, _ in model.completed_barges],
                    [0, 1, 2, 3],
                )
                departures = {
                    barge.id: float(barge.arrival_time.standard_part()) + transit
                    for barge, transit in model.completed_barges
                }
                self.assertEqual(departures, {0: 54.0, 1: 88.0, 2: 142.0, 3: 196.0})

    def test_arrival_can_fill_an_incomplete_cycle(self):
        model = CanalAndLock(2, 1)
        for identifier, heading, arrival in (
            (0, Direction.EASTBOUND, 0.0),
            (1, Direction.WESTBOUND, 1.0),
            (2, Direction.EASTBOUND, 10.0),
        ):
            model.schedule_arrival(Barge(identifier, heading, HyperTime.at(arrival)))
        model.run(200.0)
        self.assertEqual(
            [barge.id for barge, _ in model.completed_barges], [0, 2, 1]
        )
        self.assertEqual(
            [float(barge.arrival_time.standard_part()) + transit
             for barge, transit in model.completed_barges],
            [54.0, 88.0, 142.0],
        )

    def test_dataset_1(self):
        """Validate C08 Dataset 1: Alternating minimal cycles (Eastmax 1, Westmax 1).

        Verifies that after 1458 minutes, exactly 14 eastbound and 13 westbound
        barges have fully cleared the lock system, with each taking 54 minutes.
        """
        c = CanalAndLock(1, 1)
        for i in range(15):
            c.schedule_arrival(Barge(i, Direction.EASTBOUND, HyperTime.at(i * 108.0)))
        for i in range(15):
            c.schedule_arrival(Barge(100+i, Direction.WESTBOUND, HyperTime.at(54.0 + i * 108.0)))

        c.run(1458.0)

        east_completed = [b for b, _ in c.completed_barges if b.direction == Direction.EASTBOUND]
        west_completed = [b for b, _ in c.completed_barges if b.direction == Direction.WESTBOUND]

        self.assertEqual(len(east_completed), 14)
        self.assertEqual(len(west_completed), 13)

        for b, t in c.completed_barges:
            self.assertAlmostEqual(t, 54.0)

    def test_dataset_2(self):
        """Validate C08 Dataset 2: Unbalanced batches (Eastmax 2, Westmax 3).

        Verifies deterministic cycle timing for 7 eastbound and 7 westbound
        cycles, resulting in 21 westbound barges averaging 88 mins and 14
        eastbound barges averaging 71 mins by endpoint 1470.
        """
        c = CanalAndLock(2, 3)
        for i in range(20):
            c.schedule_arrival(Barge(i*2, Direction.EASTBOUND, HyperTime.at(i * 210.0)))
            c.schedule_arrival(Barge(i*2+1, Direction.EASTBOUND, HyperTime.at(i * 210.0)))

        for i in range(20):
            c.schedule_arrival(Barge(100+i*3, Direction.WESTBOUND, HyperTime.at(88.0 + i * 210.0)))
            c.schedule_arrival(Barge(100+i*3+1, Direction.WESTBOUND, HyperTime.at(88.0 + i * 210.0)))
            c.schedule_arrival(Barge(100+i*3+2, Direction.WESTBOUND, HyperTime.at(88.0 + i * 210.0)))

        c.run(1470.0)

        west_completed = [(b, t) for b, t in c.completed_barges if b.direction == Direction.WESTBOUND]
        self.assertEqual(len(west_completed), 21)
        avg_west_time = sum(t for _, t in west_completed) / len(west_completed)
        self.assertAlmostEqual(avg_west_time, 88.0)

        east_completed = [(b, t) for b, t in c.completed_barges if b.direction == Direction.EASTBOUND]
        self.assertEqual(len(east_completed), 14)
        avg_east_time = sum(t for _, t in east_completed) / len(east_completed)
        self.assertAlmostEqual(avg_east_time, 71.0)

    def test_dataset_3(self):
        """Validate C08 Dataset 3: Unidirectional Eastbound.

        Verifies that with no westbound arrivals, eastbound barges
        cycle continuously without changing lock direction, completing
        27 barges in 54 minutes each by endpoint 1458.
        """
        c = CanalAndLock(1, 1)
        for i in range(30):
            c.schedule_arrival(Barge(i, Direction.EASTBOUND, HyperTime.at(i * 54.0)))

        c.run(1458.0)

        east_completed = [(b, t) for b, t in c.completed_barges if b.direction == Direction.EASTBOUND]
        self.assertEqual(len(east_completed), 27)
        for b, t in east_completed:
            self.assertAlmostEqual(t, 54.0)

    def test_dataset_4(self):
        """Validate C08 Dataset 4: Unidirectional Westbound.

        Verifies continuous westbound cyclic operation, completing
        15 barges in 54 minutes each by endpoint 1500.
        """
        c = CanalAndLock(1, 1)
        for i in range(20):
            c.schedule_arrival(Barge(i, Direction.WESTBOUND, HyperTime.at(i * 100.0)))

        c.run(1500.0)

        west_completed = [(b, t) for b, t in c.completed_barges if b.direction == Direction.WESTBOUND]
        self.assertEqual(len(west_completed), 15)
        for b, t in west_completed:
            self.assertAlmostEqual(t, 54.0)

    def test_dataset_5(self):
        """Validate C08 Dataset 5: Mixed consecutive cycles.

        Verifies behavior when multiple cycles occur consecutively within a single
        directional block. 9 eastbound and 15 westbound complete by endpoint 1410,
        matching reference average transit times of 94.67 and 130 minutes.
        """
        c = CanalAndLock(2, 3)
        for i in range(5):
            c.schedule_arrival(Barge(i*3, Direction.EASTBOUND, HyperTime.at(i * 500.0)))
            c.schedule_arrival(Barge(i*3+1, Direction.EASTBOUND, HyperTime.at(i * 500.0)))
            c.schedule_arrival(Barge(i*3+2, Direction.EASTBOUND, HyperTime.at(i * 500.0)))

            c.schedule_arrival(Barge(100+i*5, Direction.WESTBOUND, HyperTime.at(200.0 + i * 500.0)))
            c.schedule_arrival(Barge(100+i*5+1, Direction.WESTBOUND, HyperTime.at(200.0 + i * 500.0)))
            c.schedule_arrival(Barge(100+i*5+2, Direction.WESTBOUND, HyperTime.at(200.0 + i * 500.0)))
            c.schedule_arrival(Barge(100+i*5+3, Direction.WESTBOUND, HyperTime.at(200.0 + i * 500.0)))
            c.schedule_arrival(Barge(100+i*5+4, Direction.WESTBOUND, HyperTime.at(200.0 + i * 500.0)))

        c.run(1410.0)

        east_completed = [(b, t) for b, t in c.completed_barges if b.direction == Direction.EASTBOUND]
        west_completed = [(b, t) for b, t in c.completed_barges if b.direction == Direction.WESTBOUND]

        self.assertEqual(len(east_completed), 9)
        self.assertEqual(len(west_completed), 15)

        avg_east = sum(t for b, t in east_completed) / len(east_completed)
        avg_west = sum(t for b, t in west_completed) / len(west_completed)

        self.assertAlmostEqual(avg_east, 94.67, places=1)
        self.assertAlmostEqual(avg_west, 130.0, places=1)

    def test_probabilistic_replication_is_reproducible(self):
        first = run_c08_replication(5, 5, duration=600.0, seed=123)
        second = run_c08_replication(5, 5, duration=600.0, seed=123)
        self.assertEqual(first, second)
        self.assertGreater(first, 0.0)

    def test_task_c_reports_ordinary_arv_independent_and_crn_intervals(self):
        result = c08_task_c(
            duration=600.0,
            independent_replications=6,
            paired_replications=3,
            starting_seeds=(42,),
        )
        self.assertEqual(result["confidence_probability"], 0.90)
        experiment = result["experiments"][0]
        for key in (
            "ordinary_5_5",
            "antithetic_5_5",
            "independent_difference_5_minus_6",
            "crn_difference_5_minus_6",
        ):
            interval = experiment[key]
            self.assertLessEqual(interval["lower"], interval["mean"])
            self.assertGreaterEqual(interval["upper"], interval["mean"])
            self.assertGreaterEqual(interval["half_width"], 0.0)
        self.assertIn(
            "reject_null_mean_difference_le_zero",
            experiment["crn_difference_5_minus_6"],
        )

    def test_invalid_cycle_limits_are_rejected(self):
        for eastmax, westmax in ((0, 1), (1, 0), (True, 1), (1.5, 1)):
            with self.subTest(eastmax=eastmax, westmax=westmax), self.assertRaises(ValueError):
                CanalAndLock(eastmax, westmax)

    def test_invalid_experiment_controls_are_rejected(self):
        for arguments in (
            {"duration": float("inf")},
            {"independent_replications": True},
            {"paired_replications": 1.5},
            {"starting_seeds": (True,)},
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                c08_task_c(**arguments)

    def test_scheduler_rejects_time_reversal(self):
        model = CanalAndLock(1, 1)
        model.run(10.0)
        with self.assertRaises(ValueError):
            model.run(9.0)

if __name__ == '__main__':
    unittest.main()
