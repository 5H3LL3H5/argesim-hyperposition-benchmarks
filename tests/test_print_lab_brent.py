"""Regression tests for the Brent implementation readers actually download."""

import math
import runpy
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path
from zipfile import ZipFile

LAB = (
    Path(__file__).resolve().parents[1]
    / "docs/lehrbuch/gesamtausgabe/pakete/Laborquellen.zip"
)


class PrintLabBrentTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with tempfile.TemporaryDirectory() as directory, ZipFile(LAB) as archive:
            example = archive.extract("beispiele/ereignis.py", directory)
            module = runpy.run_path(example)
        cls.brent = staticmethod(module["brent"])
        cls.bracket = module["EventBracket"]

    def test_rounded_midpoint_respects_tolerance_in_both_directions(self):
        h = math.ulp(1.0)
        for left, offset in ((1.0, Fraction(1, 4)), (1.0 + h, Fraction(11, 4))):
            with self.subTest(left=left, offset=offset):
                exact = Fraction(left) + Fraction(h) * offset

                def watchdog(t):
                    return float((Fraction(t) - exact) / Fraction(h))

                result = self.brent(watchdog, left, left + 3 * h, 1.5 * h)
                if isinstance(result, self.bracket):
                    self.assertLessEqual(Fraction(result.left), exact)
                    self.assertLessEqual(exact, Fraction(result.right))
                    self.assertEqual(math.nextafter(result.left, math.inf), result.right)
                    self.assertLess(result.left_value * result.right_value, 0)
                    self.assertEqual(result.diagnosis, "time_resolution")
                else:
                    self.assertLessEqual(abs(Fraction(result) - exact), Fraction(1.5 * h))

    def test_adjacent_times_return_original_bracket(self):
        right = math.nextafter(1.0, math.inf)
        result = self.brent(lambda t: 2**53 * (t - 1) - 1, 1.0, right, 1e-16)
        self.assertIsInstance(result, self.bracket)
        self.assertEqual((result.left, result.right, result.left_value, result.right_value),
                         (1.0, right, -1, 1))
        self.assertEqual(result.diagnosis, "time_resolution")

    def test_ordinary_root(self):
        result = self.brent(lambda t: t * t - 2, 1.0, 2.0, 1e-12)
        self.assertIsInstance(result, float)
        self.assertLessEqual(abs(result - math.sqrt(2)), 1e-12)
