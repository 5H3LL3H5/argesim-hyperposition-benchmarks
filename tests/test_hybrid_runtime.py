import unittest

from argesim_benchmarks.hybrid import (
    HybridMode,
    HybridReset,
    StateEvent,
    simulate_hybrid,
)
from argesim_benchmarks.models.c21_state_events import (
    simulate_c21_bouncing_ball_event_contact,
    simulate_c21_rotating_pendulum,
)


class HybridRuntimeTests(unittest.TestCase):
    def test_switch_precedes_the_old_modes_finite_time_singularity(self):
        switch = StateEvent(
            "limit", lambda _time, state: state[0] - 2.0,
            lambda _time, _state: (2.0,), "hold", direction=1,
        )
        result = simulate_hybrid(
            {
                "grow": HybridMode("grow", lambda _time, state: (state[0] ** 2,), (switch,)),
                "hold": HybridMode("hold", lambda _time, _state: (0.0,)),
            },
            initial_mode="grow", initial_state=(1.0,), t_bound=2.0,
            solver_options={"rtol": 1e-9, "atol": 1e-11},
        )
        self.assertEqual([event.name for event in result.events], ["limit"])
        self.assertAlmostEqual(float(result.events[0].time.macro), 0.5, delta=1e-7)
        self.assertEqual(result.final_time, 2.0)
        self.assertEqual(result.final_state, (2.0,))

    def test_terminal_guard_is_seen_before_spending_the_remaining_step_budget(self):
        event = StateEvent(
            "stop", lambda _time, state: state[0] - 0.99,
            lambda _time, state: HybridReset(state, terminate=True),
            "decay", direction=-1,
        )
        modes = {"decay": HybridMode("decay", lambda _time, state: (-state[0],), (event,))}
        for method, options in (
            ("euler", {"step": 0.1, "max_steps": 1}),
            ("rk4", {"step": 0.1, "max_steps": 1}),
            ("rk45", {"initial_step": 0.1, "max_steps": 1}),
            ("qss1", {"quantum": 0.1, "max_events": 1}),
            ("cqss1", {"quantum": 0.3, "max_events": 1}),
            ("qss2", {"quantum": 0.1, "max_events": 1}),
            ("qss3", {"quantum": 0.1, "max_events": 1}),
            ("liqss2", {"quantum": 0.1, "max_events": 1}),
            ("eliqss2", {"quantum": 0.1, "max_events": 1}),
            ("liqss-bdf", {"quantum": 0.1, "max_steps": 1,
                           "initial_step": 0.05, "rtol": 0.01}),
        ):
            with self.subTest(method=method):
                result = simulate_hybrid(
                    modes, initial_mode="decay", initial_state=(1.0,), t_bound=2.0,
                    method=method, solver_options=options,
                )
                self.assertEqual([hit.name for hit in result.events], ["stop"])
                self.assertLess(result.final_time, 0.1)
                self.assertAlmostEqual(result.final_state[0], 0.99, delta=1e-8)

    def test_guard_can_trigger_at_the_last_sample(self):
        event = StateEvent(
            "end", lambda time, _state: time - 0.1,
            lambda _time, _state: (2.0,), "fixed", direction=1,
        )
        modes = {"fixed": HybridMode("fixed", lambda _time, _state: (0.0,), (event,))}
        for method, options in (
            ("rk4", {"step": 0.1}),
            ("qss1", {"quantum": 0.1}),
            ("qss2", {"quantum": 0.1}),
        ):
            with self.subTest(method=method):
                result = simulate_hybrid(
                    modes, initial_mode="fixed", initial_state=(1.0,), t_bound=0.1,
                    method=method, solver_options=options,
                )
                self.assertEqual([hit.name for hit in result.events], ["end"])
                self.assertEqual(result.final_time, 0.1)
                self.assertEqual(result.final_state, (2.0,))

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
