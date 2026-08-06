from fractions import Fraction
import unittest

from nsa_devs import HyperTime


class HyperTimeTests(unittest.TestCase):
    def test_microsteps_are_strictly_ordered_at_one_macro_time(self) -> None:
        t0 = HyperTime.at("3/2")
        t1 = t0.after_epsilon()
        t2 = t1.after_epsilon()

        self.assertLess(t0, t1)
        self.assertLess(t1, t2)
        self.assertEqual(t0.standard_part(), Fraction(3, 2))
        self.assertEqual(t1.standard_part(), t0.standard_part())
        self.assertEqual(t2.standard_part(), t0.standard_part())

    def test_finite_delay_advances_macro_time_and_resets_microstep(self) -> None:
        source = HyperTime.at(2, 7)
        target = source.after_finite("1/4")

        self.assertEqual(target, HyperTime.at("9/4", 0))
        self.assertGreater(target, source)

    def test_invalid_values_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            HyperTime.at(-1)
        with self.assertRaises(ValueError):
            HyperTime.at(0, -1)
        with self.assertRaises(ValueError):
            HyperTime.at(0).after_epsilon(0)


if __name__ == "__main__":
    unittest.main()

