"""Directed, dimensioned C20 layout transcribed from definition Figures 4–5.

Each track ends at the next decision point. Central failure clusters apply to
whole tracks, including curved tracks; processing-area tracks are not included
in the Figure-4 disruption draw. Arc lengths use the specified radii, not the
chord or a rectangular approximation.
"""

from __future__ import annotations

import heapq
import itertools
import math
from dataclasses import dataclass


@dataclass(frozen=True)
class C20Node:
    name: str
    kind: str = "junction"
    area: int | None = None
    slot: int | None = None
    level: int | None = None
    capacity: int = 1


@dataclass(frozen=True)
class C20Track:
    name: str
    source: str
    target: str
    length: float
    cluster: str | None = None
    default_only: bool = False

    @property
    def capacity(self) -> int:
        return math.floor(self.length)


class C20Layout:
    """Full central network and three ten-position processing areas.

    Workstation slots without an installed machine remain inaccessible to parts;
    their surrounding conveyors still exist. Each area's ten buffer columns
    contain three individual FIFO places. A part can bypass both the buffer
    columns and workstations along the definition's default-decision tracks.
    """

    def __init__(self) -> None:
        self.nodes: dict[str, C20Node] = {}
        self.tracks: dict[str, C20Track] = {}
        self.outgoing: dict[str, list[str]] = {}
        self._central()
        self._area_ports()
        for area in (1, 2, 3):
            self._processing_area(area)

    def node(self, name: str, **attributes: object) -> None:
        if name in self.nodes:
            raise ValueError(f"duplicate C20 decision point {name}")
        self.nodes[name] = C20Node(name, **attributes)
        self.outgoing[name] = []

    def track(
        self,
        source: str,
        target: str,
        length: float,
        cluster: str | None = None,
        *,
        default_only: bool = False,
    ) -> None:
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("track endpoints must be defined decision points")
        if not math.isfinite(length) or length < 1.0:
            raise ValueError("a C20 track must fit at least one 1 m part")
        name = f"{source}->{target}"
        if name in self.tracks:
            raise ValueError(f"duplicate C20 track {name}")
        self.tracks[name] = C20Track(
            name, source, target, length, cluster, default_only
        )
        self.outgoing[source].append(name)

    def _central(self) -> None:
        # Rows at y=0,8,12,20 m; roundabout centre columns x=0,69,138 m.
        # The area entry/exit junctions lie 4 m from adjacent roundabouts.
        for name in (
            "T0",
            "T1",
            "T2",
            "U0",
            "U1",
            "U2",
            "L0",
            "L1",
            "L2",
            "B0",
            "B1",
            "B2",
            "WT",
            "WB",
            "ET",
            "EB",
            "in0",
            "out0",
            "in3",
            "out3",
            "in1",
            "out1",
            "in2",
            "out2",
        ):
            self.node(name)
        for sequence in (
            ("T0", "in0", "out0", "T1", "in3", "out3", "T2"),
            ("B2", "in2", "out2", "B1", "in1", "out1", "B0"),
        ):
            for index, (source, target) in enumerate(itertools.pairwise(sequence)):
                self.track(
                    source,
                    target,
                    61.0 if index in (1, 4) else 4.0,
                    "A" if index in (1, 4) else "C",
                )
        quarter, half = 2 * math.pi, 4 * math.pi  # radius 4 m
        for source, target, length, cluster in (
            ("T0", "U0", half, "A"),
            ("U0", "WT", quarter, "A"),
            ("WT", "T0", quarter, "C"),
            ("T1", "U1", half, "A"),
            ("U1", "T1", half, "A"),
            ("T2", "ET", quarter, "C"),
            ("ET", "U2", quarter, "A"),
            ("U2", "T2", half, "A"),
            ("L0", "B0", half, "A"),
            ("B0", "WB", quarter, "C"),
            ("WB", "L0", quarter, "A"),
            ("L1", "B1", half, "A"),
            ("B1", "L1", half, "A"),
            ("L2", "EB", quarter, "A"),
            ("EB", "B2", quarter, "C"),
            ("B2", "L2", half, "A"),
            ("WB", "WT", 12.0, "B"),
            ("ET", "EB", 12.0, "B"),
            ("U2", "U1", 69.0, "B"),
            ("U1", "U0", 69.0, "B"),
            ("L0", "L1", 69.0, "B"),
            ("L1", "L2", 69.0, "B"),
            ("U0", "L0", 2 * math.pi, "B"),
            ("L2", "U2", 2 * math.pi, "B"),
        ):
            self.track(source, target, length, cluster)

    def _area_ports(self) -> None:
        for area in range(4):
            self.node(
                f"a{area}:in", kind="sink" if area == 0 else "junction", area=area
            )
            self.node(
                f"a{area}:out", kind="source" if area == 0 else "junction", area=area
            )
            # The radius-3 m quarter turns are external to the area boundary.
            self.track(f"in{area}", f"a{area}:in", 1.5 * math.pi)
            self.track(f"a{area}:out", f"out{area}", 1.5 * math.pi)

    def _processing_area(self, area: int) -> None:
        prefix = f"a{area}:"
        for name in ("left_low", "left_mid", "right_mid", "right_low"):
            self.node(prefix + name, area=area)
        for index in range(1, 11):
            for row in ("machine_in", "machine_out", "buffer_in", "buffer_out"):
                self.node(f"{prefix}{row}{index}", area=area)
            self.node(f"{prefix}ws{index}", kind="workstation", area=area, slot=index)
            for level in (1, 2, 3):
                self.node(
                    f"{prefix}buffer{index}.{level}",
                    kind="buffer",
                    area=area,
                    slot=index,
                    level=level,
                )

        def connect(
            source: str, target: str, length: float, *, default: bool = False
        ) -> None:
            self.track(prefix + source, prefix + target, length, default_only=default)

        quarter = 1.25 * math.pi  # all local turns have radius 2.5 m
        connect("in", "left_low", 2.5)
        connect("right_low", "out", 2.5)
        connect("left_low", "left_mid", 13.0)
        connect("right_mid", "right_low", 13.0)
        connect("left_low", "buffer_in1", quarter)
        connect("buffer_in10", "right_low", 5.0 + quarter, default=True)
        connect("right_mid", "buffer_out10", 5.0 + quarter)
        connect("buffer_out1", "left_mid", quarter)
        connect("left_mid", "machine_in1", 8.0 + quarter)
        connect("machine_in10", "right_mid", 13.0 + quarter, default=True)
        connect("left_mid", "machine_out1", 5.0 + quarter)
        connect("machine_out10", "right_mid", quarter)
        for index in range(1, 10):
            for row in ("machine_in", "machine_out", "buffer_in"):
                connect(f"{row}{index}", f"{row}{index + 1}", 5.0)
            connect(f"buffer_out{index + 1}", f"buffer_out{index}", 5.0)
        for index in range(1, 11):
            # A workstation occupies 3 m: 1.5 m either side of its centre.
            connect(f"machine_in{index}", f"ws{index}", quarter + 1.5)
            connect(f"ws{index}", f"machine_out{index}", quarter + 1.5)
            # Buffer centres are spaced 1 m inside a 3 m storage block.
            connect(f"buffer_in{index}", f"buffer{index}.3", quarter + 0.5)
            connect(f"buffer{index}.3", f"buffer{index}.2", 1.0)
            connect(f"buffer{index}.2", f"buffer{index}.1", 1.0)
            connect(f"buffer{index}.1", f"buffer_out{index}", quarter + 0.5)

    def shortest_path(
        self,
        source: str,
        target: str,
        *,
        forbidden: frozenset[str] = frozenset(),
    ) -> tuple[str, ...]:
        """Shortest directed route; storage and workstations are not shortcuts."""
        if source not in self.nodes or target not in self.nodes:
            raise ValueError("unknown C20 route endpoint")
        queue = [(0.0, (), source)]
        settled: set[str] = set()
        while queue:
            distance, path, node = heapq.heappop(queue)
            if node in settled:
                continue
            if node == target:
                return path
            settled.add(node)
            for name in self.outgoing[node]:
                track = self.tracks[name]
                destination = self.nodes[track.target]
                if name in forbidden:
                    continue
                if (
                    destination.kind in {"source", "sink", "workstation"}
                    and destination.name != target
                ):
                    continue
                if destination.kind == "buffer" and destination.name != target:
                    # Only traverse intervening slots of the selected column,
                    # or leave a column from a stored source part.
                    selected = self.nodes[target]
                    origin = self.nodes[source]
                    entering = selected.kind == "buffer" and (
                        destination.area,
                        destination.slot,
                    ) == (selected.area, selected.slot)
                    leaving = origin.kind == "buffer" and (
                        destination.area,
                        destination.slot,
                    ) == (origin.area, origin.slot)
                    if not (entering or leaving):
                        continue
                heapq.heappush(
                    queue, (distance + track.length, (*path, name), track.target)
                )
        raise ValueError(f"no directed C20 route from {source} to {target}")
