import math
import unittest

from argesim_benchmarks.models import c02_pallet_study
from argesim_benchmarks.models.c02_flexible_assembly import C02Constants
from argesim_benchmarks.models.c02_transport import (
    C02Plant,
    _Pallet,
    _simevents_listing3_value,
)


def short_plant(count, minutes, *, warmup=0, trace=False):
    return C02Plant(
        count,
        constants=C02Constants(warmup_minutes=warmup, end_minutes=minutes),
        trace=trace,
    )


class C02TransportTests(unittest.TestCase):
    def test_one_pallet_matches_hand_calculation(self):
        result = short_plant(1, 60).run()
        # All 16 shifters are traversed lengthwise. Six also shift laterally.
        travel = (13.6 + 6 * 0.4 + 16 * 0.4) / 0.3 + 6 * 2
        production = travel + 60 + 30
        self.assertAlmostEqual(result["average_throughput_time"], production)
        self.assertAlmostEqual(
            result["average_to_unload_complete_seconds"], production + 7.5
        )
        self.assertAlmostEqual(
            result["average_including_handling_seconds"], production + 15
        )
        self.assertAlmostEqual(production + 15, 191 + 2 / 3)
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

    def test_service_only_changes_headway_without_removing_travel_or_adding_slots(self):
        for timing, headway in (("exclusive", 1840), ("service-only", 1800)):
            with self.subTest(unit_timing=timing):
                c = C02Constants(warmup_minutes=0, end_minutes=2)
                plant = C02Plant(2, constants=c, unit_timing=timing, trace=True)
                for station in plant.stations:
                    for belt in (station.bypass, station.connector):
                        if belt is not None:
                            belt.queue.clear()
                            belt.next_entry = 0
                a2 = plant.stations[1]
                self.assertEqual((a2.before.capacity, a2.after.capacity), (2, 1))
                a2.before.queue.extend(
                    [(_Pallet(0, loaded_at=0), 0), (_Pallet(1, loaded_at=0), 36)]
                )
                plant.run()
                starts = [
                    e["tick"]
                    for e in plant.trace
                    if e["event"] == "work" and e["station"] == a2.name
                ]
                self.assertEqual(len(starts), 2)
                self.assertEqual(starts[1] - starts[0], headway)
                single = C02Plant(1, unit_timing=timing).run()
                self.assertAlmostEqual(
                    single["average_including_handling_seconds"], 191 + 2 / 3
                )
                self.assertEqual(single["throughput"], 150)

    def test_seeded_initial_placement_uses_distinct_legal_b1_slots(self):
        def occupied(plant):
            result = []
            for station in plant.stations:
                self.assertFalse(
                    station.before.queue or station.after.queue or station.pallet
                )
                for belt in (station.bypass, station.connector):
                    if belt is None:
                        continue
                    entries = [ready for _, ready in belt.queue]
                    self.assertEqual(entries, sorted(set(entries)))
                    for ready in entries:
                        centre = belt.transit - ready
                        self.assertTrue(
                            belt.pitch // 2 <= centre <= belt.transit - belt.pitch // 2
                        )
                        self.assertEqual((centre - belt.pitch // 2) % belt.pitch, 0)
                        result.append((belt.name, centre))
            return result

        first = occupied(C02Plant(14, initial_seed=0))
        self.assertEqual(len(first), 14)
        self.assertEqual(first, occupied(C02Plant(14, initial_seed=0)))
        self.assertNotEqual(first, occupied(C02Plant(14, initial_seed=1)))
        full = C02Plant(60, initial_seed=3)
        self.assertEqual(occupied(full), occupied(C02Plant(60)))
        self.assertEqual((full.initial_on_b1, len(full.feed.queue)), (40, 20))
        study = c02_pallet_study(1, 1, initial_seed=0)
        self.assertEqual(study["runs"][0]["initial_seed"], 0)
        for invalid in (True, 3.5, "0"):
            with (
                self.subTest(seed=invalid),
                self.assertRaisesRegex(ValueError, "initial_seed"),
            ):
                C02Plant(14, initial_seed=invalid)

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
                plant.stations[7].before.queue.append((_Pallet(99), 0))
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
                sx.sx_free = plant.lateral_crossing + 1
                self.assertFalse(plant._transfer(sy.after, nxt, sy=sy, sx=sx))
                self.assertEqual(sy.sy_free, 0)
                plant.now = 1
                self.assertTrue(plant._transfer(sy.after, nxt, sy=sy, sx=sx))
                self.assertFalse(sy.after.queue)
                self.assertIs(sx.before.queue[-1][0], part)
                e = plant.trace[-1]
                self.assertEqual(
                    (e["tick"], e["sx_start"], e["arrival"]), (1, 101, 201)
                )

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
        self.assertEqual(station.sy_free, 100)  # 40 travel ticks plus 60 shift ticks

    def test_a3_counts_arrived_a6_pallets_and_the_occupied_unit(self):
        plant = short_plant(1, 1)
        part = _Pallet(100, loaded_at=0)
        a6 = plant.stations[7]
        a6.due = 500  # the unit is still clearing
        a6.before.reserve(_Pallet(101), arrival=1)
        self.assertFalse(plant._takes_branch(part, 4))
        plant.now = 1
        self.assertTrue(plant._takes_branch(part, 4))
        a6.due = plant.now
        a6.after.reserve(_Pallet(102), arrival=1)
        self.assertFalse(plant._takes_branch(part, 4))

    def test_a6_input_arrival_wakes_a_blocked_a3_transfer(self):
        plant = short_plant(7, 0.1, trace=True)
        for station in plant.stations:
            for belt in (station.bypass, station.connector):
                if belt is not None:
                    belt.queue.clear()
                    belt.next_entry = 0
        a3, a6 = plant.stations[4], plant.stations[7]
        # All four bypass slots are occupied. The first becomes free at tick 34.
        for identifier, ready in enumerate((34, 70, 106, 142)):
            a3.bypass.queue.append((_Pallet(identifier), ready))
        waiting = _Pallet(4, loaded_at=0, operations=1)
        plant.stations[3].after.queue.append((waiting, 0))
        a6.pallet, a6.phase, a6.due = _Pallet(5, loaded_at=0), "work", 300
        a6.before.reserve(_Pallet(6, loaded_at=0), arrival=30)
        a6.sx_free = 30
        plant.run()
        starts = [
            (e["tick"], e["destination"])
            for e in plant.trace
            if e["event"] == "transfer" and e["pallet"] == waiting.identifier
        ]
        self.assertEqual(starts, [(30, "A3.pre")])

    def test_cyclic_a2_counts_committed_passages_including_bypasses(self):
        for index, period in ((1, 3), (2, 2)):
            plant = C02Plant(1, controller="cyclic-a2")
            source = plant.stations[index - 1].connector
            sx = plant.stations[index]
            source.queue.clear()
            for passage in range(1, 2 * period + 1):
                with self.subTest(index=index, passage=passage):
                    # The first, empty pallet must also advance the counter.
                    part = _Pallet(passage, loaded_at=None if passage == 1 else 0)
                    source.queue.append((part, 0))
                    sx.sx_free = plant.now + 1
                    for _ in range(2):
                        self.assertFalse(plant._transfer(source, index, sx=sx))
                    self.assertEqual(plant.a2_passages[index - 1], passage - 1)
                    plant.now += 1
                    self.assertTrue(plant._transfer(source, index, sx=sx))
                    target = sx.bypass if passage % period else sx.before
                    self.assertIs(target.queue.pop()[0], part)
                    plant.now += 200

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
                        self.assertEqual(end - begin, 100 if lateral else 40)
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
        live = short_plant(60, 13).run()
        self.assertFalse(live["deadlock"])
        self.assertEqual(live["stopped_at_seconds"], 780)
        self.assertEqual(live["initial_on_b1"], 40)
        self.assertEqual(live["pending_admission"], 0)
        self.assertIsNone(live["deadlock_witness"])

    def test_staged_pallets_remain_in_the_deadlock_witness(self):
        result = C02Plant(75).run()
        self.assertTrue(result["deadlock"])
        self.assertGreater(result["pending_admission"], 0)
        self.assertIsNone(result["fully_admitted_at_seconds"])
        witness = result["deadlock_witness"]
        inventory = witness["occupied_capacity"]
        self.assertEqual(
            inventory["initial B1 feed"], (result["pending_admission"], 75)
        )
        self.assertEqual(sum(used for used, _ in inventory.values()), 75)
        self.assertEqual(set(witness["waits_for"]), set(inventory))
        for blockers in witness["waits_for"].values():
            self.assertTrue(blockers)
            for name in blockers:
                used, capacity = inventory[name]
                self.assertEqual(used, capacity)

    def test_study_ranks_only_fully_admitted_productive_loads(self):
        low = c02_pallet_study(1, 2)
        self.assertEqual(low["best_num_pallets"], 2)
        self.assertEqual(low["simevents_listing_3"]["evaluated_populations"], 0)
        self.assertIsNone(low["simevents_listing_3"]["objective_value"])
        self.assertIsNone(low["simevents_listing_3"]["best_num_pallets"])
        self.assertIsNone(c02_pallet_study(60, 60)["best_num_pallets"])
        for bounds in ((2, 1), (False, 1), (1, math.inf)):
            with self.subTest(bounds=bounds), self.assertRaises(ValueError):
                c02_pallet_study(*bounds)
        with self.assertRaises(ValueError):
            c02_pallet_study(1, 1, controller="unknown")
        with self.assertRaisesRegex(ValueError, "unit_timing"):
            c02_pallet_study(1, 1, unit_timing="unknown")
        self.assertEqual(
            c02_pallet_study(1, 1, controller="cyclic-a2")["runs"][0]["controller"],
            "cyclic-a2",
        )

    def test_simevents_listing3_reproduces_the_literal_objective_and_range(self):
        # The published data at 10 already rule out the stated minimum at 14.
        self.assertEqual(_simevents_listing3_value(959, 285), 646366)
        self.assertEqual(_simevents_listing3_value(1439, 265), 1689386)
        study = c02_pallet_study(9, 11)
        listing = study["simevents_listing_3"]
        self.assertEqual(listing["evaluated_populations"], 2)
        self.assertEqual(listing["published_pallet_range"], [10, 49])
        self.assertEqual(listing["best_num_pallets"], 10)
        ten = study["runs"][1]
        self.assertAlmostEqual(
            listing["objective_value"],
            abs(ten["throughput"] - ten["average_throughput_time"]) * ten["throughput"],
        )
