import unittest

from argesim_benchmarks.models import solve_c02


class C02Tests(unittest.TestCase):
    def test_parameter_study_tracks_published_reference(self):
        # SNE 21(3-4), 2011, Table 2.  The independent implementation is
        # expected to remain within six percent of both reported metrics.
        reference = {
            10: (959.0, 285.0),
            14: (1439.0, 265.0),
            20: (1439.0, 385.0),
            40: (1437.0, 787.0),
        }
        for num_pallets, (throughput, transit_time) in reference.items():
            with self.subTest(num_pallets=num_pallets):
                result = solve_c02(num_pallets)
                self.assertFalse(result["deadlock"])
                self.assertAlmostEqual(
                    result["throughput"] / throughput, 1.0, delta=0.06
                )
                self.assertAlmostEqual(
                    result["average_throughput_time"] / transit_time,
                    1.0,
                    delta=0.06,
                )

    def test_reference_deadlock_region_is_explicit(self):
        for num_pallets in (50, 60):
            with self.subTest(num_pallets=num_pallets):
                result = solve_c02(num_pallets)
                self.assertTrue(result["deadlock"])
                self.assertEqual(result["throughput"], 0.0)

    def test_invalid_pallet_counts_are_rejected(self):
        for value in (0, -1, 2.5, True):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    solve_c02(value)


if __name__ == "__main__":
    unittest.main()
