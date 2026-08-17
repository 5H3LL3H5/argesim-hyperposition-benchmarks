import unittest

from argesim_benchmarks.hybrid import HybridMode, simulate_hybrid

from argesim_benchmarks.models.c21_state_events import (
    simulate_c21_bouncing_ball_event_contact,
    simulate_c21_rotating_pendulum,
)


class HybridRuntimeTests(unittest.TestCase):
    def test_bounded_segments_preserve_continuous_result(self):
        mode = HybridMode("decay", lambda _time, state: (-state[0],))
        whole = simulate_hybrid(
            {"decay": mode},
            initial_mode="decay",
            initial_state=(1.0,),
            t_bound=1.0,
            method="rk4",
            solver_options={"step": 0.01},
        )
        segmented = simulate_hybrid(
            {"decay": mode},
            initial_mode="decay",
            initial_state=(1.0,),
            t_bound=1.0,
            method="rk4",
            solver_options={"step": 0.01},
            segment_span=0.1,
        )
        self.assertAlmostEqual(whole.final_state[0], segmented.final_state[0], delta=1e-12)

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
        self.assertEqual([event.name for event in result.events], ["fall", "catch"])
        fall, catch = result.events
        self.assertEqual(fall.source_mode, "swinging")
        self.assertEqual(fall.target_mode, "falling")
        self.assertEqual(len(fall.state_before), 2)
        self.assertEqual(len(fall.state_after), 4)
        self.assertEqual(len(catch.state_before), 4)
        self.assertEqual(len(catch.state_after), 2)
        self.assertEqual(len(result.final_state), 2)


if __name__ == "__main__":
    unittest.main()
