import unittest
from unittest.mock import patch

from argesim_benchmarks.catalog import BenchmarkStatus, benchmark
from argesim_benchmarks.models.c04_dining_philosophers import (
    C04Strategy,
    c04_compare_strategies,
    c04_refinement_study,
    run_c04,
)


class C04Tests(unittest.TestCase):
    def test_catalog_and_seeded_state_time_accounting(self) -> None:
        self.assertEqual(benchmark("C04").status, BenchmarkStatus.IMPLEMENTED)
        first = run_c04(C04Strategy.PUT_BACK, seed=11)
        second = run_c04(C04Strategy.PUT_BACK, seed=11)
        self.assertEqual(first, second)
        self.assertAlmostEqual(
            first.thinking_fraction + first.waiting_fraction + first.eating_fraction,
            1.0,
        )
        self.assertEqual(sum(first.philosopher_meals), first.meals)
        for fractions in first.philosopher_fractions:
            self.assertAlmostEqual(sum(fractions), 1.0)

    def test_unprotected_deadlocks_and_protected_strategies_progress(self) -> None:
        self.assertTrue(
            run_c04(
                C04Strategy.UNPROTECTED,
                seed=1,
                acquisition_delay=1.0,
            ).deadlocked
        )
        for strategy in (
            C04Strategy.WAITER,
            C04Strategy.CLEANING,
            C04Strategy.PUT_BACK,
        ):
            result = run_c04(strategy, seed=1)
            self.assertFalse(result.deadlocked)
            self.assertGreater(result.meals, 0)

    def test_comparison_contains_all_strategies(self) -> None:
        summaries = c04_compare_strategies(replications=3)
        self.assertEqual({summary.strategy for summary in summaries}, set(C04Strategy))
        self.assertTrue(
            all(summary.mean_meal_count_range >= 0.0 for summary in summaries)
        )

    def test_resource_release_cannot_bypass_pending_acquisition_delay(self) -> None:
        # Philosopher 0 finishes at 0.3, waking philosopher 2, whose second
        # acquisition is due at 0.35. Its meal must finish at 0.45, not 0.4.
        with patch(
            "argesim_benchmarks.models.c04_dining_philosophers._C04Simulation.duration",
            return_value=0.1,
        ):
            result = run_c04(
                "unprotected",
                horizon=0.425,
                acquisition_delay=0.2,
                initial_thinking_times=(0.0, 100.0, 0.15, 100.0, 100.0),
            )
        self.assertEqual(result.philosopher_meals, (1, 0, 0, 0, 0))

    def test_dirty_forks_cannot_be_reused_before_cleaning_completes(self) -> None:
        with patch(
            "argesim_benchmarks.models.c04_dining_philosophers._C04Simulation.duration",
            return_value=1.0,
        ):
            result = run_c04(
                "cleaning",
                philosophers=2,
                horizon=2.5,
                cleaning_delay=2.0,
                initial_thinking_times=(0.0, 0.0),
            )
        self.assertEqual(result.meals, 1)
        self.assertEqual(result.completed_cleanings, 0)

    def test_neighbour_request_prevents_a_newer_hungry_philosopher_overtaking(
        self,
    ) -> None:
        with patch(
            "argesim_benchmarks.models.c04_dining_philosophers._C04Simulation.duration",
            return_value=1.0,
        ):
            result = run_c04(
                "requests",
                philosophers=2,
                horizon=4.1,
                cleaning_delay=2.0,
                request_delay=0.25,
                initial_thinking_times=(0.0, 0.0),
            )
        self.assertEqual(result.philosopher_meals, (1, 1))
        self.assertEqual(result.completed_cleanings, 2)
        self.assertEqual(result.request_tokens_sent, 4)

    def test_refinements_exhibit_deadlock_and_selective_starvation(self) -> None:
        results = c04_refinement_study(horizon=30.0)
        self.assertTrue(results["hungry-deadlock"].deadlocked)
        self.assertEqual(results["hungry-deadlock"].meals, 0)
        self.assertGreater(results["cleaning"].completed_cleanings, 0)
        self.assertGreater(results["neighbour-requests"].request_tokens_sent, 0)
        for policy in ("hoard", "targeted-hold"):
            self.assertEqual(results[policy].philosopher_meals[1], 0)
            self.assertGreater(results[policy].philosopher_meals[0], 0)
        self.assertEqual(results["hoard"].philosopher_meals[4], 0)
        self.assertGreater(results["targeted-hold"].philosopher_meals[4], 0)
        with patch(
            "argesim_benchmarks.models.c04_dining_philosophers._C04Simulation.duration",
            return_value=1.0,
        ):
            blocked = run_c04(
                "requests",
                philosophers=2,
                horizon=10.0,
                initial_thinking_times=(0.0, 0.5),
                request_delay=0.1,
                conspiracy="hoard",
                conspirators=(0,),
                victims=(1,),
            )
        self.assertTrue(blocked.deadlocked)
        self.assertEqual(blocked.philosopher_meals, (1, 0))

    def test_refinement_controls_reject_inconsistent_inputs(self) -> None:
        for kwargs in (
            {"cleaning_delay": 0.0},
            {"request_delay": float("nan")},
            {"initial_thinking_times": (0.0,)},
            {"conspiracy": "hoard", "conspirators": (0,), "victims": (0,)},
            {"conspiracy": "hoard", "conspirators": (5,), "victims": (1,)},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                run_c04("cleaning", **kwargs)


if __name__ == "__main__":
    unittest.main()
