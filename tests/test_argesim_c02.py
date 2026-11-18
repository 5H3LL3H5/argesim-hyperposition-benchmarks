import unittest

from argesim_benchmarks.models import solve_c02


class C02Tests(unittest.TestCase):
    def test_parameter_study_tracks_published_reference(self):
        # Historical proximity check against SNE 21(3-4), 2011, Table 2.
        # This partial model lacks belt blocking and has timing mismatches;
        # agreement within six percent does not establish model validation.
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

    def test_unimplemented_deadlock_is_not_returned_as_simulated_evidence(self):
        for num_pallets in (50, 60):
            with (
                self.subTest(num_pallets=num_pallets),
                self.assertRaisesRegex(NotImplementedError, "deadlock detection"),
            ):
                solve_c02(num_pallets)

    def test_invalid_pallet_counts_are_rejected(self):
        for value in (0, -1, 2.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solve_c02(value)


if __name__ == "__main__":
    unittest.main()
