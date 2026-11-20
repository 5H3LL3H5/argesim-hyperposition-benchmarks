import math
import unittest
from unittest.mock import patch

from argesim_benchmarks.models.c16_restaurant_business import (
    C16Parameters,
    C16Simulation,
    Restaurant,
    c16_task_a,
    c16_task_b,
    c16_task_c,
    restaurant_density_at,
)
from nsa_devs import DesScheduler


class TestC16RestaurantBusiness(unittest.TestCase):
    def test_official_initial_restaurant_grid(self):
        sim = C16Simulation(seed=123)
        self.assertEqual(len(sim.people), 3000)
        self.assertEqual(len(sim.restaurants), 30)
        xs = sorted({restaurant.x for restaurant in sim.restaurants})
        ys = sorted({restaurant.y for restaurant in sim.restaurants})
        self.assertEqual(xs, [50.0, 150.0, 250.0, 350.0, 450.0, 550.0])
        self.assertEqual(ys, [40.0, 120.0, 200.0, 280.0, 360.0])

    def test_restaurant_density_uses_distance_exponent(self):
        restaurants = [Restaurant(2.0, 0.0), Restaurant(4.0, 0.0)]
        self.assertAlmostEqual(restaurant_density_at(0.0, 0.0, restaurants, 2.0), 0.3125)
        self.assertEqual(restaurant_density_at(0.0, 0.0, restaurants, 0.0), 2.0)
        self.assertTrue(math.isinf(restaurant_density_at(2.0, 0.0, restaurants, 2.0)))

    def test_week_boundary_processes_dinners_before_reset(self):
        sim = C16Simulation(seed=123)
        self.assertIsInstance(sim.scheduler, DesScheduler)
        sim.run_until(6)
        sim.restaurants[0].weekly_revenue = 1000.0
        sim.run_until(7)
        self.assertTrue(all(restaurant.weekly_revenue == 0.0 for restaurant in sim.restaurants))

    def test_incremental_and_single_horizon_runs_are_equivalent(self):
        params = C16Parameters(total_people=40)
        direct = C16Simulation(params, seed=19)
        split = C16Simulation(params, seed=19)

        direct.run_until(21)
        split.run_until(7)
        split.run_until(14)
        split.run_until(21)

        self.assertEqual(direct.current_time, split.current_time)
        self.assertEqual(direct.restaurants, split.restaurants)
        self.assertEqual(direct.total_tax, split.total_tax)
        self.assertEqual(
            direct.new_restaurant_revenues(),
            split.new_restaurant_revenues(),
        )

    def test_new_restaurant_revenue_excludes_initial_restaurants(self):
        params = C16Parameters(total_people=10, initial_restaurants=1)
        sim = C16Simulation(parameters=params, seed=1)
        sim.restaurants[0].lifetime_revenue = 999.0
        sim.restaurants.append(
            Restaurant(10.0, 10.0, id=1, is_initial=False, lifetime_revenue=123.0)
        )
        self.assertEqual(sim.new_restaurant_revenues(), (123.0,))

    def test_default_event_budget_covers_multiyear_tasks(self):
        sim = C16Simulation(C16Parameters(maximum_dining_interval=1), seed=19)
        with patch.object(sim.scheduler, "run", return_value=0) as run:
            for years in (5, 10):
                with self.subTest(years=years):
                    days = years * 52 * 7
                    sim.run_until(days)
                    self.assertEqual(run.call_args.args, (days,))
                    expected_events = days * len(sim.people) + days // 7
                    self.assertGreaterEqual(run.call_args.kwargs["max_events"], expected_events)

    def test_tasks_execute_with_small_auditable_workloads(self):
        params = C16Parameters(total_people=30)
        task_a = c16_task_a(runs=1, seed=2, parameters=params, years=6)
        self.assertEqual(len(task_a["time_series_1_year"]), 52)
        self.assertEqual(len(task_a["time_series_5_years"]), 260)
        self.assertEqual(len(task_a["time_series_10_years"]), 312)
        self.assertEqual(task_a, c16_task_a(runs=1, seed=2, parameters=params, years=6, workers=2))

        task_b = c16_task_b([0.0, 0.2], seed=2, runs=1, years=1, parameters=params)
        self.assertEqual(set(task_b), {0.0, 0.2})
        self.assertEqual(task_b[0.0], 0.0)

        task_c = c16_task_c([0.0, 2.0], seed=2, runs=1, years=1, parameters=params)
        self.assertEqual(set(task_c), {0.0, 2.0})
        self.assertTrue(all(value >= 0.0 for value in task_c.values()))

    def test_year_five_endpoint_and_following_time_average(self):
        first = [0] * 259 + [4] + [1] * 52
        second = [0] * 259 + [8] + [3] * 52
        with patch(
            "argesim_benchmarks.models.c16_restaurant_business._weekly_restaurant_counts",
            side_effect=[first, second, [30] * 312],
        ):
            task = c16_task_a(runs=2, years=6)
        self.assertEqual(task["restaurants_at_year_5"], [4, 8])
        self.assertEqual(task["mean_at_year_5"], 6.0)
        self.assertEqual(task["average_after_5_years"], 2.0)
        self.assertEqual(task["time_series_5_years"], [30] * 260)

    def test_populated_city_outside_area_is_rejected(self):
        params = C16Parameters(total_people=40, area_width=40, area_height=40)
        with self.assertRaisesRegex(ValueError, "city B"):
            C16Simulation(params, seed=1)

    def test_invalid_task_inputs_are_rejected(self):
        calls = (
            lambda: c16_task_a(runs=0),
            lambda: c16_task_a(runs=True),
            lambda: c16_task_b([], runs=1),
            lambda: c16_task_b([float("nan")], runs=1),
            lambda: c16_task_c([6.5], runs=1),
            lambda: c16_task_c([1.0], runs=1.5),
        )
        for call in calls:
            with self.subTest(call=call), self.assertRaises(ValueError):
                call()

    def test_parameter_validation_rejects_invalid_numeric_domains(self):
        for arguments in (
            {"total_people": True},
            {"area_width": float("nan")},
            {"dinner_cost": -1.0},
            {"cell_size": 1000.0},
        ):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                C16Parameters(**arguments)

    def test_simulation_rejects_time_reversal_and_invalid_tax(self):
        sim = C16Simulation(C16Parameters(total_people=20), seed=1)
        sim.run_until(10)
        with self.assertRaises(ValueError):
            sim.run_until(9)
        with self.assertRaises(ValueError):
            sim.run_until(11, tax_rate=float("nan"))
        with self.assertRaises(RuntimeError):
            C16Simulation(C16Parameters(total_people=20), seed=1).run_until(
                10,
                max_events=1,
            )


if __name__ == "__main__":
    unittest.main()
