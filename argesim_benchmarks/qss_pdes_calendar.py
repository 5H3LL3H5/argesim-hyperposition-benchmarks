"""Reference calendar for the book's QSS/PDES study (Python standard library).

Call step() on one coordinator. The partitions are calendar partitions, not
worker processes. Times are pairs (physical time, microstep). Node identifiers
are stable integers; dependants decide how to recompute their Taylor segments.
"""
from __future__ import annotations

import heapq
import math
from collections import defaultdict
from collections.abc import Callable, Iterable, Sequence
from fractions import Fraction

Stamp = tuple[float, int]
Item = tuple[Stamp, int, int]
Mail = tuple[int, object]
Output = Callable[[int, Stamp], Iterable[Mail]]
Transition = Callable[[int, Stamp, bool, tuple[Mail, ...]], Stamp | None]


class PartitionedCalendar:
    """Local versioned heaps, plus a directory of the live partition minima."""

    def __init__(self, owners: Sequence[int], partitions: int):
        if partitions < 1 or any(not 0 <= p < partitions for p in owners):
            raise ValueError("invalid partition assignment")
        self.owners = tuple(owners)
        self.now: Stamp | None = None
        self._versions = [0] * len(owners)
        self._local: list[list[Item]] = [[] for _ in range(partitions)]
        self._live: list[dict[int, Item]] = [{} for _ in range(partitions)]
        self._heads: dict[int, Stamp] = {}
        self._epochs = [0] * partitions
        self._directory: list[Item] = []

    def _owner(self, node: int) -> int:
        if not 0 <= node < len(self.owners):
            raise IndexError("unknown node")
        return self.owners[node]

    def _publish(self, p: int) -> None:
        heap, live = self._local[p], self._live[p]
        if len(heap) > 2 * len(live) + 8:
            heap[:] = live.values()
            heapq.heapify(heap)
        while heap and live.get(heap[0][1]) != heap[0]:
            heapq.heappop(heap)
        head = heap[0][0] if heap else None
        if self._heads.get(p) == head:
            return
        self._epochs[p] += 1
        if head is None:
            self._heads.pop(p, None)
        else:
            self._heads[p] = head
            heapq.heappush(self._directory, (head, p, self._epochs[p]))
        if len(self._directory) > 2 * len(self._heads) + 8:
            self._directory = [
                (stamp, lp, self._epochs[lp]) for lp, stamp in self._heads.items()
            ]
            heapq.heapify(self._directory)

    def schedule(self, updates: Iterable[tuple[int, Stamp | None]]) -> None:
        """Replace deadlines atomically; None cancels even an old finite date."""
        changes = list(updates)
        touched = set()
        for node, stamp in changes:
            touched.add(self._owner(node))
            if stamp is None:
                continue
            time, micro = stamp
            if not math.isfinite(time) or not isinstance(micro, int) or micro < 0:
                raise ValueError("use a finite physical time and a natural microstep")
            if self.now is not None and stamp <= self.now:
                raise ValueError("new deadline must follow the committed event bag")
        for node, stamp in changes:
            p = self.owners[node]
            self._versions[node] += 1
            if stamp is None:
                self._live[p].pop(node, None)
            else:
                entry = stamp, node, self._versions[node]
                self._live[p][node] = entry
                heapq.heappush(self._local[p], entry)
        for p in touched:
            self._publish(p)

    def peek(self) -> Stamp | None:
        while self._directory:
            stamp, p, epoch = self._directory[0]
            if self._epochs[p] == epoch:
                return stamp
            heapq.heappop(self._directory)
        return None

    def pop_bag(self) -> tuple[Stamp, tuple[int, ...]] | None:
        stamp = self.peek()
        if stamp is None:
            return None
        imminent = []
        while self.peek() == stamp:
            _, p, _ = heapq.heappop(self._directory)
            heap, live = self._local[p], self._live[p]
            while heap and heap[0][0] == stamp:
                entry = heapq.heappop(heap)
                node = entry[1]
                if live.get(node) == entry:
                    del live[node]
                    imminent.append(node)
            self._publish(p)
        self.now = stamp
        return stamp, tuple(sorted(imminent))

    def step(self, output: Output, transition: Transition) -> Stamp | None:
        """Route all pre-transition outputs first, then transition each receiver once.

        Callbacks operate on node-local state. output is pure and sends immutable
        payloads in deterministic order. transition reads its own prior state and
        the supplied bag only. External source knots can be scheduled as nodes.
        """
        event = self.pop_bag()
        if event is None:
            return None
        stamp, nodes = event
        internal = set(nodes)
        inbox: dict[int, list[Mail]] = defaultdict(list)
        for sender in nodes:
            for receiver, payload in output(sender, stamp):
                self._owner(receiver)
                inbox[receiver].append((sender, payload))
        updates = []
        for node in sorted(internal.union(inbox)):
            next_stamp = transition(
                node, stamp, node in internal, tuple(inbox.get(node, ()))
            )
            updates.append((node, next_stamp))
        self.schedule(updates)
        return stamp


def certified_interval(
    margin: Fraction, coefficients: Sequence[Fraction], horizon: Fraction,
    iterations: int = 64,
) -> Fraction:
    """Lower endpoint for sum(c[k-1]*h**k) <= margin on [0, horizon].

    Supply outward bounds as exact rationals, with factorials already included.
    horizon accounts for all other causes of outgoing messages. A zero reserve
    returns zero even when the polynomial vanishes (possible immediate event).
    """
    if not all(isinstance(x, (Fraction, int)) for x in (margin, horizon, *coefficients)):
        raise TypeError("supply integers or exact fractions")
    if not 1 <= len(coefficients) <= 3 or iterations < 1:
        raise ValueError("one to three terms and at least one bisection required")
    if margin < 0 or horizon < 0 or any(c < 0 for c in coefficients):
        raise ValueError("bounds must be nonnegative")

    def variation(h: Fraction) -> Fraction:
        value = Fraction(0)
        for c in reversed(coefficients):
            value = (value + c) * h
        return value

    lo, hi = Fraction(0), Fraction(horizon)
    if margin == 0:
        return lo
    end_variation = variation(hi)
    if end_variation <= margin:
        return hi
    # Nonnegative coefficients give E(sH) <= s*E(H) for 0 <= s <= 1.
    # This yields a positive certified start even far below the bisection scale.
    positive_lower_bound = hi * margin / end_variation
    for _ in range(iterations):
        mid = (lo + hi) / 2
        if variation(mid) <= margin:
            lo = mid
        else:
            hi = mid
    return max(lo, positive_lower_bound)
