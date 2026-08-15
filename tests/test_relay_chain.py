import unittest
from fractions import Fraction

from nsa_devs import DesScheduler, HyperTime, run_relay_chain


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

    def test_scheduler_orders_same_time_events_and_nested_microsteps(self) -> None:
        scheduler = DesScheduler()
        trace: list[tuple[str, HyperTime]] = []

        def first() -> None:
            trace.append(("first", scheduler.time))
            scheduler.schedule(
                0.0,
                "nested",
                lambda: trace.append(("nested", scheduler.time)),
            )

        scheduler.schedule(0.0, "first", first)
        scheduler.schedule(
            0.0,
            "second",
            lambda: trace.append(("second", scheduler.time)),
        )
        scheduler.run(0.0)

        self.assertEqual([name for name, _time in trace], ["first", "second", "nested"])
        self.assertEqual([time.micro for _name, time in trace], [1, 1, 2])

    def test_scheduler_and_relay_validate_public_inputs(self) -> None:
        scheduler = DesScheduler()
        with self.assertRaises(TypeError):
            scheduler.schedule(True, "event", lambda: None)
        with self.assertRaises(ValueError):
            scheduler.schedule(0.0, "", lambda: None)
        with self.assertRaises(TypeError):
            scheduler.schedule(0.0, "event", None)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            scheduler.run(-1.0)
        with self.assertRaises(TypeError):
            scheduler.run(0.0, max_events=True)
        with self.assertRaises(TypeError):
            run_relay_chain(2, input_delay_microsteps=True)
        with self.assertRaises(TypeError):
            run_relay_chain(2, initial_payload=True)


if __name__ == "__main__":
    unittest.main()
