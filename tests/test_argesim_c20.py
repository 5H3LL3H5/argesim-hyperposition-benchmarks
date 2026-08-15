import unittest
import random
import argesim_benchmarks.catalog as catalog
from argesim_benchmarks.models.c20_complex_production import (
    WorkStationType,
    Operation,
    Order,
    SimulationEnvironment,
    WorkStation,
    generate_osc1_order_book,
)

class C20Tests(unittest.TestCase):
    def test_c20_is_specified(self):
        c20 = catalog.benchmark("C20")
        self.assertEqual(c20.status, catalog.BenchmarkStatus.SPECIFIED)

    def test_c20_components_exist(self):
        self.assertEqual(WorkStationType.I.value, "WS1")
        self.assertEqual(Operation.O1.value, "O1")

    def test_c20_simulation_runs(self):
        env = SimulationEnvironment()
        ws1 = WorkStation(env, WorkStationType.I)
        orders = generate_osc1_order_book()

        def dummy_on_finish(o: Order) -> None:
            pass

        # Schedule orders for the workstation
        for order in orders:
            env.schedule(order.earliest_release_date, lambda o=order: ws1.request(o, delay=10.0, on_finish=dummy_on_finish))

        env.run(until_macro=1000000.0)
        self.assertEqual(ws1.processed_count, len(orders))

    def test_order_books_are_seeded_without_global_rng_side_effects(self):
        random.seed(1234)
        expected_next = random.random()
        random.seed(1234)
        first = generate_osc1_order_book(seed=7)
        observed_next = random.random()
        second = generate_osc1_order_book(seed=7)

        self.assertEqual(first, second)
        self.assertEqual(observed_next, expected_next)

if __name__ == '__main__':
    unittest.main()
