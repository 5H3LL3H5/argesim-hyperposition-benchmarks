import unittest
from argesim_benchmarks.models.c08_canal_and_lock import CanalAndLock, Barge, Direction
from nsa_devs.hypertime import HyperTime

class TestC08(unittest.TestCase):
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

if __name__ == '__main__':
    unittest.main()
