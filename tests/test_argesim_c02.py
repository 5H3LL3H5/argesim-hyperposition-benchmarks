import math
import unittest

from argesim_benchmarks.models import solve_c02
from argesim_benchmarks.models.c02_flexible_assembly import (
    C02Constants,
    Message,
    Pallet,
    StationModel,
    _station_configs,
)


class C02Tests(unittest.TestCase):
    @unittest.expectedFailure
    def test_parameter_study_tracks_published_reference(self):
        # Historical proximity check against SNE 21(3-4), 2011, Table 2.
        # Correct geometry exposes a >6% mismatch for 10 pallets. Keep the
        # reference threshold unchanged and the failure explicit until the
        # missing blocking/merging model is implemented; do not recalibrate
        # physical lengths or operation times to fit this table.
        reference = {
            10: (959.0, 285.0),
            14: (1439.0, 265.0),
            20: (1439.0, 385.0),
            40: (1437.0, 787.0),
        }
        for num_pallets, (throughput, transit_time) in reference.items():
            with self.subTest(num_pallets=num_pallets):
                result = solve_c02(num_pallets)
                self.assertIsNone(result["deadlock"])
                self.assertAlmostEqual(
                    result["throughput"] / throughput, 1.0, delta=0.06
                )
                self.assertAlmostEqual(
                    result["average_throughput_time"] / transit_time,
                    1.0,
                    delta=0.06,
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

    def test_unimplemented_deadlock_is_not_returned_as_simulated_evidence(self):
        # Keep execution errors outside the expected-failure reference test.
        partial = solve_c02(10)
        self.assertIsNone(partial["deadlock"])
        self.assertGreater(partial["throughput"], 0)
        self.assertTrue(math.isfinite(partial["average_throughput_time"]))
        for num_pallets in (50, 60):
            with (
                self.subTest(num_pallets=num_pallets),
                self.assertRaisesRegex(NotImplementedError, "deadlock detection"),
            ):
                solve_c02(num_pallets)

    def test_invalid_pallet_counts_are_rejected(self):
        for value in (0, -1, 2.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                solve_c02(value)


if __name__ == "__main__":
    unittest.main()
