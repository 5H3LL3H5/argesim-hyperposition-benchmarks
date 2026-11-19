import itertools
import math
import unittest
from collections import Counter
from dataclasses import replace
from unittest.mock import patch

from argesim_benchmarks.models.c20_complex_production import (
    C20OrderScenario,
    C20PlantScenario,
    Operation,
)
from argesim_benchmarks.models.c20_flow import C20Flow
from argesim_benchmarks.models.c20_layout import C20Layout
from argesim_benchmarks.models.c20_production import (
    C20_MACHINE_LOCATIONS,
    C20Production,
)


def small_layout():
    layout = C20Layout.__new__(C20Layout)
    layout.nodes, layout.tracks, layout.outgoing = {}, {}, {}
    layout.node("source", kind="source")
    layout.node("junction")
    layout.node("sink", kind="sink")
    layout.track("source", "junction", 2.0, "A")
    layout.track("junction", "sink", 2.0, "B")
    return layout


class C20FlowTests(unittest.TestCase):
    def test_dimensions_and_failure_tracks_from_definition_figures(self):
        layout = C20Layout()
        clusters = Counter(
            track.cluster for track in layout.tracks.values() if track.cluster
        )
        self.assertEqual(clusters, {"A": 16, "B": 8, "C": 12})
        self.assertEqual(
            sum(node.kind == "buffer" for node in layout.nodes.values()), 90
        )
        self.assertEqual(
            sum(node.kind == "workstation" for node in layout.nodes.values()), 30
        )
        self.assertAlmostEqual(layout.tracks["T0->U0"].length, 4 * math.pi)
        self.assertAlmostEqual(layout.tracks["U0->L0"].length, 2 * math.pi)
        self.assertAlmostEqual(layout.tracks["in1->a1:in"].length, 1.5 * math.pi)
        self.assertEqual(layout.tracks["WB->WT"].cluster, "B")
        self.assertEqual(layout.tracks["in0->out0"].length, 69 - 2 * 4)
        self.assertEqual(C20_MACHINE_LOCATIONS["I.2"], "a1:ws4")
        self.assertEqual(C20_MACHINE_LOCATIONS["III.3"], "a2:ws4")
        self.assertEqual(C20_MACHINE_LOCATIONS["IV.2"], "a3:ws3")

    def test_isolated_source_trip_matches_independent_geometry_sum(self):
        flow = C20Flow()
        arrived = []
        flow.insert(1, "a0:out")
        flow.send(1, "a1:ws1", arrived.append)
        flow.run()
        # Two R3 quarter turns, two R4 quarter turns, two R2.5
        # quarter turns; the straight segments sum to 183 metres.
        expected = 183 + (3 + 4 + 2.5) * math.pi
        self.assertEqual(len(arrived), 1)
        self.assertAlmostEqual(arrived[0].distance, expected)
        self.assertAlmostEqual(arrived[0].arrived, expected)
        flow.assert_conservation()

    def test_downstream_blockage_retains_capacity_and_reaches_source(self):
        flow = C20Flow(layout=small_layout())
        flow.insert(99, "sink")
        pending = list(range(6))
        arrived = []

        def arrival(trip):
            arrived.append(trip)
            flow.remove(trip.part)

        def admit():
            if pending and flow.insert(pending[0], "source"):
                flow.send(pending.pop(0), "sink", arrival)

        flow.on_change = admit
        admit()
        flow.run(until=10.0)
        self.assertEqual(arrived, [])
        self.assertEqual(pending, [])
        self.assertFalse(flow.can_insert("source"))
        self.assertEqual([len(state.parts) for state in flow.tracks.values()], [2, 2])
        flow.assert_conservation()
        flow.remove(99)
        flow.run(until=100.0)
        self.assertEqual([trip.part for trip in arrived], list(range(6)))
        self.assertGreaterEqual(arrived[0].arrived, 11.0)
        self.assertTrue(
            all(b.arrived - a.arrived >= 1 for a, b in itertools.pairwise(arrived))
        )
        self.assertFalse(flow.parts)
        flow.assert_conservation()

    def test_failure_pauses_remaining_motion_and_prevents_early_departure(self):
        flow = C20Flow(layout=small_layout())
        arrivals = []
        flow.insert(1, "source")
        flow.send(1, "sink", arrivals.append)
        flow.call_at(1.0, lambda: flow.fail_track("source->junction", 5.0))
        flow.run(until=8.0)
        self.assertEqual(arrivals, [])
        flow.run()
        self.assertEqual(arrivals[0].arrived, 9.0)
        self.assertEqual(arrivals[0].paused_on_failed_belts, 5.0)
        flow.assert_conservation()

    def test_no_backdated_events_or_duplicate_parts(self):
        flow = C20Flow(layout=small_layout())
        flow.insert(1, "source")
        with self.assertRaises(ValueError):
            flow.insert(1, "junction")
        flow.run(until=2)
        with self.assertRaises(ValueError):
            flow.call_at(1, lambda: None)

    def test_production_keeps_fifo_reservations_and_minimum_process_delay(self):
        simulation = C20Production(
            C20OrderScenario.OSC2,
            C20PlantScenario.PSC4,
            seed=7,
            order_count=40,
            trace=True,
        )
        result = simulation.run()
        self.assertEqual(result.completed_orders, 40)
        self.assertLessEqual(simulation.maximum_wip, 30)
        self.assertLessEqual(simulation.maximum_buffer_reservations, 90)
        self.assertFalse(simulation.buffer_owners)
        last_o5 = {}
        checked = 0
        for when, event, identifier, operation, _ in simulation.operation_trace:
            if event == "finish" and operation == "O5":
                last_o5[identifier] = when
            if event == "start" and operation == "O3" and identifier in last_o5:
                self.assertGreaterEqual(when - last_o5[identifier], 600.0)
                checked += 1
        self.assertGreater(checked, 0)
        self.assertTrue(all(not machine.busy for machine in simulation.machines))

    def test_maximum_constraints_use_actual_start_and_include_boundary(self):
        for product, predecessor, operation, maximum, violation in (
            ("C", Operation.O4, Operation.O3, 360.0, "max_nok"),
            ("E", Operation.O6, Operation.O5, 300.0, "max_ok"),
        ):
            for excess in (0.0, 0.01):
                simulation = C20Production(
                    "OSc1", "PSc1", seed=1, order_count=1, trace=True
                )
                job = next(iter(simulation.jobs.values()))
                job.order = replace(job.order, product_type=product)
                job.plan, job.index, job.previous_completion = (
                    (predecessor, operation),
                    1,
                    0.0,
                )
                machine = next(
                    i
                    for i, m in enumerate(simulation.machines)
                    if m.supports(operation, product)
                )
                simulation.flow.now = maximum + excess
                with patch.object(simulation, "dispatch"):
                    simulation._start(job, machine, operation, 10.0)
                with self.subTest(product=product, excess=excess):
                    self.assertEqual(
                        simulation.operation_trace[-1][1],
                        "start" if excess == 0 else violation,
                    )
                    self.assertEqual(getattr(job, violation), int(excess > 0))
                    if product == "E" and excess:
                        self.assertEqual(job.index, 0)
                        self.assertEqual(job.plan[job.index], Operation.O6)

    def test_operation_change_keeps_part_outside_workstation(self):
        simulation = C20Production("OSc1", "PSc1", seed=1, order_count=1, trace=True)
        simulation.flow.events.clear()
        simulation.flow.on_change = None
        job = next(iter(simulation.jobs.values()))
        job.order = replace(job.order, product_type="D")
        job.plan, job.phase = (Operation.O5, Operation.O3), "waiting"
        machine = next(i for i, m in enumerate(simulation.machines) if m.name == "V.1")
        simulation.machines[machine].last_operation = Operation.O4
        simulation.flow.insert(job.order.identifier, "a0:out")
        target = simulation.machine_nodes[machine]
        with patch.object(simulation, "dispatch"):
            simulation._to_machine(job, machine)
            simulation.flow.run(until=299.0)
            self.assertNotIn(target, simulation.flow.at_node)
            simulation.flow.run(until=301.0)
        self.assertEqual(simulation.flow.at_node[target], job.order.identifier)
        self.assertEqual(simulation.operation_trace[0][:2], (300.0, "start"))


if __name__ == "__main__":
    unittest.main()
