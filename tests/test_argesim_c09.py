import math
import statistics
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
        # Fig. 4b: rising spans -.001 to .025 cm, so at .0125 cm
        # its weight is 13.5/26. Good and low have weights .4 and .6.
        for controller, expected in (
            (C09Controller.IFC1, 0.00014393939393939394),
            (C09Controller.IFC2, 0.00012285714285714286),
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

    def test_level_change_memberships_overlap_at_zero(self):
        # For e=1 cm the two slow singletons cancel in the numerator,
        # but each contributes .96/26 to the denominator.
        expected = .04 * 2e-4 / (.04 + 2 * .96 / 26)
        self.assertAlmostEqual(c09_ifc_increment(.01, 0., C09Controller.IFC2),
                               expected, places=12)

    def test_complete_experiment_reports_the_published_figure_windows(self) -> None:
        validation = c09_validate()
        checks = validation.figure_checks
        self.assertEqual([c.window_s for c in checks],
                         [(24000, 28000), (44000, 46000), (54000, 56000)])
        for check in checks:
            self.assertEqual(check.within_tolerance,
                             abs(check.model_cm - check.reference_cm) <= check.tolerance_cm)
        self.assertTrue(checks[1].within_tolerance)
        if validation.ifc2_second_setpoint_overshoot <= 0.01:
            self.assertFalse(validation.published_qualitative_behaviour)
        if all(check.within_tolerance for check in checks):
            self.assertEqual(c09_validate(require_figure_match=True), validation)
        else:
            with self.assertRaisesRegex(ValueError, "outside the 1 cm figure tolerance"):
                c09_validate(require_figure_match=True)
        self.assertLess(abs(validation.ifc1_final_error), 1.0e-3)
        self.assertLess(abs(validation.ifc2_final_error), 1.0e-3)
        self.assertGreater(abs(validation.pfc_final_error), 0.1)
        benchmark_result = c09_run_benchmark(surface_points=5)
        self.assertEqual(len(benchmark_result.surfaces), 3)
        self.assertEqual(len(benchmark_result.transients), 3)
        traces = {run.controller: run for run in benchmark_result.transients}
        for check in checks:
            run = traces[check.controller]
            lo, hi = check.window_s
            levels = [100 * h for t, h in zip(run.times, run.h2) if lo <= t <= hi]
            observed = max(levels) if check.statistic == "peak" else statistics.median(levels)
            self.assertAlmostEqual(check.model_cm, observed, places=8)
            self.assertEqual(check.tolerance_cm, 1.0)

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
