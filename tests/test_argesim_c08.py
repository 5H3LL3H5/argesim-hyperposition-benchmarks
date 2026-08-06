import unittest
from argesim_benchmarks.models.c08_canal_and_lock import CanalAndLock, Barge, Direction

class TestC08(unittest.TestCase):
    def test_dataset_1(self):
        c = CanalAndLock(1, 1)
        for i in range(15):
            c.schedule_arrival(Barge(i, Direction.EASTBOUND, i * 108.0))
        for i in range(15):
            c.schedule_arrival(Barge(100+i, Direction.WESTBOUND, 54.0 + i * 108.0))

        c.run(1458.0)

        east_completed = [b for b, _ in c.completed_barges if b.direction == Direction.EASTBOUND]
        west_completed = [b for b, _ in c.completed_barges if b.direction == Direction.WESTBOUND]

        self.assertEqual(len(east_completed), 14)
        self.assertEqual(len(west_completed), 13)

        for b, t in c.completed_barges:
            self.assertAlmostEqual(t, 54.0)

    def test_dataset_2(self):
        c = CanalAndLock(2, 3)
        for i in range(20):
            c.schedule_arrival(Barge(i*2, Direction.EASTBOUND, i * 210.0))
            c.schedule_arrival(Barge(i*2+1, Direction.EASTBOUND, i * 210.0))

        for i in range(20):
            c.schedule_arrival(Barge(100+i*3, Direction.WESTBOUND, 88.0 + i * 210.0))
            c.schedule_arrival(Barge(100+i*3+1, Direction.WESTBOUND, 88.0 + i * 210.0))
            c.schedule_arrival(Barge(100+i*3+2, Direction.WESTBOUND, 88.0 + i * 210.0))

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
        c = CanalAndLock(1, 1)
        for i in range(30):
            c.schedule_arrival(Barge(i, Direction.EASTBOUND, i * 54.0))

        c.run(1458.0)

        east_completed = [(b, t) for b, t in c.completed_barges if b.direction == Direction.EASTBOUND]
        self.assertEqual(len(east_completed), 27)
        for b, t in east_completed:
            self.assertAlmostEqual(t, 54.0)

    def test_dataset_4(self):
        c = CanalAndLock(1, 1)
        for i in range(20):
            c.schedule_arrival(Barge(i, Direction.WESTBOUND, i * 100.0))

        c.run(1500.0)

        west_completed = [(b, t) for b, t in c.completed_barges if b.direction == Direction.WESTBOUND]
        self.assertEqual(len(west_completed), 15)
        for b, t in west_completed:
            self.assertAlmostEqual(t, 54.0)

    def test_dataset_5(self):
        c = CanalAndLock(2, 3)
        for i in range(5):
            c.schedule_arrival(Barge(i*3, Direction.EASTBOUND, i * 500.0))
            c.schedule_arrival(Barge(i*3+1, Direction.EASTBOUND, i * 500.0))
            c.schedule_arrival(Barge(i*3+2, Direction.EASTBOUND, i * 500.0))

            c.schedule_arrival(Barge(100+i*5, Direction.WESTBOUND, 200.0 + i * 500.0))
            c.schedule_arrival(Barge(100+i*5+1, Direction.WESTBOUND, 200.0 + i * 500.0))
            c.schedule_arrival(Barge(100+i*5+2, Direction.WESTBOUND, 200.0 + i * 500.0))
            c.schedule_arrival(Barge(100+i*5+3, Direction.WESTBOUND, 200.0 + i * 500.0))
            c.schedule_arrival(Barge(100+i*5+4, Direction.WESTBOUND, 200.0 + i * 500.0))

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
