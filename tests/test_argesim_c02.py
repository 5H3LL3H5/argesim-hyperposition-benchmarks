import math
import unittest
from typing import ClassVar

from argesim_benchmarks.models import solve_c02
from argesim_benchmarks.models.c02_flexible_assembly import (
    C02Constants,
    Message,
    Pallet,
    RouterModel,
    StationModel,
    _station_configs,
)


class C02Tests(unittest.TestCase):
    def test_empty_pallets_only_enter_loading_station(self):
        constants = C02Constants()
        for config in _station_configs(constants)[1:]:
            station = StationModel(config.name, config, constants)
            router = RouterModel(config.name, station)
            for identifier in range(6):
                router.dext(0, Message("in", Pallet(identifier)))
            self.assertTrue(all(port == "to_conveyor" for _, port in router.queue))

    def test_a2_cannot_interrupt_the_a3_a4_a5_group(self):
        constants = C02Constants()
        config = _station_configs(constants)[3]  # A2_3 accepts every eligible pallet.
        for operations in ({"A3"}, {"A4"}, {"A5"}, {"A3", "A4"}):
            station = StationModel(config.name, config, constants)
            router = RouterModel(config.name, station)
            router.dext(
                0, Message("in", Pallet(0, operations_done=operations, in_system=True))
            )
            self.assertEqual(router.out().port, "to_conveyor")

    def test_simultaneous_arrivals_reserve_before_delivery(self):
        constants = C02Constants()
        config = _station_configs(constants)[3]
        station = StationModel(config.name, config, constants)
        router = RouterModel(config.name, station)
        for identifier in range(config.buffer_capacity + 1):
            router.dext(0, Message("in", Pallet(identifier, in_system=True)))
        self.assertEqual(station.occupancy, config.buffer_capacity)
        self.assertEqual(router.queue[-1][1], "to_conveyor")
        # Remove the routing event, then deliver on the next DEVS microstep.
        message = router.out()
        router.dint()
        self.assertEqual(station.occupancy, config.buffer_capacity)
        station.dext(0, Message("in", message.value))
        self.assertEqual(station.occupancy, config.buffer_capacity)
        self.assertEqual(len(station.reserved_admissions), config.buffer_capacity - 1)

    def test_all_shifts_and_transport_lengths_follow_the_clarification(self):
        constants = C02Constants()
        configs = _station_configs(constants)
        self.assertTrue(all(config.shift_time == 2.0 for config in configs))
        self.assertAlmostEqual(configs[0].b1_transport_length(constants), 2.8)
        self.assertAlmostEqual(configs[1].b1_transport_length(constants), 2.4)

    def test_station_travel_is_split_around_processing_without_double_counting(self):
        constants = C02Constants()
        config = _station_configs(constants)[1]
        station = StationModel("test", config, constants)
        station.dext(0.0, Message("in", Pallet(0, in_system=True)))
        elapsed = 0.0
        transitions = []
        while math.isfinite(station.sigma):
            elapsed += station.sigma
            transitions.append((station.next_internal_event, elapsed))
            station.dint()
        self.assertEqual(
            [kind for kind, _ in transitions],
            [
                "SHIFT_IN_DONE",
                "BUFFER_ARRIVAL",
                "PROCESSING_DONE",
                "POST_TRAVEL_DONE",
                "SHIFT_OUT_DONE",
            ],
        )
        self.assertAlmostEqual(transitions[1][1], 2.0 + 1.0 / 0.3)
        self.assertAlmostEqual(transitions[2][1] - transitions[1][1], 60.0)
        self.assertAlmostEqual(elapsed, 2.0 + 1.6 / 0.3 + 60.0 + 2.0)

    def test_initial_empty_pallet_needs_loading_only(self):
        constants = C02Constants()
        config = _station_configs(constants)[0]
        durations = []
        for loaded in (False, True):
            station = StationModel("A1", config, constants, is_a1=True)
            station.dext(0.0, Message("in", Pallet(0, in_system=loaded)))
            elapsed = 0.0
            while math.isfinite(station.sigma):
                elapsed += station.sigma
                station.dint()
            durations.append(elapsed)
        self.assertAlmostEqual(durations[0], 2.0 + 2.0 / 0.3 + 7.5 + 2.0)
        self.assertAlmostEqual(durations[1] - durations[0], 7.5)

    def test_high_load_deadlock_has_a_closed_resource_wait_cycle(self):
        for n in (50, 60):
            with self.subTest(pallets=n):
                result = solve_c02(n)
                self.assertIs(result["deadlock"], True)
                self.assertEqual(result["pending_admission"], 0)
                self.assertLess(
                    result["fully_admitted_at_seconds"], result["stopped_at_seconds"]
                )
                self.assertLess(result["stopped_at_seconds"], 7200)
                self.assertEqual(result["throughput"], 0)
                self.assertIsNone(result["average_throughput_time"])
                blocked = result["deadlock_witness"]
                inventory = blocked["occupied_capacity"]
                self.assertEqual(sum(used for used, _ in inventory.values()), n)
                waits = blocked["waits_for"]
                self.assertEqual(set(waits), set(inventory))
                for destinations in waits.values():
                    self.assertTrue(destinations)
                    for destination in destinations:
                        used, capacity = inventory[destination]
                        self.assertEqual(used, capacity)

    def test_invalid_pallet_counts_are_rejected(self):
        for value in (0, -1, 2.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solve_c02(value)


class C02PublishedComparisons(unittest.TestCase):
    # Pingel & Pawletta (2011), Table 2. Preserve the original relative 6% band.
    references: ClassVar[dict[int, tuple[int, int]]] = {
        10: (959, 285),
        11: (1072, 280),
        12: (1185, 276),
        13: (1298, 273),
        14: (1439, 265),
        15: (1439, 285),
        20: (1439, 385),
        25: (1439, 396),
        30: (1440, 586),
        35: (1438, 682),
        40: (1437, 787),
        45: (1440, 882),
    }

    @classmethod
    def setUpClass(cls):
        # Model or execution errors here are failures for every comparison.
        cls.runs = {n: solve_c02(n) for n in cls.references}

    def assert_reference(self, n):
        expected_count, expected_mean = self.references[n]
        r = self.runs[n]
        errors = (
            abs(r["throughput"] / expected_count - 1),
            abs(r["average_throughput_time"] / expected_mean - 1),
        )
        self.assertLessEqual(max(errors), 0.06, (n, errors))

    def test_all_reference_cases_complete_and_report_consistent_clocks(self):
        for n, r in self.runs.items():
            with self.subTest(n=n):
                self.assertIs(r["deadlock"], False)
                self.assertEqual(r["controller"], "first-eligible")
                self.assertEqual(r["pending_admission"], 0)
                self.assertGreater(r["throughput"], 0)
                mean = r["average_throughput_time"]
                self.assertGreater(mean, 0)
                self.assertAlmostEqual(
                    r["average_to_unload_complete_seconds"], mean + 7.5
                )
                self.assertAlmostEqual(
                    r["average_including_handling_seconds"], mean + 15
                )

    def test_simevents_numeric_comparisons(self):
        for n in (10, 11, 12, 15, 20, 30, 35, 40, 45):
            with self.subTest(n=n):
                self.assert_reference(n)
        # Only the mean is outside the band at 25 pallets.
        self.assertAlmostEqual(self.runs[25]["throughput"] / 1439, 1, delta=0.06)

    def test_processing_only_sensitivity_against_reference_cases(self):
        for n, (count, mean_time) in self.references.items():
            with self.subTest(n=n):
                r = solve_c02(n, unit_timing="service-only")
                self.assertEqual(r["unit_timing"], "service-only")
                self.assertFalse(r["deadlock"])
                self.assertGreater(r["average_throughput_time"], 0)
                if n != 14:
                    self.assertAlmostEqual(r["throughput"] / count, 1, delta=0.06)
                if n not in (14, 25):
                    self.assertAlmostEqual(
                        r["average_throughput_time"] / mean_time, 1, delta=0.06
                    )

    def test_service_only_with_one_fixed_placement_seed_across_reference_rows(self):
        for n, (count, mean_time) in self.references.items():
            with self.subTest(pallets=n):
                run = solve_c02(n, unit_timing="service-only", initial_seed=0)
                self.assertEqual(run["initial_seed"], 0)
                self.assertFalse(run["deadlock"])
                self.assertEqual(run["pending_admission"], 0)
                self.assertAlmostEqual(run["throughput"] / count, 1, delta=0.06)
                if n != 25:
                    self.assertAlmostEqual(
                        run["average_throughput_time"] / mean_time, 1, delta=0.06
                    )
                if n == 14:
                    self.assertEqual(run["throughput"], 1440)
                    self.assertAlmostEqual(run["average_throughput_time"], 265)
        # A different legal start with the same control and clocks is periodic too.
        other = solve_c02(14, unit_timing="service-only", initial_seed=1)
        self.assertEqual(other["throughput"], 1344)
        self.assertAlmostEqual(other["average_throughput_time"], 285)

    def test_csim_table_one_against_counts_and_full_pallet_clock(self):
        # Pllana & Fahringer (2003), Table 1. The paper does not specify the
        # two timer edges. Use the same full pallet clock for every row.
        published = {
            13: (1320, 284.56), 16: (1440, 321.25), 17: (1442, 341.18),
            18: (1442, 361.64), 20: (1438, 401.03), 21: (1440, 420.86),
            22: (1442, 440.33), 23: (1438, 460.79), 24: (1439, 480.21),
            25: (1440, 499.33), 40: (1440, 794.10),
        }
        for n, (jobs, seconds) in published.items():
            with self.subTest(n=n):
                result = solve_c02(n, unit_timing="service-only")
                self.assertAlmostEqual(result["throughput"] / jobs, 1, delta=0.06)
                self.assertAlmostEqual(result["average_including_handling_seconds"] / seconds, 1, delta=0.06)

    @unittest.expectedFailure
    def test_simevents_13_pallets(self):
        self.assert_reference(13)

    @unittest.expectedFailure
    def test_simevents_14_pallets(self):
        self.assert_reference(14)

    @unittest.expectedFailure
    def test_simevents_25_pallets(self):
        self.assert_reference(25)

    def test_cyclic_policy_tracks_anylogic_full_cycle_references(self):
        # Breitenecker & Kittenberger (2003), p. 22, uses a full-cycle clock.
        for n, count, full_cycle in (
            (1, 150, 191.67),
            (12, 1409, 245.32),
            (13, 1409, 265.76),
            (20, 1409, 408.67),
            (40, 1409, 819.26),
        ):
            with self.subTest(n=n):
                r = solve_c02(n, controller="cyclic-a2")
                self.assertEqual(r["controller"], "cyclic-a2")
                self.assertIs(r["deadlock"], False)
                self.assertAlmostEqual(r["throughput"] / count, 1, delta=0.01)
                self.assertAlmostEqual(
                    r["average_including_handling_seconds"] / full_cycle, 1, delta=0.01
                )


if __name__ == "__main__":
    unittest.main()
