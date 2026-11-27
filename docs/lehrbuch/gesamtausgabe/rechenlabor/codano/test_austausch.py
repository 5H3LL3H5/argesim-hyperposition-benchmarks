"""Compare the teaching reference with independent matrix exponentiation."""

import unittest

import numpy as np
from scipy.linalg import expm

from austausch import DIFFUSION, HORIZON, RATE, sample


class ReferenceTest(unittest.TestCase):
    def test_first_mode_exact_solution(self):
        coefficients = np.zeros((1, 2, 6))
        coefficients[0, :, 0] = (1, 2)
        x, y = sample(coefficients, 13)
        mu = 2 * np.pi**2
        matrix = np.array(
            [[-RATE - DIFFUSION[0] * mu, RATE], [RATE, -RATE - DIFFUSION[1] * mu]]
        )
        expected = expm(HORIZON * matrix) @ coefficients[0, :, 0]
        np.testing.assert_allclose(x[0, :, 6, 6], [1, 2], atol=1e-7)
        np.testing.assert_allclose(y[0, :, 6, 6], expected, atol=1e-7)
        for field in (x, y):
            self.assertEqual(float(field[..., [0, -1]].abs().max()), 0)
            self.assertEqual(float(field[..., [0, -1], :].abs().max()), 0)

    def test_second_field_changes_first_field(self):
        coefficients = np.zeros((2, 2, 6))
        coefficients[:, 0, 0] = 1
        coefficients[1, 1, 0] = 1
        x, y = sample(coefficients, 25)
        self.assertTrue(x[0, 0].equal(x[1, 0]))
        self.assertGreater(float(y[1, 0, 12, 12] - y[0, 0, 12, 12]), 0.1)

    def test_cross_field_gain_symmetric_at_two_modes(self):
        for mode, point, expected in ((0, 12, 0.222055180593), (4, 4, 0.056614215014)):
            with self.subTest(mode=mode):
                coefficients = np.zeros((2, 2, 6))
                coefficients[0, 0, mode] = 1
                coefficients[1, 1, mode] = 1
                _, future = sample(coefficients, 25)
                self.assertAlmostEqual(float(future[0, 1, point, 12]), expected)
                self.assertAlmostEqual(float(future[1, 0, point, 12]), expected)
