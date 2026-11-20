import math
import unittest

from argesim_benchmarks.models import c02_pallet_study
from argesim_benchmarks.models.c02_flexible_assembly import C02Constants
from argesim_benchmarks.models.c02_transport import C02Plant, _Pallet


def short_plant(count, minutes, *, warmup=0, trace=False):
    return C02Plant(
        count,
        constants=C02Constants(warmup_minutes=warmup, end_minutes=minutes),
        trace=trace,
    )


class C02TransportTests(unittest.TestCase):
    def test_one_pallet_matches_hand_calculation(self):
        result = short_plant(1, 60).run()
        # One loop: 13.6 m B1/B2, six 0.4 m connectors, 10 straight
        # shifters, and six lateral shifts at A1, A2 and idle A6.
        travel = (13.6 + 6 * 0.4 + 10 * 0.4) / 0.3 + 6 * 2
        production = travel + 60 + 30
        self.assertAlmostEqual(result["average_throughput_time"], production)
        self.assertAlmostEqual(
            result["average_to_unload_complete_seconds"], production + 7.5
        )
        self.assertAlmostEqual(
            result["average_including_handling_seconds"], production + 15
        )
        self.assertFalse(result["deadlock"])

    def test_measurement_window_counts_completed_unloads_including_its_endpoints(self):
        trial = short_plant(1, 15, trace=True)
        trial.run()
        unloads = [e["tick"] for e in trial.trace if e["event"] == "unloaded"]
        self.assertGreaterEqual(len(unloads), 3)
        # Include the two boundary completions, although the first load was earlier.
        ticks_per_minute = 1800
        for offset, count in ((0, 2), (1, 1)):
            timing = short_plant(
                1,
                unloads[1] / ticks_per_minute,
                warmup=(unloads[0] + offset) / ticks_per_minute,
            ).run()
            self.assertEqual(timing["throughput"], count)
        early = short_plant(1, (unloads[0] - 1) / ticks_per_minute).run()
        self.assertEqual(early["throughput"], 0)
        self.assertIsNone(early["average_throughput_time"])
        self.assertFalse(early["deadlock"])

    def test_two_adjacent_shifters_need_an_exit_before_the_first_move(self):
        for previous, operations in ((3, 1), (7, 15)):
            with self.subTest(previous=previous):
                plant = short_plant(1, 1, trace=True)
                nxt = (previous + 1) % 8
                sy, sx = plant.stations[previous], plant.stations[nxt]
                self.assertIsNone(sy.connector)
                # The fixture models completed work on A2_3 or A6; make A3
                # eligible in the former case. Fill both potential outlets.
                plant.stations[7].due = 500
                part = _Pallet(100, loaded_at=0, operations=operations)
                sy.after.queue.append((part, 0))
                for belt in (sx.before, sx.bypass):
                    belt.queue.clear()
                    belt.queue.extend((_Pallet(i), 0) for i in range(belt.capacity))
                self.assertFalse(plant._transfer(sy.after, nxt, sy=sy, sx=sx))
                self.assertEqual((sy.sy_free, sx.sx_free), (0, 0))
                self.assertIs(sy.after.queue[0][0], part)
                sx.before.queue.pop()
                # The second shifter still has an owner for one more tick
                # than the first crossing. Nothing can wait between them.
                sx.sx_free = plant.shift + 1
                self.assertFalse(plant._transfer(sy.after, nxt, sy=sy, sx=sx))
                self.assertEqual(sy.sy_free, 0)
                plant.now = 1
                self.assertTrue(plant._transfer(sy.after, nxt, sy=sy, sx=sx))
                self.assertFalse(sy.after.queue)
                self.assertIs(sx.before.queue[-1][0], part)
                e = plant.trace[-1]
                self.assertEqual((e["tick"], e["sx_start"], e["arrival"]), (1, 61, 121))

    def test_simultaneous_branch_return_has_priority_at_sy(self):
        plant = short_plant(2, 1, trace=True)
        station = plant.stations[1]
        for s in plant.stations:
            s.bypass.queue.clear()
            if s.connector is not None:
                s.connector.queue.clear()
        branch, main = _Pallet(0), _Pallet(1)
        station.after.queue.append((branch, 0))
        station.bypass.queue.append((main, 0))
        plant._settle()
        self.assertIs(station.connector.queue[0][0], branch)
        self.assertIs(station.bypass.queue[0][0], main)
        self.assertEqual(station.sy_free, 60)  # 2 s transfer

    def test_trace_has_exclusive_shifters_and_finite_speed_fifo_handoffs(self):
        plant = short_plant(40, 10, trace=True)
        # Reconstruct belt ownership from the initial queues and subsequent
        # trace only. Reservations belong to the destination until FIFO release.
        inventory = {}
        capacity = {}
        for station in plant.stations:
            for belt in (
                station.bypass,
                station.before,
                station.after,
                station.connector,
            ):
                if belt is not None:
                    inventory[belt.name] = [p.identifier for p, _ in belt.queue]
                    capacity[belt.name] = belt.capacity
        units = {}
        gate_free, last_entry, last_exit = {}, {}, {}
        earliest_exit = {}
        trips = 0
        plant.run()
        for event in plant.trace:
            pallet, now = event["pallet"], event["tick"]
            kind = event["event"]
            if kind == "transfer":
                trips += 1
                source, dest = event["source"], event["destination"]
                start, arrival = event["sx_start"], event["arrival"]
                for gate, name, begin, end in (
                    ("Sy", event["sy"], now, start),
                    ("Sx", event["sx"], start, arrival),
                ):
                    if name is not None:
                        self.assertGreaterEqual(begin, gate_free.get((gate, name), 0))
                        lateral = (
                            source.endswith(".post")
                            if gate == "Sy"
                            else dest.endswith(".pre")
                        )
                        self.assertEqual(end - begin, 60 if lateral else 40)
                        gate_free[gate, name] = end
            elif kind == "unit_enter":
                source, dest = event["station"] + ".pre", None
                self.assertNotIn(event["station"], units)
                units[event["station"]] = pallet
            elif kind == "unit_exit":
                source, dest = None, event["station"] + ".post"
                arrival = event["clear"]
                self.assertEqual(units.pop(event["station"]), pallet)
            else:
                continue
            if source is not None:
                self.assertEqual(inventory[source].pop(0), pallet)
                self.assertGreaterEqual(now - last_exit.get(source, -36), 36)
                self.assertGreaterEqual(now, earliest_exit.pop((source, pallet), 0))
                last_exit[source] = now
            if dest is not None:
                inventory[dest].append(pallet)
                self.assertLessEqual(len(inventory[dest]), capacity[dest])
                self.assertGreaterEqual(arrival - last_entry.get(dest, -36), 36)
                name, section = dest.split(".")
                long = name in ("A1", "A6")
                length = {
                    "B1": 200 if long else 160,
                    "pre": 120 if long else 80,
                    "post": 40,
                    "gap": 40,
                }[section]
                earliest_exit[dest, pallet] = arrival + length
                last_entry[dest] = arrival
        self.assertGreater(trips, 500)
        self.assertEqual(
            set(gate_free), {(g, s.name) for g in ("Sx", "Sy") for s in plant.stations}
        )
        final = [p for q in inventory.values() for p in q] + list(units.values())
        self.assertEqual(sorted(final), list(range(40)))

    def test_completed_parts_follow_the_permitted_operation_order(self):
        plant = short_plant(40, 30, trace=True)
        result = plant.run()
        group = {"A3", "A4", "A5"}
        active = {}
        counted = 0
        seen = set()
        for e in plant.trace:
            pallet, kind = e["pallet"], e["event"]
            if kind == "loaded":
                self.assertNotIn(pallet, active)
                active[pallet] = set()
            elif kind == "assembled":
                done = active[pallet]
                station = e["station"]
                seen.add(station)
                if station.startswith("A2"):
                    self.assertNotIn("A2", done)
                    self.assertIn(done & group, (set(), group))
                    done.add("A2")
                elif station == "A6":
                    self.assertTrue(group - done)
                    done.update(group)
                else:
                    self.assertNotIn(station, done)
                    done.add(station)
            elif kind == "unloaded":
                self.assertEqual(active.pop(pallet), {"A2"} | group)
                counted += 1
        self.assertEqual(seen, {"A2_1", "A2_2", "A2_3", "A3", "A4", "A5", "A6"})
        self.assertGreater(counted, 0)
        self.assertEqual(result["throughput"], counted)

    def test_deadlock_depends_on_state_not_population_or_short_horizon(self):
        live = short_plant(60, 10).run()
        self.assertFalse(live["deadlock"])
        self.assertEqual(live["stopped_at_seconds"], 600)
        self.assertEqual(live["initial_on_b1"], 40)
        self.assertEqual(live["pending_admission"], 0)
        self.assertIsNone(live["deadlock_witness"])

    def test_study_ranks_only_fully_admitted_productive_loads(self):
        self.assertEqual(c02_pallet_study(1, 2)["best_num_pallets"], 2)
        self.assertIsNone(c02_pallet_study(60, 60)["best_num_pallets"])
        for bounds in ((2, 1), (False, 1), (1, math.inf)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                c02_pallet_study(*bounds)
