import unittest

from argesim_benchmarks.models.c21_state_events import (
    simulate_c21_bouncing_ball_event_contact,
    simulate_c21_rotating_pendulum,
)


class HybridRuntimeTests(unittest.TestCase):
    def test_classical_and_qss2_share_bounce_event_semantics(self):
        classical = simulate_c21_bouncing_ball_event_contact(
            t_bound=2.0,
            method="rk45",
        )
        quantized = simulate_c21_bouncing_ball_event_contact(
            t_bound=2.0,
            method="qss2",
            options={"quantum": (1.0e-3, 1.0e-3)},
        )
        self.assertEqual(len(classical.events), 1)
        self.assertEqual(len(quantized.events), 1)
        self.assertAlmostEqual(
            float(classical.events[0].time.macro),
            float(quantized.events[0].time.macro),
            delta=2.0e-4,
        )
        for result in (classical, quantized):
            event = result.events[0]
            self.assertEqual(event.name, "bounce")
            self.assertEqual(event.state_after[0], 0.0)
            self.assertGreater(event.state_after[1], 0.0)
            self.assertEqual(event.time.micro, 1)

    def test_dimension_changing_transition_uses_the_same_runtime(self):
        result = simulate_c21_rotating_pendulum(t_bound=5.0, method="qss2")
        self.assertEqual(len(result.events), 1)
        event = result.events[0]
        self.assertEqual(event.name, "fall")
        self.assertEqual(event.source_mode, "swinging")
        self.assertEqual(event.target_mode, "falling")
        self.assertEqual(len(event.state_before), 2)
        self.assertEqual(len(event.state_after), 4)
        self.assertEqual(len(result.final_state), 4)


if __name__ == "__main__":
    unittest.main()
