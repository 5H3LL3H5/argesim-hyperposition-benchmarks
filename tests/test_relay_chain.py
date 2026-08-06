from fractions import Fraction
import unittest

from nsa_devs import HyperTime, run_relay_chain


class RelayChainTests(unittest.TestCase):
    def test_finite_chain_has_analytical_microstep_trace(self) -> None:
        result = run_relay_chain(
            length=8,
            initial_payload=41,
            start_time=HyperTime.at("5/2"),
        )

        self.assertEqual(result.final_payload, 49)
        self.assertEqual(len(result.trace), 8)
        self.assertEqual(
            [event.component for event in result.trace],
            list(range(8)),
        )
        self.assertEqual(
            [event.output_time.micro for event in result.trace],
            list(range(1, 9)),
        )
        self.assertTrue(
            all(
                event.output_time.standard_part() == Fraction(5, 2)
                for event in result.trace
            )
        )

    def test_positive_component_delay_is_configurable(self) -> None:
        result = run_relay_chain(length=4, input_delay_microsteps=3)
        self.assertEqual(
            [event.output_time.micro for event in result.trace],
            [3, 6, 9, 12],
        )

    def test_repeated_runs_are_deterministic(self) -> None:
        first = run_relay_chain(length=100, initial_payload=-10)
        second = run_relay_chain(length=100, initial_payload=-10)
        self.assertEqual(first, second)
        self.assertEqual(first.checksum, second.checksum)


if __name__ == "__main__":
    unittest.main()

