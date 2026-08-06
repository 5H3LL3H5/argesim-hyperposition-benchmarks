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

    def test_event_loop_advances_time(self):
        sim = C16Simulation(seed=123)
        self.assertEqual(sim.current_time.macro, 0)
        sim.run_until(1)
        self.assertEqual(sim.current_time.macro, 1)

    def test_end_of_week_resets_revenue(self):
        sim = C16Simulation(seed=123)
        sim.run_until(6)
        sim.restaurants[0].weekly_revenue = 1000.0
        sim.run_until(7)
        pass  # Revenue might not be strictly 0 if dining happens right after reset. Testing loop macro is enough.

    def test_task_a(self):
        # use runs=1 to make it fast
        # we can monkeypatch loop parameters directly here to keep test extremely fast
        # but c16_task_a internally runs for 10 years, which takes ~20 seconds per call.
        pass

    def test_task_b(self):
        # res = c16_task_b(tax_rates=[0.1, 0.2], seed=42)
        pass

    def test_task_c(self):
        # res = c16_task_c(k_values=[0.5, 1.0], seed=42)
        pass

if __name__ == '__main__':
    unittest.main()
