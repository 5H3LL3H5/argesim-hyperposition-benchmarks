"""A QSS1 internal update preempted by an external derivative message."""

import unittest
from fractions import Fraction

from argesim_benchmarks import InitialValueProblem, qss1
from nsa_devs.scheduler import DesScheduler


class QuantizerEventTrace(unittest.TestCase):
    def test_external_slope_change_preserves_the_old_quantized_value(self):
        clock = DesScheduler()
        delta = Fraction(1, 4)
        x = q = at = Fraction(0)
        rate = Fraction(1)
        emitted = []

        def schedule_hit():
            target = q + (delta if rate > 0 else -delta)
            return clock.schedule((target - x) / rate, "publish", publish, target)

        def publish(target):
            nonlocal at, x, q, pending
            at, x, q = clock.time.macro, target, target
            emitted.append((at, q))
            pending = schedule_hit()

        def external(new_rate):
            nonlocal at, x, rate, pending
            x += rate * (clock.time.macro - at)
            at = clock.time.macro
            clock.cancel(pending)
            rate = new_rate
            pending = schedule_hit()

        pending = schedule_hit()
        clock.schedule(Fraction(1, 8), "new derivative", external, Fraction(-1, 2))
        clock.run(Fraction(7, 5))
        self.assertEqual(
            emitted, [(Fraction(7, 8), -delta), (Fraction(11, 8), -2 * delta)]
        )

        # Drive the stand-alone solver from a second state with the same first
        # boundary. Subsequent updates of that clock leave x's derivative fixed.
        p = InitialValueProblem(
            lambda t, y: (1.0, 1.0 if y[0] < 0.125 else -0.5),
            0,
            (0.0, 0.0),
            1.4,
            autonomous=True,
        )
        result = qss1(p, (0.125, 0.25))
        for t, target in emitted:
            self.assertEqual(
                result.states[result.times.index(float(t))][1], float(target)
            )
        self.assertAlmostEqual(result.final_state[1], 0.125 - 0.5 * (1.4 - 0.125))
