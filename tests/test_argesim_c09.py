import math
import unittest

from argesim_benchmarks.catalog import BenchmarkStatus, benchmark
from argesim_benchmarks.models.c09_fuzzy_tanks import (
    C09Controller,
    C09DifferenceSignal,
    c09_controller_surface,
    c09_ifc_increment,
    c09_pfc_control,
    c09_run_benchmark,
    c09_validate,
    simulate_c09,
)


class C09Tests(unittest.TestCase):
    def test_ifc_surface_uses_centimetres_for_both_axes(self) -> None:
        # Figure 4: e=15 cm gives good=.4, low=.6; de=.0125 cm
        # gives rising=.5. Product rule weights are therefore .2 and .6.
        # IFC2: (-1e-4*.2 + 2e-4*.6)/.8 = 1.25e-4.
        # IFC1: use triangular areas 2.5e-4 and 1.25e-4 and their centroids.
        for controller, expected in (
            (C09Controller.IFC1, 1.5e-4),
            (C09Controller.IFC2, 1.25e-4),
        ):
            with self.subTest(controller=controller):
                surface = c09_controller_surface(controller, points=9)
                self.assertAlmostEqual(surface.x[6], 15.0)
                self.assertAlmostEqual(surface.y[5], 0.0125)
                self.assertAlmostEqual(surface.z[5][6], expected, places=12)

    def test_controller_surfaces_and_rule_directions(self) -> None:
        self.assertEqual(benchmark("C09").status, BenchmarkStatus.IMPLEMENTED)
        for controller in C09Controller:
            surface = c09_controller_surface(controller, points=7)
            self.assertEqual(len(surface.z), 7)
            self.assertTrue(all(len(row) == 7 for row in surface.z))
        self.assertGreater(c09_ifc_increment(0.30, 0.0), 0.0)
        self.assertLess(c09_ifc_increment(-0.30, 0.0), 0.0)
        self.assertGreater(c09_pfc_control(0.0, 0.30), 0.10)
        self.assertLess(c09_pfc_control(0.0, 0.30), 0.18)

    def test_sampled_hybrid_plant_is_finite(self) -> None:
        result = simulate_c09(C09Controller.IFC1, t_bound=200.0, output_step=20.0)
        self.assertEqual(result.times[-1], 200.0)
        self.assertTrue(all(math.isfinite(value) and value >= 0.0 for value in result.h2))
        self.assertTrue(all(0.0 <= value <= 0.3 for value in result.control))

    def test_complete_experiment_matches_published_qualitative_results(self) -> None:
        validation = c09_validate()
        self.assertTrue(validation.published_qualitative_behaviour)
        self.assertLess(abs(validation.ifc1_final_error), 1.0e-3)
        self.assertLess(abs(validation.ifc2_final_error), 1.0e-3)
        self.assertGreater(abs(validation.pfc_final_error), 0.1)
        benchmark_result = c09_run_benchmark(surface_points=5)
        self.assertEqual(len(benchmark_result.surfaces), 3)
        self.assertEqual(len(benchmark_result.transients), 3)

    def test_literal_printed_difference_remains_reproducible(self) -> None:
        reference = simulate_c09(
            C09Controller.IFC1,
            t_bound=200.0,
            output_step=200.0,
        )
        literal = simulate_c09(
            C09Controller.IFC1,
            t_bound=200.0,
            output_step=200.0,
            difference_signal=C09DifferenceSignal.LITERAL_ERROR_DIFFERENCE,
        )
        self.assertNotEqual(reference.control, literal.control)


if __name__ == "__main__":
    unittest.main()
