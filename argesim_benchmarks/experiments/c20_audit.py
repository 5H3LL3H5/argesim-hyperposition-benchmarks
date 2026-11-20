"""Independent replay checks for C20 results and transport event traces.

These checks do not call the simulator's dispatch, routing or conservation
code. They verify the supplied graph, not its transcription from the drawings,
and are not a replacement for an external model or measured reference data.
"""

from __future__ import annotations

import math
import statistics
from collections import defaultdict, deque
from collections.abc import Sequence
from itertools import pairwise

from ..models.c20_complex_production import C20ReplicationResult, Order
from ..models.c20_flow import C20FlowTrip
from ..models.c20_layout import C20Layout

_EPS = 1e-7
_WEIGHTS = {"A": 0.40, "B": 0.90, "C": 1.42, "D": 1.42, "E": 2.21}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(f"C20 audit: {message}")


def _equal(actual: float, expected: float, message: str) -> None:
    _require(
        math.isfinite(actual)
        and math.isclose(actual, expected, rel_tol=1e-12, abs_tol=_EPS),
        message,
    )


def audit_result(result: C20ReplicationResult, orders: Sequence[Order]) -> None:
    """Recompute task A--D metrics from a complete, unchanged input book."""
    expected = {order.identifier: order for order in orders}
    _require(bool(expected) and len(expected) == len(orders), "invalid input book")
    _require(
        len(result.orders) == len(expected)
        and {row.identifier for row in result.orders} == set(expected),
        "missing, duplicate or unexpected completed order",
    )
    for row in result.orders:
        order = expected[row.identifier]
        _require(row.product_type == order.product_type, "product changed")
        _equal(row.release_date, order.earliest_release_date, "release changed")
        _equal(row.due_date, order.due_date, "due date changed")
        _require(
            math.isfinite(row.completion_date)
            and row.completion_date >= row.release_date,
            "completion precedes release or is not finite",
        )
        _equal(
            row.throughput_time,
            row.completion_date - row.release_date,
            "incorrect throughput time",
        )
        tardiness = max(0.0, row.completion_date - row.due_date)
        _equal(row.tardiness, tardiness, "incorrect tardiness")
        _equal(
            row.weighted_tardiness,
            _WEIGHTS[row.product_type] * tardiness,
            "incorrect weighted tardiness",
        )
        for count in (
            row.max_nok_violations,
            row.max_ok_violations,
            row.disruption_nok,
        ):
            _require(type(count) is int and count >= 0, "invalid violation count")
    rows = result.orders
    metrics = {
        "makespan": max(row.completion_date for row in rows)
        - min(order.earliest_release_date for order in orders),
        "median_throughput_time": statistics.median(
            row.throughput_time for row in rows
        ),
        "tardy_orders": sum(row.tardiness > 0 for row in rows),
        "weighted_tardiness": math.fsum(row.weighted_tardiness for row in rows),
        "total_tardiness": math.fsum(row.tardiness for row in rows),
        "max_nok_parts": sum(row.max_nok_violations for row in rows),
        "max_ok_parts": sum(row.max_ok_violations for row in rows),
        "completed_orders": len(rows),
    }
    for field, expected_value in metrics.items():
        _equal(getattr(result, field), expected_value, f"incorrect {field}")


def audit_flow(
    layout: C20Layout,
    trace: Sequence[tuple[float, str, int, str, int]],
    failures: Sequence[tuple[str, float, float]],
    trips: Sequence[C20FlowTrip],
) -> dict[str, int]:
    """Replay every owner, FIFO, headway, capacity and travel-time constraint.

    Requires a complete production trace, including insert/remove events.
    Junctions are single-place resources with one-second clearance. Conveyor
    motion is 1 m/s, part length 1 m, and failures pause motion. Simultaneous
    failure boundaries are excluded from the interval test because their
    ordering is represented by the simulator's event calendar, not this log.
    """
    _require(bool(trace), "empty transport trace")
    queues: dict[str, deque[tuple[int, float]]] = defaultdict(deque)
    nodes: dict[str, int] = {}
    locations: dict[int, tuple[str, str]] = {}
    node_free: dict[str, float] = defaultdict(float)
    last_entry: dict[str, float] = defaultdict(lambda: -math.inf)
    last_exit: dict[str, float] = defaultdict(lambda: -math.inf)
    visited: dict[int, list[str]] = defaultdict(list)
    breakdowns: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for name, start, finish in failures:
        _require(name in layout.tracks, "failure on unknown track")
        _require(
            math.isfinite(start) and math.isfinite(finish) and 0 <= start < finish,
            "invalid failure interval",
        )
        breakdowns[name].append((start, finish))
    for intervals in breakdowns.values():
        intervals.sort()
        _require(
            all(a[1] <= b[0] for a, b in pairwise(intervals)),
            "overlapping failures on one track",
        )
    previous = -math.inf
    inserted = removed = movements = 0
    for when, kind, identifier, name, occupancy in trace:
        _require(math.isfinite(when) and when >= previous, "backdated trace event")
        previous = when
        if kind == "insert":
            _require(name in layout.nodes, "insertion at unknown node")
            _require(
                identifier not in locations and name not in nodes, "duplicate insertion"
            )
            _require(when + _EPS >= node_free[name], "insertion headway")
            locations[identifier] = ("node", name)
            nodes[name] = identifier
            _require(occupancy == 1, "insertion occupancy")
            inserted += 1
        elif kind == "remove":
            _require(locations.get(identifier) == ("node", name), "invalid removal")
            del locations[identifier]
            del nodes[name]
            node_free[name] = when + 1.0
            _require(occupancy == 0, "removal occupancy")
            removed += 1
        else:
            _require(
                kind in {"enter", "exit"} and name in layout.tracks, "unknown movement"
            )
            track = layout.tracks[name]
            queue = queues[name]
            _require(
                not any(
                    start + _EPS < when < finish - _EPS
                    for start, finish in breakdowns[name]
                ),
                "movement on failed conveyor",
            )
            if kind == "enter":
                _require(
                    locations.get(identifier) == ("node", track.source),
                    "discontinuous route or duplicate track admission",
                )
                _require(
                    when - last_entry[name] >= 1.0 - _EPS, "conveyor entry headway"
                )
                del nodes[track.source]
                node_free[track.source] = when + 1.0
                locations[identifier] = ("track", name)
                queue.append((identifier, when))
                last_entry[name] = when
                _require(len(queue) <= math.floor(track.length), "conveyor capacity")
            else:
                _require(
                    bool(queue) and queue[0][0] == identifier,
                    "conveyor FIFO or ownership",
                )
                _require(track.target not in nodes, "occupied destination node")
                _require(when + _EPS >= node_free[track.target], "junction headway")
                _require(when - last_exit[name] >= 1.0 - _EPS, "conveyor exit headway")
                _, entered = queue.popleft()
                pause = math.fsum(
                    max(0.0, min(when, finish) - max(entered, start))
                    for start, finish in breakdowns[name]
                )
                _require(
                    when - entered - pause + _EPS >= track.length, "conveyor speed"
                )
                locations[identifier] = ("node", track.target)
                nodes[track.target] = identifier
                last_exit[name] = when
                visited[identifier].append(name)
            _require(occupancy == len(queue), "reported conveyor occupancy")
            movements += 1
    _require(not locations and inserted == removed, "parts left at termination")
    described: dict[int, list[str]] = defaultdict(list)
    for trip in trips:
        node, distance = trip.source, 0.0
        for name in trip.tracks:
            _require(name in layout.tracks, "trip uses unknown track")
            track = layout.tracks[name]
            _require(track.source == node, "discontinuous reported trip")
            node, distance = track.target, distance + track.length
        _require(node == trip.target, "wrong trip destination")
        _equal(trip.distance, distance, "incorrect reported trip distance")
        _require(
            math.isfinite(trip.requested)
            and math.isfinite(trip.arrived)
            and trip.arrived - trip.requested + _EPS >= distance,
            "reported trip exceeds belt speed",
        )
        described[trip.part].extend(trip.tracks)
    _require(
        dict(described) == dict(visited), "trip paths disagree with transport trace"
    )
    return {
        "events": len(trace),
        "movements": movements,
        "insertions": inserted,
        "removals": removed,
        "trips": len(trips),
    }
