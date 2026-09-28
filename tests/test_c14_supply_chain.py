import math
import unittest

from argesim_benchmarks.models.c14_supply_chain import (
    SECONDS_PER_HOUR,
    SUPPLY_LEAD_TIMES,
    TASK_A_B_MAPPING,
    TRANSPORT_COST_PER_HOUR_PER_ORDER,
    WHOLESALER_START_TIME,
    SupplyChainSim,
    c14_task_a1,
    c14_task_a2,
    c14_task_b1,
    c14_task_b2,
    c14_task_c1,
    c14_task_c2,
)


class _WholesalerRng:
    def __init__(self):
        self.values = iter((4, 12, 600))

    def randint(self, _low, _high):
        return next(self.values)


class TestC14SupplyChain(unittest.TestCase):
    def test_table_3_maps_all_products_for_every_distributor(self):
        expected_products = set(range(1, 13))
        self.assertTrue(all(set(mapping) == expected_products for mapping in TASK_A_B_MAPPING.values()))
        self.assertEqual(TASK_A_B_MAPPING[1][12], 2)
        self.assertEqual(TASK_A_B_MAPPING[3][1], 4)
        self.assertEqual(TASK_A_B_MAPPING[4][8], 3)

    def test_transport_cost_is_lead_time_times_ten(self):
        sim = SupplyChainSim("a", seed=1)
        sim.factories[1].stock[1] = 2
        self.assertTrue(sim.place_factory_order(1, 1, 1, 2, 100))
        expected_cost = TRANSPORT_COST_PER_HOUR_PER_ORDER * SUPPLY_LEAD_TIMES[(1, 1)]
        self.assertEqual(sim.distributors[1].total_cost, expected_cost)
        self.assertIn((100 + 16 * SECONDS_PER_HOUR, 1, 2), sim.distributors[1].incoming_deliveries)

    def test_factory_order_is_all_or_nothing(self):
        sim = SupplyChainSim("b", seed=1)
        sim.factories[1].stock[1] = 1
        self.assertFalse(sim.place_factory_order(1, 1, 1, 2, 0))
        self.assertEqual(sim.factories[1].stock[1], 1)
        self.assertEqual(sim.distributors[1].total_cost, 0.0)

    def test_wholesaler_starts_at_day_nine_and_can_request_product_twelve(self):
        sim = SupplyChainSim("b", seed=1)
        for factory in sim.factories.values():
            factory.next_production_time = math.inf
        sim.rng = _WholesalerRng()
        sim.advance_time(WHOLESALER_START_TIME)
        self.assertEqual(sim.distributors[4].wholesaler_demand[12], 1)
        self.assertEqual(sim.distributors[4].unfulfilled_wholesaler_demand[12], 1)

    def test_day_eight_initial_fill_is_strategy_independent(self):
        sim = SupplyChainSim("c", seed=1)
        for factory in sim.factories.values():
            factory.next_production_time = math.inf
            for product in factory.stock:
                factory.stock[product] = 100

        sim.run(days=8)

        # D1/product 1 follows Table 3 (F1), even though F4 would have
        # the shorter lead time. The delivery itself has arrived by day 8.
        # Table 3: D1 and D2 draw p1 from F1; D3 and D4 from F4.
        self.assertEqual(sim.factories[1].stock[1], 80)
        self.assertEqual(sim.factories[4].stock[1], 80)

    def test_single_run_tasks_return_full_stock_vectors(self):
        for task in (c14_task_a1, c14_task_b1):
            history = task(seed=123)
            self.assertEqual(history[-1][0], 30 * 24 * SECONDS_PER_HOUR)
            self.assertTrue(all(set(stock) == set(range(1, 13)) for _, stock in history))

    def test_monte_carlo_tasks_return_finite_metrics(self):
        for task in (c14_task_a2, c14_task_b2, c14_task_c1):
            metrics = task(seed=123, runs=2)
            for metric in ("C", "N", "R"):
                self.assertEqual(set(metrics[metric]), {"max", "min", "mean", "dev"})
                self.assertTrue(all(math.isfinite(value) for value in metrics[metric].values()))

    def test_comparison_contains_all_strategies(self):
        comparison = c14_task_c2(seed=101, runs=2)
        self.assertEqual(set(comparison), {"Strategy A", "Strategy B", "Strategy C"})
        self.assertNotEqual(
            comparison["Strategy B"]["C"]["mean"],
            comparison["Strategy C"]["C"]["mean"],
        )

    def test_invalid_run_count_is_rejected(self):
        with self.assertRaises(ValueError):
            c14_task_a2(runs=0)


if __name__ == "__main__":
    unittest.main()
