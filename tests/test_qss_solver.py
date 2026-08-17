import math
import unittest
from itertools import pairwise

from argesim_benchmarks import InitialValueProblem, cqss1, qss1, qss2


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

    def test_centered_qss_preserves_harmonic_oscillator_energy(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (state[1], -state[0]),
            0.0,
            (1.0, 0.0),
            100.0,
            name="cqss-harmonic-oscillator",
            autonomous=True,
        )
        result = cqss1(problem, 0.05)
        energies = [
            0.5 * (state[0] ** 2 + state[1] ** 2)
            for state in result.states
        ]
        self.assertEqual(result.final_time, 100.0)
        self.assertLess(max(energies) - min(energies), 6.0e-4)

    def test_centered_qss_uses_cell_midpoints(self) -> None:
        samples = []

        def rhs(_time, state):
            samples.append(tuple(state))
            return (1.0,)

        problem = InitialValueProblem(
            rhs, 0.0, (0.21,), 0.25, autonomous=True
        )
        result = cqss1(problem, 0.1)
        self.assertEqual(samples[0], (0.25,))
        self.assertEqual(samples[1], (0.35000000000000003,))
        self.assertAlmostEqual(result.final_state[0], 0.46)

    def test_centered_qss_reports_its_no_hysteresis_cycle(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (-state[0],),
            0.0,
            (0.0,),
            1.0,
            autonomous=True,
        )
        with self.assertRaisesRegex(RuntimeError, "no hysteresis"):
            cqss1(problem, 0.1)

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

    def test_qss2_scales_finite_difference_against_fast_nonlinearity(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (1.0e8 * state[0] ** 2,),
            0.0,
            (1.0,),
            1.0e-9,
            autonomous=True,
        )
        result = qss2(problem, 1.0e-3, max_events=100)
        self.assertLess(result.stats.accepted_steps, 20)
        self.assertAlmostEqual(result.final_state[0], 1.0 / 0.9, delta=2.0e-4)

    def test_controls_reject_boolean_and_fractional_event_limits(self) -> None:
        with self.assertRaises(TypeError):
            qss1(self.decay_problem(), True)
        with self.assertRaises(TypeError):
            qss2(self.decay_problem(), (0.1, True))
        with self.assertRaises(TypeError):
            qss2(self.decay_problem(), 0.1, max_events=10.5)
        with self.assertRaises(TypeError):
            qss1(self.decay_problem(), 0.1, simultaneous_tolerance=True)

    def test_simultaneous_events_respect_the_strict_event_limit(self) -> None:
        problem = InitialValueProblem(
            lambda _time, state: (state[0], state[1]),
            0.0,
            (1.0, 1.0),
            1.0,
            autonomous=True,
        )
        with self.assertRaisesRegex(RuntimeError, "exceeded max_events"):
            qss1(problem, 0.1, max_events=1)
        with self.assertRaisesRegex(RuntimeError, "exceeded max_events"):
            qss2(problem, 0.1, max_events=1)

if __name__ == "__main__":
    unittest.main()
