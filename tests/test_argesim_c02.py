import math
import unittest

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

    def test_parameter_study_tracks_published_reference(self):
        # Pingel & Pawletta (2011), Table 2. The original 6% band also
        # applies to the former ten-pallet expected failure.
        reference = {
            10: (959.0, 285.0),
            14: (1439.0, 265.0),
            20: (1439.0, 385.0),
            40: (1437.0, 787.0),
        }
        for num_pallets, (throughput, transit_time) in reference.items():
            with self.subTest(num_pallets=num_pallets):
                result = solve_c02(num_pallets)
                self.assertIs(result["deadlock"], False)
                self.assertEqual(result["pending_admission"], 0)
                self.assertAlmostEqual(
                    result["throughput"] / throughput, 1.0, delta=0.06
                )
                self.assertAlmostEqual(
                    result["average_throughput_time"] / transit_time, 1.0, delta=0.06
                )

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


if __name__ == "__main__":
    unittest.main()
