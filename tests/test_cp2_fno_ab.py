"""Deterministic data and contract checks for the CP2 FNO ablation."""
import importlib.util
import unittest

import numpy as np

from argesim_benchmarks.experiments import cp2_fields as fields


@unittest.skipUnless(importlib.util.find_spec("torch") and importlib.util.find_spec("neuralop"),
                     "requires neuraloperator optional extra")
class FNOAblationTests(unittest.TestCase):
    def test_random_plucks_have_fixed_ends_and_exact_initial_time(self):
        from argesim_benchmarks.experiments import cp2_fno_ab as ab

        x, y = ab.triangle_samples(12, np.random.default_rng(77))
        self.assertEqual(x.shape, (12, 65))
        self.assertEqual(y.shape, (12, 2, 65))
        np.testing.assert_array_equal(x[:, [0, -1]], np.zeros((12, 2)))
        np.testing.assert_allclose(y[:, :, [0, -1]], np.zeros((12, 2, 2)), atol=1e-6)
        self.assertTrue(np.isfinite(y).all())

    def test_splits_reproducible_and_disjoint(self):
        from argesim_benchmarks.experiments import cp2_fno_ab as ab

        for variant in ab.VARIANTS:
            first = ab.make_splits(2027, variant)
            second = ab.make_splits(2027, variant)
            self.assertEqual(tuple(len(a) for a, _ in first), ab.SPLIT_SIZES)
            for (a, b), (c, d) in zip(first, second):
                np.testing.assert_array_equal(a, c)
                np.testing.assert_array_equal(b, d)
            self.assertEqual(len({row.tobytes() for a, _ in first for row in a}),
                             sum(ab.SPLIT_SIZES))

    def test_gradient_loss_zero_for_exact_match(self):
        import torch
        from argesim_benchmarks.experiments import cp2_fno_ab as ab

        x = torch.randn(2, 2, 65)
        self.assertEqual(ab.gradient_loss(x, x).item(), 0.0)
        self.assertGreater(ab.gradient_loss(x + torch.linspace(0, 1, 65), x).item(), 0.0)

    def test_model_output_grid_invariance(self):
        from argesim_benchmarks.experiments import cp2_fno_ab as ab
        from argesim_benchmarks.experiments import cp2_operators as baseline

        for variant in ab.VARIANTS:
            model = ab.make_model(variant)
            for nodes in (65, 501):
                x = np.sin(np.linspace(0, np.pi, nodes)) * fields.ROPE.h
                prediction = baseline.predict_array("rope", model, x)
                self.assertEqual(prediction.shape, (2, nodes))
                np.testing.assert_array_equal(prediction[:, [0, -1]], np.zeros((2, 2)))


if __name__ == "__main__":
    unittest.main()
