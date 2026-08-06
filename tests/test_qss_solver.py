import math
import unittest
from itertools import pairwise

from argesim_benchmarks import InitialValueProblem, qss1, qss2


class QssSolverTests(unittest.TestCase):
    @staticmethod
    def decay_problem() -> InitialValueProblem:
        return InitialValueProblem(
            lambda _time, state: (-state[0],),
            0.0,
            (1.0,),
            1.0,
            name="qss-decay",
            autonomous=True,
        )

    def test_qss1_endpoint_converges_as_quantum_decreases(self) -> None:
        exact = math.exp(-1.0)
        errors = [
            abs(qss1(self.decay_problem(), quantum).final_state[0] - exact)
            for quantum in (0.1, 0.05, 0.025, 0.0125)
        ]
        self.assertTrue(all(later < earlier for earlier, later in pairwise(errors)))
        self.assertLess(errors[-1], 0.01)

    def test_qss1_uses_asynchronous_quantization_events(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (-state[0], -4.0 * state[1]),
            0.0,
            (1.0, 1.0),
            0.25,
            autonomous=True,
        )
        result = qss1(problem, (0.1, 0.1))
        self.assertGreater(result.stats.accepted_steps, 2)
        self.assertEqual(result.final_time, 0.25)
        self.assertTrue(
            all(
                later >= earlier
                for earlier, later in zip(result.times, result.times[1:])
            )
        )

    def test_qss2_endpoint_converges_as_quantum_decreases(self) -> None:
        exact = math.exp(-1.0)
        errors = [
            abs(qss2(self.decay_problem(), quantum).final_state[0] - exact)
            for quantum in (0.1, 0.05, 0.025, 0.0125)
        ]
        self.assertTrue(
            all(later <= earlier for earlier, later in pairwise(errors))
        )
        # QSS2 should be more accurate for the same quantum than QSS1.
        self.assertLess(errors[-1], 0.005)

    def test_qss2_uses_asynchronous_quantization_events(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (-state[0], -4.0 * state[1]),
            0.0,
            (1.0, 1.0),
            0.5,
            autonomous=True,
        )
        # qss2 parabolic steps are larger, so we need a larger t_bound
        # or smaller quantum to trigger more events.
        result = qss2(problem, (0.01, 0.01))
        self.assertGreater(result.stats.accepted_steps, 2)
        self.assertEqual(result.final_time, 0.5)
        self.assertTrue(
            all(
                later >= earlier
                for earlier, later in zip(result.times, result.times[1:])
            )
        )

    def test_non_autonomous_problem_is_rejected(self) -> None:
        problem = InitialValueProblem(lambda time, _state: (time,), 0.0, (0.0,), 1.0)
        with self.assertRaises(ValueError):
            qss1(problem, 0.1)
        with self.assertRaises(ValueError):
            qss2(problem, 0.1)

    def test_quantum_dimension_is_checked(self) -> None:
        with self.assertRaises(ValueError):
            qss1(self.decay_problem(), (0.1, 0.2))
        with self.assertRaises(ValueError):
            qss2(self.decay_problem(), (0.1, 0.2))


    def test_qss2_catastrophic_cancellation_edge_case(self) -> None:
        # Trigger b == 0 and c_eff == 0 in QSS2 logic.
        problem = InitialValueProblem(
            lambda _time, state: (1.0, state[0]),
            0.0,
            (0.0, 0.0),
            2.0,
            autonomous=True,
        )
        result = qss2(problem, 0.1)
        self.assertEqual(result.final_time, 2.0)
        self.assertGreater(result.stats.accepted_steps, 0)

if __name__ == "__main__":
    unittest.main()
