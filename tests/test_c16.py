import unittest
from argesim_benchmarks.models.c16_restaurant_business import (
    C16Parameters,
    C16Simulation,
    c16_task_a,
    c16_task_b,
    c16_task_c,
)

class TestC16RestaurantBusiness(unittest.TestCase):
    def test_initialization(self):
        sim = C16Simulation(seed=123)
        self.assertEqual(len(sim.people), 3000)
        self.assertEqual(len(sim.restaurants), 30)

    def test_day_step_decrements_interval(self):
        sim = C16Simulation(seed=123)
        initial_intervals = [p.days_until_next_visit for p in sim.people]
        sim.step_day()
        # They should decrement, and some might reset (if they were 1)
        for old, p in zip(initial_intervals, sim.people):
            if old > 1:
                self.assertEqual(p.days_until_next_visit, old - 1)

    def test_week_step_resets_revenue(self):
        sim = C16Simulation(seed=123)
        sim.restaurants[0].weekly_revenue = 1000.0
        sim.step_week()
        for r in sim.restaurants:
            self.assertEqual(r.weekly_revenue, 0.0)

    def test_task_a(self):
        # use runs=1 to make it fast
        res = c16_task_a(runs=1, seed=42)
        self.assertIn("time_series_10_years", res)
        self.assertIn("average_after_5_years", res)
        self.assertEqual(len(res["time_series_10_years"]), 10 * 52)

    def test_task_b(self):
        res = c16_task_b(tax_rates=[0.1, 0.2], seed=42)
        self.assertIn(0.1, res)
        self.assertIn(0.2, res)
        self.assertIsInstance(res[0.1], float)

    def test_task_c(self):
        res = c16_task_c(k_values=[0.5, 1.0], seed=42)
        self.assertIn(0.5, res)
        self.assertIn(1.0, res)
        self.assertIsInstance(res[0.5], float)

if __name__ == '__main__':
    unittest.main()
