import unittest
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
    def test_c20_is_implemented(self):
        c20 = catalog.benchmark("C20")
        self.assertEqual(c20.status, catalog.BenchmarkStatus.IMPLEMENTED)

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

        env.run(until_macro=100.0)
        self.assertEqual(ws1.processed_count, len(orders))

if __name__ == '__main__':
    unittest.main()
