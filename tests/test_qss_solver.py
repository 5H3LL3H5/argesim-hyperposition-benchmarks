import math
import unittest
from itertools import pairwise

from argesim_benchmarks import InitialValueProblem, qss1


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

    def test_non_autonomous_problem_is_rejected(self) -> None:
        problem = InitialValueProblem(lambda time, _state: (time,), 0.0, (0.0,), 1.0)
        with self.assertRaises(ValueError):
            qss1(problem, 0.1)

    def test_quantum_dimension_is_checked(self) -> None:
        with self.assertRaises(ValueError):
            qss1(self.decay_problem(), (0.1, 0.2))


if __name__ == "__main__":
    unittest.main()
