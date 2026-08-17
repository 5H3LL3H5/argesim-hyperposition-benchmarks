import unittest

from argesim_benchmarks.catalog import BenchmarkStatus, benchmark
from argesim_benchmarks.models.c04_dining_philosophers import (
    C04Strategy,
    c04_compare_strategies,
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
        self.assertTrue(all(summary.mean_meal_count_range >= 0.0 for summary in summaries))


if __name__ == "__main__":
    unittest.main()
