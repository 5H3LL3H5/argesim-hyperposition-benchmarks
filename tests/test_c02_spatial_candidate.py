import unittest

from argesim_benchmarks.experiments.c02_spatial import C02SpatialCandidate
from argesim_benchmarks.models.c02_flexible_assembly import C02Constants


class C02SpatialCandidateTests(unittest.TestCase):
    """Check only the candidate's claimed invariants, not C02 conformance."""

    def test_high_load_keeps_parts_and_finite_station_storage(self):
        model = C02SpatialCandidate(
            60, constants=C02Constants(warmup_minutes=0, end_minutes=10)
        )
        result = model.run()
        self.assertEqual(result["stopped_at_seconds"], 600)
        self.assertEqual(len({part.identifier for part in model.pallets}), 60)
        self.assertGreaterEqual(result["minimum_main_spacing_m"], 0.36)
        self.assertGreaterEqual(result["minimum_branch_spacing_m"], 0.36)
        limits = (3, 2, 2, 2, 2, 2, 2, 3)
        self.assertTrue(
            all(
                actual <= limit
                for actual, limit in zip(
                    result["maximum_input_buffer_occupancy"], limits
                )
            )
        )
        self.assertTrue(
            all(actual <= 1 for actual in result["maximum_output_buffer_occupancy"])
        )
        self.assertEqual(
            result["scope"], "experimental; shifter zero-storage geometry incomplete"
        )

    def test_partial_operation_group_cannot_be_interleaved_with_a2(self):
        model = C02SpatialCandidate(
            1, constants=C02Constants(warmup_minutes=0, end_minutes=1)
        )
        part = model.pallets[0]
        part.loaded = True
        for bits, needs_a2 in (
            (0, True),
            (2, False),
            (4, False),
            (8, False),
            (6, False),
            (14, True),
            (15, False),
        ):
            part.operations = bits
            self.assertEqual(model._needs(part, 1), needs_a2)
            self.assertEqual(model._needs(part, 2), needs_a2)
            self.assertEqual(model._needs(part, 3), needs_a2)

    def test_overlapping_and_out_of_range_initial_positions_are_rejected(self):
        for positions in ((0.0, 0.35), (0.0, 22.40), (-0.01, 0.5)):
            with self.subTest(positions=positions), self.assertRaises(ValueError):
                C02SpatialCandidate(2, initial_positions_m=positions)


if __name__ == "__main__":
    unittest.main()
