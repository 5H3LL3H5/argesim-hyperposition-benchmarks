"""Independent scan oracle and causal counterexamples for the PDES study."""
import math
import random
import unittest
from fractions import Fraction

from argesim_benchmarks.qss_pdes_calendar import PartitionedCalendar, certified_interval


class PartitionedCalendarTests(unittest.TestCase):
    def test_matches_scan_with_ties_cancellations_and_replacement(self):
        for parts in (1, 4, 8):
            with self.subTest(parts=parts):
                rnd = random.Random(817)
                calendar = PartitionedCalendar([i % parts for i in range(113)], parts)
                pending = {}
                time = 0.0
                for _ in range(125):
                    updates = []
                    for _ in range(60):
                        node = rnd.randrange(113)
                        stamp = None if rnd.randrange(6) == 0 else (
                            time + rnd.randrange(1, 11), rnd.randrange(2)
                        )
                        updates.append((node, stamp))
                        if stamp is None:
                            pending.pop(node, None)
                        else:
                            pending[node] = stamp
                    calendar.schedule(updates)
                    expected = min(pending.values())
                    nodes = tuple(sorted(i for i, t in pending.items() if t == expected))
                    self.assertEqual(calendar.peek(), expected)
                    self.assertEqual(calendar.pop_bag(), (expected, nodes))
                    for node in nodes:
                        del pending[node]
                    time = expected[0]
                while pending:
                    stamp = min(pending.values())
                    nodes = tuple(sorted(i for i, t in pending.items() if t == stamp))
                    self.assertEqual(calendar.pop_bag(), (stamp, nodes))
                    for node in nodes:
                        del pending[node]
                self.assertIsNone(calendar.pop_bag())

    def test_confluence_snapshot_and_future_microstep(self):
        for owners in ([0, 0, 0], [2, 0, 1]):
            states = [11, 17, 23]
            calls = []
            calendar = PartitionedCalendar(owners, max(owners) + 1)
            calendar.schedule([(0, (2.0, 0)), (1, (2.0, 0)), (2, (9.0, 0))])

            def output(node, stamp):
                return [(1 - node, states[node]), (2, states[node])]

            def transition(node, stamp, internal, bag):
                calls.append((node, internal, bag))
                states[node] = -1
                return (stamp[0], 1) if node == 2 else None

            self.assertEqual(calendar.step(output, transition), (2.0, 0))
            self.assertEqual(calls, [
                (0, True, ((1, 17),)), (1, True, ((0, 11),)),
                (2, False, ((0, 11), (1, 17))),
            ])
            self.assertEqual(calendar.pop_bag(), ((2.0, 1), (2,)))
            self.assertIsNone(calendar.peek())

    def test_book_sized_partitions_equal_the_same_serial_bags(self):
        # Manufactured event times only. Keep both string states on their node.
        for columns, scalars in ((65, 33), (799, 2)):
            size = columns * scalars
            inputs = [(i, (float((i * 11) % 37), 0)) for i in range(size)]
            expected = [
                ((float(t), 0), tuple(i for i in range(size) if (i * 11) % 37 == t))
                for t in range(37)
            ]
            for parts in (1, 4, 8):
                with self.subTest(columns=columns, partitions=parts):
                    widths = [columns // parts + (p < columns % parts) for p in range(parts)]
                    owners = [p for p, w in enumerate(widths) for _ in range(w * scalars)]
                    c = PartitionedCalendar(owners, parts)
                    c.schedule(inputs)
                    self.assertEqual([c.pop_bag() for _ in expected], expected)
                    self.assertIsNone(c.peek())

    def test_cancellation_and_close_distinct_times(self):
        c = PartitionedCalendar([0, 1], 2)
        adjacent = math.nextafter(1.0, math.inf)
        c.schedule([(0, (1.0, 0)), (1, (adjacent, 0))])
        self.assertEqual(c.pop_bag(), ((1.0, 0), (0,)))
        c.schedule([(0, (1.0, 1))])
        self.assertEqual(c.pop_bag(), ((1.0, 1), (0,)))
        with self.assertRaises(ValueError):
            c.schedule([(1, None), (0, (1.0, 0))])
        self.assertEqual(c.peek(), (adjacent, 0))
        c.schedule([(1, None)])
        self.assertIsNone(c.peek())

    def test_many_obsolete_slots_do_not_revive(self):
        c = PartitionedCalendar([0, 1], 2)
        c.schedule([(0, (1.0, 0))])
        for i in range(250):
            c.schedule([(1, (10.0 + i, 0))])
        c.schedule([(0, None)])
        self.assertEqual(c.pop_bag(), ((259.0, 0), (1,)))
        self.assertIsNone(c.peek())


class LookaheadTests(unittest.TestCase):
    def test_first_three_orders_and_a_nonzero_initial_mismatch(self):
        for power in (1, 2, 3):
            with self.subTest(power=power):
                coeff = [0] * (power - 1) + [Fraction(1, math.factorial(power))]
                margin = Fraction(1, 8)
                h = certified_interval(margin, coeff, 4)
                self.assertLessEqual(coeff[-1] * h**power, margin)
                self.assertGreater(coeff[-1] * (h + Fraction(4, 2**64))**power, margin)
        self.assertEqual(certified_interval(3, (1, 2, 0), 2), 1)
        self.assertEqual(certified_interval(0, (0, 0, 0), 2), 0)
        self.assertEqual(certified_interval(5, (0,), 3), 3)
        with self.assertRaises(TypeError):
            certified_interval(1, (0.1,), 3)

    def test_changed_input_preempts_root_for_all_three_orders(self):
        # Under the old continuation d(s)=s**p would first reach 1 at s=1.
        # Starting at s=1/8 add 512*(s-1/8)**p. The added term is C^(p-1).
        eps, t = Fraction(1, 8), Fraction(1, 4)
        for p in (1, 2, 3):
            with self.subTest(order=p):
                self.assertLess(eps**p, 1)
                self.assertGreater(t**p + 512 * (t - eps)**p, 1)
                self.assertLess(t, 1)

    def test_band_smallness_does_not_preserve_a_threshold_output(self):
        quantum, eps = Fraction(1), Fraction(1, 100)
        slope, delay = Fraction(1, 5), Fraction(1, 10)
        old = quantum - eps
        new = old + slope * delay
        self.assertLess(new - old, quantum)
        self.assertLess(old, quantum)
        self.assertGreater(new, quantum)
