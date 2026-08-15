import math
import unittest

from argesim_benchmarks.ivp import IntegrationError
from argesim_benchmarks.solvers import brentq


class BrentRootTests(unittest.TestCase):
    def test_converges_with_forward_and_reversed_brackets(self) -> None:
        for left, right in ((0.0, 2.0), (2.0, 0.0)):
            root = brentq(lambda value: value * value - 2.0, left, right)
            self.assertAlmostEqual(root, math.sqrt(2.0), delta=2.0e-12)

    def test_returns_exact_endpoint_roots(self) -> None:
        self.assertEqual(brentq(lambda value: value, 0.0, 2.0), 0.0)
        self.assertEqual(brentq(lambda value: value - 2.0, 0.0, 2.0), 2.0)

    def test_rejects_unbracketed_and_non_finite_functions(self) -> None:
        with self.assertRaises(ValueError):
            brentq(lambda value: value * value + 1.0, -1.0, 1.0)
        with self.assertRaises(IntegrationError):
            brentq(lambda _value: math.nan, -1.0, 1.0)

    def test_validates_controls_and_reports_nonconvergence(self) -> None:
        with self.assertRaises(ValueError):
            brentq(lambda value: value, -1.0, 1.0, tol=0.0)
        with self.assertRaises(TypeError):
            brentq(lambda value: value, -1.0, 1.0, maxiter=True)
        with self.assertRaises(IntegrationError):
            brentq(lambda value: value * value - 2.0, 0.0, 2.0, maxiter=1)


if __name__ == "__main__":
    unittest.main()
