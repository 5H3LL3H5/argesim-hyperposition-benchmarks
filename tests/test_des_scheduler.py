import itertools
import unittest

from nsa_devs import DesEvent, DesScheduler, HyperTime


class DesSchedulerTests(unittest.TestCase):
    def test_same_time_priorities_are_independent_of_enqueue_order(self) -> None:
        for order in itertools.permutations(("abort", "result", "audit")):
            for drain in (False, True):
                with self.subTest(order=order, drain=drain):
                    scheduler = DesScheduler()
                    trace = []
                    state = {"aborted": False, "accounted": 0, "accepted": False}

                    def abort(state=state, trace=trace) -> None:
                        state["aborted"] = True
                        trace.append("abort")

                    def result(state=state, trace=trace) -> None:
                        state["accounted"] += 1
                        state["accepted"] = not state["aborted"]
                        trace.append("result")

                    handlers = {
                        "abort": (-1, abort),
                        "result": (0, result),
                        "audit": (1, lambda trace=trace: trace.append("audit")),
                    }
                    for name in order:
                        priority, handler = handlers[name]
                        scheduler.schedule_at(
                            HyperTime.at(1, 2), name, handler, priority=priority
                        )
                    count = (
                        scheduler.run_until_idle(max_events=3)
                        if drain
                        else scheduler.run(1, max_events=3)
                    )
                    self.assertEqual(count, 3)
                    self.assertEqual(trace, ["abort", "result", "audit"])
                    self.assertEqual(
                        state, {"aborted": True, "accounted": 1, "accepted": False}
                    )
                    self.assertEqual(scheduler.time, HyperTime.at(1, 2))

    def test_relative_scheduling_preserves_time_and_passes_priority(self) -> None:
        for delay, target in ((0, HyperTime.at(2, 7)), (3, HyperTime.at(5))):
            with self.subTest(delay=delay):
                scheduler = DesScheduler(initial_time=HyperTime.at(2, 4))
                trace = []
                for name, priority in (("later", 4), ("earlier", -4)):
                    event = scheduler.schedule(
                        delay,
                        name,
                        trace.append,
                        name,
                        microsteps=3,
                        priority=priority,
                    )
                    self.assertEqual(event.time, target)
                    self.assertEqual(event.priority, priority)
                scheduler.run_until_idle()
                self.assertEqual(trace, ["earlier", "later"])

    def test_equal_priority_retains_fifo_order(self) -> None:
        for priority in (-2, 0, 2):
            with self.subTest(priority=priority):
                scheduler = DesScheduler()
                trace = []
                for name in ("z", "a", "m"):
                    scheduler.schedule_at(
                        HyperTime.at(1), name, trace.append, name, priority=priority
                    )
                scheduler.run_until_idle()
                self.assertEqual(trace, ["z", "a", "m"])

    def test_macro_and_micro_time_precede_priority(self) -> None:
        scheduler = DesScheduler()
        trace = []
        for name, time, priority in (
            ("next_macro", HyperTime.at(2), -100),
            ("next_micro", HyperTime.at(1, 2), -100),
            ("first", HyperTime.at(1, 1), 100),
        ):
            scheduler.schedule_at(time, name, trace.append, name, priority=priority)
        scheduler.run_until_idle()
        self.assertEqual(trace, ["first", "next_micro", "next_macro"])

    def test_nested_priority_only_orders_pending_events(self) -> None:
        scheduler = DesScheduler()
        trace = []

        def parent() -> None:
            trace.append("parent")
            scheduler.schedule_at(
                scheduler.time, "child", trace.append, "child", priority=-1
            )
            scheduler.schedule(
                0, "next_micro", trace.append, "next_micro", priority=-100
            )

        scheduler.schedule_at(HyperTime.at(1), "peer", trace.append, "peer", priority=1)
        scheduler.schedule_at(HyperTime.at(1), "parent", parent)
        scheduler.run_until_idle()
        self.assertEqual(trace, ["parent", "child", "peer", "next_micro"])

    def test_invalid_priority_does_not_mutate_queue(self) -> None:
        for priority in (True, False, 0.5, "1", None):
            for absolute in (False, True):
                with self.subTest(priority=priority, absolute=absolute):
                    scheduler = DesScheduler()
                    with self.assertRaisesRegex(
                        TypeError, "priority must be an integer"
                    ):
                        if absolute:
                            scheduler.schedule_at(
                                HyperTime.at(1),
                                "invalid",
                                lambda: None,
                                priority=priority,
                            )
                        else:
                            scheduler.schedule(
                                1, "invalid", lambda: None, priority=priority
                            )
                    self.assertEqual(scheduler.events, [])
                    self.assertEqual(scheduler.event_sequence, 0)
                    self.assertEqual(scheduler.time, HyperTime.at(0))

    def test_event_positional_constructor_remains_compatible(self) -> None:
        def handler(*args: object) -> None:
            pass

        event = DesEvent(HyperTime.at(1), 3, "legacy", handler, (42,), True)
        self.assertEqual(event.priority, 0)
        self.assertEqual(event.sequence, 3)
        self.assertEqual(event.args, (42,))
        self.assertTrue(event.cancelled)
        urgent = DesEvent(HyperTime.at(1), 4, "urgent", handler, priority=-1)
        self.assertLess(urgent, event)

    def test_cancelled_tail_does_not_exceed_idle_event_limit(self) -> None:
        scheduler = DesScheduler()
        trace = []
        scheduler.schedule(1, "kept", trace.append, "kept")
        for delay in (0, 1, 2):
            event = scheduler.schedule(delay, "cancelled", trace.append, "bad")
            scheduler.cancel(event)
        self.assertEqual(scheduler.run_until_idle(max_events=1), 1)
        self.assertEqual(trace, ["kept"])
        self.assertEqual(scheduler.events, [])
        self.assertEqual(scheduler.time, HyperTime.at(1))

    def test_handler_can_cancel_last_event_at_idle_event_limit(self) -> None:
        scheduler = DesScheduler()
        event = scheduler.schedule(2, "cancelled", self.fail, "cancelled handler ran")
        scheduler.schedule(1, "cancel", scheduler.cancel, event)
        self.assertEqual(scheduler.run_until_idle(max_events=1), 1)
        self.assertEqual(scheduler.events, [])
        self.assertEqual(scheduler.time, HyperTime.at(1))

    def test_idle_limit_preserves_unprocessed_live_event(self) -> None:
        scheduler = DesScheduler()
        trace = []
        scheduler.schedule(1, "first", trace.append, "first")
        cancelled = scheduler.schedule(2, "cancelled", trace.append, "bad")
        scheduler.cancel(cancelled)
        last = scheduler.schedule(3, "last", trace.append, "last")
        with self.assertRaisesRegex(RuntimeError, "exceeded max_events"):
            scheduler.run_until_idle(max_events=1)
        self.assertEqual(trace, ["first"])
        self.assertEqual(scheduler.time, HyperTime.at(1))
        self.assertIn(last, scheduler.events)
        self.assertEqual(scheduler.run_until_idle(max_events=1), 1)
        self.assertEqual(trace, ["first", "last"])

    def test_idle_limit_stops_zero_delay_cascade(self) -> None:
        scheduler = DesScheduler()

        def reschedule() -> None:
            scheduler.schedule(0, "again", reschedule)

        scheduler.schedule(0, "start", reschedule)
        with self.assertRaisesRegex(RuntimeError, "exceeded max_events"):
            scheduler.run_until_idle(max_events=5)
        self.assertEqual(scheduler.time, HyperTime.at(0, 5))
        self.assertEqual(len(scheduler.events), 1)


if __name__ == "__main__":
    unittest.main()
