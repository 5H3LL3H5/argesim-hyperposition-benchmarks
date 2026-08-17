import unittest
import random

import argesim_benchmarks.catalog as catalog
from argesim_benchmarks.models.c20_complex_production import (
    C20ConveyorCluster,
    C20ConveyorElement,
    C20ConveyorNetwork,
    C20OrderScenario,
    C20PlantScenario,
    Operation,
    Order,
    SimulationEnvironment,
    WorkStation,
    WorkStationType,
    _C20Machine,
    generate_osc1_order_book,
    generate_osc2_order_book,
    generate_osc3_order_book,
    run_c20_replication,
    get_process_plans,
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

    def test_operational_scenarios_share_the_same_base_orders(self):
        books = (
            generate_osc1_order_book(seed=9, count=100),
            generate_osc2_order_book(seed=9, count=100),
            generate_osc3_order_book(seed=9, count=100),
        )
        for aligned in zip(*books):
            self.assertEqual(len({order.product_type for order in aligned}), 1)
            self.assertEqual(
                len({order.earliest_release_date for order in aligned}),
                1,
            )
            self.assertEqual(len({order.rush_order_flag for order in aligned}), 1)
        self.assertTrue(all(order.appearance_date == 0.0 for order in books[0]))
        self.assertTrue(
            all(
                order.appearance_date <= order.earliest_release_date
                for order in books[1]
            )
        )
        self.assertTrue(
            all(
                order.appearance_date == order.earliest_release_date
                for order in books[2]
            )
        )

    def test_failures_only_damage_parts_during_processing(self):
        process_machine = _C20Machine(
            "IIg1.1",
            WorkStationType.II,
            1,
            next_failure=5.0,
            mttr=10.0,
            failure_shape=1.0,
            failure_scale_hours=1000.0,
        )
        finish, damaged = process_machine.complete(0.0, 20.0, random.Random(3))
        self.assertEqual(finish, 15.0)
        self.assertTrue(damaged)

        setup_machine = _C20Machine(
            "V.1",
            WorkStationType.V,
            0,
            next_failure=5.0,
            mttr=10.0,
            failure_shape=1.0,
            failure_scale_hours=1000.0,
        )
        finish, damaged = setup_machine.complete(
            0.0,
            20.0,
            random.Random(3),
            damage_on_failure=False,
        )
        self.assertEqual(finish, 30.0)
        self.assertFalse(damaged)

    def test_idle_machine_cannot_start_during_repair(self):
        machine = _C20Machine(
            "IIg1.1",
            WorkStationType.II,
            1,
            next_failure=5.0,
            mttr=10.0,
            failure_shape=1.0,
            failure_scale_hours=1000.0,
        )
        finish, damaged = machine.complete(10.0, 1.0, random.Random(4))
        self.assertEqual(finish, 16.0)
        self.assertFalse(damaged)

    def test_dimensioned_conveyor_capacity_and_routes(self):
        element = C20ConveyorElement(
            "ten-metre-belt",
            10.0,
            C20ConveyorCluster.A,
        )
        self.assertEqual(element.capacity, 10)
        self.assertEqual(element.travel_time, 10.0)

        network = C20ConveyorNetwork(seed=4)
        first = network.transport(0.0, 0, 1)
        second = network.transport(0.0, 0, 1)
        local = network.transport(second.arrival, 1, 1)
        sink = network.transport(local.arrival, 1, 0)
        self.assertGreaterEqual(second.arrival - first.arrival, 1.0)
        self.assertIn("ingress_1", first.elements)
        self.assertEqual(local.elements, ("local_1",))
        self.assertIn("egress_1", sink.elements)

    def test_replication_counts_source_and_sink_transport(self):
        result = run_c20_replication(
            C20OrderScenario.OSC1,
            C20PlantScenario.PSC1,
            seed=3,
            order_count=1,
            transport_time=10.0,
        )
        # Every product needs at least two operations, hence source,
        # inter-operation, and sink transfers all contribute to throughput.
        self.assertGreaterEqual(result.orders[0].throughput_time, 80.0)

    def test_all_alternative_process_plans_and_small_full_scenario(self):
        self.assertEqual(len(get_process_plans("A")), 1)
        self.assertEqual(len(get_process_plans("E")), 2)
        result = run_c20_replication(
            C20OrderScenario.OSC2,
            C20PlantScenario.PSC4,
            seed=7,
            order_count=40,
        )
        self.assertEqual(result.completed_orders, 40)
        self.assertEqual(len(result.orders), 40)
        self.assertGreater(result.makespan, 0.0)
        self.assertEqual(
            result.max_nok_parts,
            sum(order.max_nok_violations for order in result.orders),
        )
        self.assertEqual(
            result.max_ok_parts,
            sum(order.max_ok_violations for order in result.orders),
        )


if __name__ == "__main__":
    unittest.main()
