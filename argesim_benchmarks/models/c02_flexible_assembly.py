"""ARGESIM C02: Flexible Assembly System.

This model is a Discrete Event Simulation (DES).
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from enum import Enum, auto

from nsa_devs.hypertime import HyperTime


@dataclass(frozen=True)
class C02Constants:
    """System-wide configuration parameters for C02."""
    speed_m_min: float = 18.0
    speed_m_s: float = 18.0 / 60.0
    pallet_length: float = 0.36
    shift_time: float = 2.0
    space_between_subsystems: float = 0.4
    warmup_minutes: int = 120
    end_minutes: int = 600

@dataclass
class Pallet:
    """A single pallet in the assembly system."""
    id: int
    arrival_time: HyperTime | None = None
    operations_done: set[str] = field(default_factory=set)
    in_system: bool = False

    def reset(self, time: HyperTime):
        self.arrival_time = time
        self.operations_done = set()
        self.in_system = True

@dataclass(frozen=True)
class StationConfig:
    name: str
    op_time: float
    length_b1: float
    length_buffer: float
    buffer_capacity: int

    @classmethod
    def create(cls, name: str, op_time: float, length_b1: float, length_buffer: float, pallet_length: float = 0.36):
        return cls(
            name=name,
            op_time=op_time,
            length_b1=length_b1,
            length_buffer=length_buffer,
            buffer_capacity=int(length_buffer // pallet_length)
        )

class EventType(Enum):
    ARRIVAL_B1 = auto()
    ENTER_STATION = auto()
    LEAVE_STATION = auto()
    SHIFT_TO_B2 = auto()
    SHIFT_TO_B1 = auto()

@dataclass(order=True)
class Event:
    time: HyperTime
    sequence: int
    type: EventType = field(compare=False)
    pallet: Pallet = field(compare=False)
    station_idx: int = field(compare=False)

class Simulator:
    def __init__(self, num_pallets: int, constants: C02Constants = C02Constants()):
        self.constants = constants
        self.pallets = [Pallet(id=i) for i in range(num_pallets)]
        self.queue: list[Event] = []
        self.sequence = 0
        self.time = HyperTime.at(0)

        # Subsystems configuration
        self.stations = [
            StationConfig.create("A1", 15.0, 2.0, 1.2, constants.pallet_length),
            StationConfig.create("A2_1", 60.0, 1.6, 0.8, constants.pallet_length),
            StationConfig.create("A2_2", 60.0, 1.6, 0.8, constants.pallet_length),
            StationConfig.create("A2_3", 60.0, 1.6, 0.8, constants.pallet_length),
            StationConfig.create("A3", 20.0, 1.6, 0.8, constants.pallet_length),
            StationConfig.create("A4", 20.0, 1.6, 0.8, constants.pallet_length),
            StationConfig.create("A5", 20.0, 1.6, 0.8, constants.pallet_length),
            StationConfig.create("A6", 30.0, 2.0, 1.2, constants.pallet_length),
        ]

        # Distances to the next subsystem. A2_3 to A3 is 0.0, A6 to A1 is 0.0, rest are 0.4.
        self.distances = [0.4, 0.4, 0.4, 0.0, 0.4, 0.4, 0.4, 0.0]

        self.buffer_occupancy = [0] * 8
        self.station_busy = [False] * 8
        self.station_wait_lists: list[list[tuple[HyperTime, Pallet]]] = [[] for _ in range(8)]

        self.throughput = 0
        self.total_throughput_time = 0.0

    def schedule(self, time: HyperTime, event_type: EventType, pallet: Pallet, station_idx: int):
        heapq.heappush(self.queue, Event(time, self.sequence, event_type, pallet, station_idx))
        self.sequence += 1

    def run(self):
        # 5. In the beginning empty pallets are circulating in the system.
        # Their positions on the conveyors B1 (not B2!) can be chosen randomly.
        # To avoid randomness causing nondeterminism in tests and per methodology,
        # we evenly space them along the total loop length of B1.

        # Calculate total belt length
        total_b1_length = sum(s.length_b1 for s in self.stations) + sum(self.distances)
        spacing = total_b1_length / len(self.pallets)

        for i, pallet in enumerate(self.pallets):
            pos = i * spacing
            # Find which station and where it is
            current_dist = 0.0
            for s_idx, station in enumerate(self.stations):
                segment_len = station.length_b1 + self.distances[s_idx]
                if current_dist + segment_len >= pos or s_idx == len(self.stations) - 1:
                    dist_to_end_of_segment = current_dist + segment_len - pos
                    travel_time = dist_to_end_of_segment / self.constants.speed_m_s
                    self.schedule(HyperTime.at(travel_time), EventType.ARRIVAL_B1, pallet, (s_idx + 1) % 8)
                    break
                current_dist += segment_len

        while self.queue:
            event = heapq.heappop(self.queue)
            self.time = event.time

            # Stop condition
            if self.time.macro >= self.constants.end_minutes * 60:
                break

            self.process_event(event)

    def process_event(self, event: Event):
        pallet = event.pallet
        s_idx = event.station_idx
        station = self.stations[s_idx]
        t = self.time

        if event.type == EventType.ARRIVAL_B1:
            # Pallet arrives at start of subsystem s_idx (at Sx)
            # Decide if it needs processing here
            needs_processing = False

            if s_idx == 0: # A1
                # 5. Unprocessed pieces are put on in A1, finished parts unloaded in A1. A1 only used for this.
                needs_processing = True
            elif s_idx in (1, 2, 3): # A2
                if "A2" not in pallet.operations_done:
                    needs_processing = True
            elif s_idx == 4: # A3
                if "A3" not in pallet.operations_done:
                    needs_processing = True
            elif s_idx == 5: # A4
                if "A4" not in pallet.operations_done:
                    needs_processing = True
            elif s_idx == 6: # A5
                if "A5" not in pallet.operations_done:
                    needs_processing = True
            elif s_idx == 7: # A6
                # 6. Pallets are brought to A6 if they have not undergone one or more of A3, A4, A5.
                if not {"A3", "A4", "A5"}.issubset(pallet.operations_done):
                    needs_processing = True

            can_shift = needs_processing and self.buffer_occupancy[s_idx] < station.buffer_capacity

            if can_shift:
                # Reserve the spot immediately to avoid race conditions with pallets arriving right behind
                self.buffer_occupancy[s_idx] += 1
                # Shift to B2 (takes 2 sec)
                self.schedule(t.after_finite(self.constants.shift_time), EventType.SHIFT_TO_B2, pallet, s_idx)
            else:
                # Move along B1 to next station
                travel_time = station.length_b1 / self.constants.speed_m_s
                # Add gap distance
                travel_time += self.distances[s_idx] / self.constants.speed_m_s
                if travel_time > 0:
                    self.schedule(t.after_finite(travel_time), EventType.ARRIVAL_B1, pallet, (s_idx + 1) % 8)
                else:
                    self.schedule(t.after_epsilon(1), EventType.ARRIVAL_B1, pallet, (s_idx + 1) % 8)

        elif event.type == EventType.SHIFT_TO_B2:
            # Wait list logic
            self.station_wait_lists[s_idx].append((t, pallet))

            if not self.station_busy[s_idx] and len(self.station_wait_lists[s_idx]) == 1:
                travel_time = station.length_buffer / self.constants.speed_m_s
                self.schedule(t.after_finite(travel_time), EventType.ENTER_STATION, pallet, s_idx)

        elif event.type == EventType.ENTER_STATION:
            # We pop ourselves
            self.station_wait_lists[s_idx].pop(0)
            self.station_busy[s_idx] = True
            self.buffer_occupancy[s_idx] -= 1
            self.schedule(t.after_finite(station.op_time), EventType.LEAVE_STATION, pallet, s_idx)

        elif event.type == EventType.LEAVE_STATION:
            self.station_busy[s_idx] = False

            # Update operations done
            if s_idx == 0:
                if pallet.in_system:
                    # Output
                    if t.macro >= self.constants.warmup_minutes * 60:
                        self.throughput += 1
                        self.total_throughput_time += float(t.macro - pallet.arrival_time.macro)
                pallet.reset(t)
            elif s_idx in (1, 2, 3):
                pallet.operations_done.add("A2")
            elif s_idx == 4:
                pallet.operations_done.add("A3")
            elif s_idx == 5:
                pallet.operations_done.add("A4")
            elif s_idx == 6:
                pallet.operations_done.add("A5")
            elif s_idx == 7:
                # A6 substitute - does missing operations
                missing = {"A3", "A4", "A5"} - pallet.operations_done
                pallet.operations_done.update(missing)
                # Text says: "They can then undergo all the missing operations at a time."
                # Does this mean operation time is 30s total or 30s per missing?
                # Table says operation time 30s. We use 30s total since it's one station.

            # If someone is waiting in the queue for this station, trigger their entry
            if self.station_wait_lists[s_idx]:
                # Next one travels from wherever it is.
                # Simplification: buffer is constantly moving, so next is ready immediately if it has been waiting long enough.
                # Actually, the buffer conveys parts at constant speed.
                # If they queued up, the next one is 0.36m behind the station.
                # So travel time is 0.36m / speed.
                next_t, next_pallet = self.station_wait_lists[s_idx][0]
                travel_delay = self.constants.pallet_length / self.constants.speed_m_s

                # However, if they just entered the buffer, they need to travel the full distance.
                # Take max of (now + travel_delay) and (time_entered + full_buffer_travel_time)
                full_travel = station.length_buffer / self.constants.speed_m_s
                earliest_arrival = next_t.after_finite(full_travel)

                start_time = max(t.after_finite(travel_delay), earliest_arrival)
                self.schedule(start_time, EventType.ENTER_STATION, next_pallet, s_idx)

            # Shift back to B1 in Sy (takes 2 sec)
            self.schedule(t.after_finite(self.constants.shift_time), EventType.SHIFT_TO_B1, pallet, s_idx)

        elif event.type == EventType.SHIFT_TO_B1:
            # Shifted back to B1, has priority over those coming from left.
            # Just move to next station.
            travel_time = self.distances[s_idx] / self.constants.speed_m_s
            if travel_time > 0:
                self.schedule(t.after_finite(travel_time), EventType.ARRIVAL_B1, pallet, (s_idx + 1) % 8)
            else:
                self.schedule(t.after_epsilon(1), EventType.ARRIVAL_B1, pallet, (s_idx + 1) % 8)


def solve_c02(num_pallets: int) -> dict[str, float]:
    """Solve ARGESIM C02 for the specified number of pallets."""
    sim = Simulator(num_pallets)
    sim.run()

    avg_throughput_time = (
        sim.total_throughput_time / sim.throughput if sim.throughput > 0 else 0.0
    )

    return {
        "throughput": float(sim.throughput),
        "average_throughput_time": avg_throughput_time
    }
