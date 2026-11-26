"""Production-path checks for QSS3/QSS4 Taylor coefficients and contacts."""

import math
import unittest

from argesim_benchmarks.ivp import InitialValueProblem
from argesim_benchmarks.solvers.advanced_qss import qss3, qss4


class HighOrderContactTests(unittest.TestCase):
    @staticmethod
    def problem(order: int) -> InitialValueProblem:
        def rhs(_time, state):
            # The chain produces x_k(t) = t**k. The order-th quantizer
            # stays at zero until t=1, then its stored value jumps to one.
            trigger = state[order - 1]
            before = order * state[order - 2]
            after = 1.5 - state[0]
            if trigger <= 1 / 8:
                rate = before
            elif trigger >= 1 / 2:
                rate = after
            else:
                # C^3 transition. The two local stencils stay on the plateaux.
                z = (trigger - 1 / 8) / (3 / 8)
                weight = z**4 * (35 + z * (-84 + z * (70 - 20 * z)))
                rate = before + weight * (after - before)
            return (1.0, *(k * state[k - 2] for k in range(2, order + 1)), rate)

        return InitialValueProblem(
            rhs, 0.0, (0.0,) * (order + 1), 2.0, autonomous=True
        )

    def test_model_contact_and_adjacent_thresholds(self):
        quantum = 9 / 8
        lower = math.nextafter(quantum, 0.0)
        upper = math.nextafter(quantum, math.inf)
        # After the first update, w's quantization gap is
        # 1+s/2-s**2/2, s=t-1. Its maximum is 9/8 at t=3/2.
        for order, solver in ((3, qss3), (4, qss4)):
            for derivative_step in (None, 1 / 32):
                for width, expected in (
                    (lower, 1.5 - math.sqrt(2 * (quantum - lower))),
                    (quantum, 1.5),
                    (upper, None),
                ):
                    with self.subTest(
                        order=order, derivative_step=derivative_step, width=width
                    ):
                        result = solver(
                            self.problem(order),
                            (100.0,) * (order - 1) + (1.0, width),
                            derivative_step=derivative_step,
                        )
                        self.assertAlmostEqual(result.times[1], 1.0, delta=1e-12)
                        # The next trigger event is at the terminal boundary;
                        # isolate the target component's earlier event.
                        interior = [time for time in result.times if 1.0 < time < 1.75]
                        if expected is None:
                            self.assertEqual(interior, [])
                        else:
                            self.assertEqual(len(interior), 1)
                            self.assertAlmostEqual(interior[0], expected, delta=1e-12)
