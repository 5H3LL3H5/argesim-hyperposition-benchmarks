"""ARGESIM C02: Flexible Assembly System.

The public solver uses the finite conveyor plant. The earlier DEVS delay blocks
and solve_c02_legacy remain available to reproduce historical results.
"""

from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

from nsa_devs.hypertime import HyperTime


@dataclass(frozen=True)
class C02Constants:
    """System-wide configuration parameters for C02."""

    speed_m_min: float = 18.0
    speed_m_s: float = 18.0 / 60.0
    pallet_length: float = 0.36
    shift_time: float = 2.0
    shifter_width: float = 0.4
    positioning_unit_length: float = 0.4
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
    fallback_to_a6: bool = False

    def reset(self, time: HyperTime):
        self.arrival_time = time
        self.operations_done = set()
        self.in_system = True
        self.fallback_to_a6 = False


@dataclass(frozen=True)
class StationConfig:
    name: str
    op_time: float
    length_b1: float
    length_buffer: float
    buffer_capacity: int
    shift_time: float

    def b1_transport_length(self, constants: C02Constants) -> float:
        """Through lane plus the two 0.4 m shifter sections (clarification 1)."""
        return self.length_b1 + 2 * constants.shifter_width

    @classmethod
    def create(
        cls,
        name: str,
        op_time: float,
        length_b1: float,
        length_buffer: float,
        pallet_length: float = 0.36,
        shift_time: float = 2.0,
    ):
        return cls(
            name=name,
            op_time=op_time,
            length_b1=length_b1,
            length_buffer=length_buffer,
            # The B2 lane stores pallets on the buffer plus one at the station.
            buffer_capacity=int(length_buffer // pallet_length) + 1,
            shift_time=shift_time,
        )


# --- Formal DEVS Framework ---


class Message:
    def __init__(self, port: str, value: object):
        self.port = port
        self.value = value


class AtomicModel:
    def __init__(self, name: str):
        self.name = name
        self.sigma: float = math.inf
        self.phase: str = "passive"

    def init_state(self):
        """Initialize model state."""

    def ta(self) -> float:
        """Time advance function."""
        return self.sigma

    def dint(self):
        """Internal transition function."""

    def dext(self, e: float, message: Message):
        """External transition function."""

    def out(self) -> Message | None:
        """Output function."""
        return None


@dataclass(order=True)
class DEVS_Event:
    time: HyperTime
    sequence: int
    type: str = field(compare=False)
    model: AtomicModel = field(compare=False)
    message: Message | None = field(compare=False, default=None)


class Coordinator:
    def __init__(self, end_minutes: int):
        self.end_minutes = end_minutes
        self.time = HyperTime.at(0)
        self.models: list[AtomicModel] = []
        self.couplings: dict[
            tuple[AtomicModel, str], list[tuple[AtomicModel, str]]
        ] = {}
        self.model_next_event: dict[AtomicModel, HyperTime] = {}
        self.model_last_event: dict[AtomicModel, HyperTime] = {}
        self.throughput = 0
        self.total_throughput_time = 0.0
        self.external_events: list[DEVS_Event] = []
        self._sequence = 0

    def add_model(self, model: AtomicModel):
        self.models.append(model)
        self.model_last_event[model] = self.time
        model.init_state()

    def add_coupling(
        self, source: AtomicModel, src_port: str, dest: AtomicModel, dst_port: str
    ):
        key = (source, src_port)
        if key not in self.couplings:
            self.couplings[key] = []
        self.couplings[key].append((dest, dst_port))

    def schedule(self, model: AtomicModel, current_time: HyperTime):
        ta = model.ta()
        if ta < math.inf:
            if ta > 0:
                next_time = current_time.after_finite(ta)
            else:
                next_time = current_time.after_epsilon(1)
            self.model_next_event[model] = next_time
        else:
            self.model_next_event[model] = None

    def get_next_internal_model(self) -> tuple[HyperTime, AtomicModel] | None:
        min_time = None
        min_model = None
        for model, t in self.model_next_event.items():
            if t is not None and (min_time is None or t < min_time):
                min_time = t
                min_model = model
        if min_time is None:
            return None
        return min_time, min_model

    def send_messages(self, source: AtomicModel, msg: Message, time: HyperTime):
        targets = self.couplings.get((source, msg.port), [])
        for dest, dst_port in targets:
            new_msg = Message(dst_port, msg.value)
            self.schedule_external(time.after_epsilon(1), dest, new_msg)

    def schedule_external(self, time: HyperTime, model: AtomicModel, message: Message):
        heapq.heappush(
            self.external_events,
            DEVS_Event(time, self._sequence, "external", model, message),
        )
        self._sequence += 1

    def initialize(self):
        for model in self.models:
            self.schedule(model, self.time)

    def run(self):
        self.initialize()
        while True:
            internal_times = [
                time for time in self.model_next_event.values() if time is not None
            ]
            next_internal = min(internal_times) if internal_times else None
            next_external = (
                self.external_events[0].time if self.external_events else None
            )
            candidates = [
                time for time in (next_internal, next_external) if time is not None
            ]
            if not candidates:
                break
            t_next = min(candidates)

            if t_next.macro > self.end_minutes * 60:
                break

            self.time = t_next

            imminent = [
                model
                for model, event_time in self.model_next_event.items()
                if event_time == t_next
            ]
            for model in imminent:
                msg = model.out()
                if msg:
                    self.send_messages(model, msg, self.time)
            for model in imminent:
                model.dint()
                self.model_last_event[model] = self.time
                self.schedule(model, self.time)

            external_by_model: dict[AtomicModel, list[Message]] = {}
            while self.external_events and self.external_events[0].time == t_next:
                event = heapq.heappop(self.external_events)
                if event.message is not None:
                    external_by_model.setdefault(event.model, []).append(event.message)
            for model, messages in external_by_model.items():
                elapsed = float(self.time.macro - self.model_last_event[model].macro)
                for index, message in enumerate(messages):
                    model.dext(elapsed if index == 0 else 0.0, message)
                self.model_last_event[model] = self.time
                self.schedule(model, self.time)


# --- C02 DEVS Models ---


class StationModel(AtomicModel):
    """
    Formal DEVS Atomic Model for a Station.

    States:
      - passive: empty, waiting for pallets.
      - shifting_in: moving from main belt B1 to B2 (takes 2 sec).
      - buffering: waiting in buffer or traveling along buffer to station.
      - processing: at the positioning unit undergoing operation.
      - shifting_out: moving from B2 to B1 (takes 2 sec).

    In reality, due to the buffer holding multiple pallets concurrently,
    a strict AtomicModel state machine needs to track a queue of pallets
    and multiplex their delays. Since standard DEVS typically has a single
    sigma, we track multiple events using a single state variable that
    predicts the *next* event time.
    """

    def __init__(
        self,
        name: str,
        config: StationConfig,
        constants: C02Constants,
        is_a1: bool = False,
    ):
        super().__init__(name)
        self.config = config
        self.constants = constants
        self.is_a1 = is_a1

        # State variables
        self.buffer_queue: list[Pallet] = []
        self.processing_pallet: Pallet | None = None
        self.shifting_out_pallet: Pallet | None = None
        # Reserve synchronously at routing, before the DEVS message arrives.
        # Several arrivals in one macro/micro instant must not claim one slot.
        self.reserved_admissions: set[int] = set()

        # Next event times relative to current time
        self.next_internal_event: str | None = None
        self.events: list[
            tuple[float, str, Pallet]
        ] = []  # (remaining_time, event_type, pallet)

    @property
    def occupancy(self) -> int:
        """Return the number of pallets committed to the B2 branch.

        Capacity decisions must include pallets that are still shifting in and
        out; otherwise simultaneous arrivals can overbook the finite branch.
        """
        shifting_in = sum(
            event_type == "SHIFT_IN_DONE" for _, event_type, _ in self.events
        )
        travelling = sum(
            event_type == "BUFFER_ARRIVAL" for _, event_type, _ in self.events
        )
        shifting_out = sum(
            event_type == "SHIFT_OUT_DONE" for _, event_type, _ in self.events
        )
        leaving_station = sum(
            event_type == "POST_TRAVEL_DONE" for _, event_type, _ in self.events
        )
        return (
            len(self.buffer_queue)
            + shifting_in
            + travelling
            + shifting_out
            + leaving_station
            + int(self.processing_pallet is not None)
            + len(self.reserved_admissions)
        )

    @property
    def buffer_load(self) -> int:
        """Pallets committed to the travelling and waiting part of B2."""
        shifting_in = sum(
            event_type == "SHIFT_IN_DONE" for _, event_type, _ in self.events
        )
        travelling = sum(
            event_type == "BUFFER_ARRIVAL" for _, event_type, _ in self.events
        )
        shifting_out = sum(
            event_type == "SHIFT_OUT_DONE" for _, event_type, _ in self.events
        )
        return (len(self.buffer_queue) + travelling + shifting_in + shifting_out
                + len(self.reserved_admissions))

    def _schedule_internal(self, delay: float, event_type: str, pallet: Pallet):
        self.events.append((delay, event_type, pallet))
        self._update_sigma()

    def _update_sigma(self):
        if not self.events:
            self.sigma = math.inf
            self.next_internal_event = None
        else:
            self.events.sort(key=lambda x: x[0])
            self.sigma = self.events[0][0]
            self.next_internal_event = self.events[0][1]

    def dext(self, e: float, message: Message):
        # Time advance all pending events
        for i in range(len(self.events)):
            self.events[i] = (
                self.events[i][0] - e,
                self.events[i][1],
                self.events[i][2],
            )

        if message.port == "in":
            pallet: Pallet = message.value
            self.reserved_admissions.discard(pallet.id)
            # Pallet is shifting in (takes 2 sec)
            self._schedule_internal(self.config.shift_time, "SHIFT_IN_DONE", pallet)

    def out(self) -> Message | None:
        if self.next_internal_event == "SHIFT_OUT_DONE":
            # Just look at the first event
            pallet = self.events[0][2]
            return Message("out", pallet)
        return None

    def dint(self):
        if not self.events:
            return

        # Time advance by sigma (which is events[0][0])
        e = self.sigma
        for i in range(len(self.events)):
            self.events[i] = (
                self.events[i][0] - e,
                self.events[i][1],
                self.events[i][2],
            )

        # Pop the first event (it is now at time 0)
        _, event_type, pallet = self.events.pop(0)

        if event_type == "SHIFT_IN_DONE":
            # The B2 belt keeps moving while the station processes another
            # pallet.  Model that travel independently instead of adding it to
            # every serial processing cycle.
            # The buffer is part of B2, not an additional conveyor length.
            # Place the processing point at the positioning unit's centre.
            travel_time = (
                self.config.length_buffer + self.constants.positioning_unit_length / 2
            ) / self.constants.speed_m_s
            self._schedule_internal(travel_time, "BUFFER_ARRIVAL", pallet)

        elif event_type == "BUFFER_ARRIVAL":
            self.buffer_queue.append(pallet)
            self._check_buffer_to_processing()

        elif event_type == "PROCESSING_DONE":
            self.processing_pallet = None

            # Apply operation
            if self.is_a1:
                pass  # Unload/load happens, but we handle in_system tracking at SourceSink
            else:
                if self.config.name.startswith("A2"):
                    pallet.operations_done.add("A2")
                elif self.config.name == "A3":
                    pallet.operations_done.add("A3")
                elif self.config.name == "A4":
                    pallet.operations_done.add("A4")
                elif self.config.name == "A5":
                    pallet.operations_done.add("A5")
                elif self.config.name == "A6":
                    missing = {"A3", "A4", "A5"} - pallet.operations_done
                    pallet.operations_done.update(missing)

            # Travel from the positioning unit to Sy is separate from both
            # processing and shifting, as required by clarification 4.
            remaining_length = (
                self.config.length_b1
                - self.config.length_buffer
                - self.constants.positioning_unit_length / 2
            )
            self._schedule_internal(
                remaining_length / self.constants.speed_m_s,
                "POST_TRAVEL_DONE",
                pallet,
            )
            self._check_buffer_to_processing()

        elif event_type == "POST_TRAVEL_DONE":
            self._schedule_internal(self.config.shift_time, "SHIFT_OUT_DONE", pallet)

        elif event_type == "SHIFT_OUT_DONE":
            # Output was already sent
            pass

        self._update_sigma()

    def _check_buffer_to_processing(self):
        if self.buffer_queue and self.processing_pallet is None:
            # Pop next
            pallet = self.buffer_queue.pop(0)
            self.processing_pallet = pallet

            duration = self.config.op_time
            if self.is_a1 and not pallet.in_system:
                # Initially empty pallets require loading only (7.5 s).
                duration /= 2
            self._schedule_internal(duration, "PROCESSING_DONE", pallet)


class ConveyorModel(AtomicModel):
    """
    Formal DEVS Atomic Model for a conveyor belt segment.
    Transports a pallet with a fixed delay.
    """

    def __init__(self, name: str, length: float, constants: C02Constants):
        super().__init__(name)
        self.delay = length / constants.speed_m_s
        self.events: list[tuple[float, Pallet]] = []

    def dext(self, e: float, message: Message):
        for i in range(len(self.events)):
            self.events[i] = (self.events[i][0] - e, self.events[i][1])

        if message.port == "in":
            self.events.append((self.delay, message.value))
            self.events.sort(key=lambda x: x[0])
            self.sigma = self.events[0][0]

    def out(self) -> Message | None:
        if self.events:
            return Message("out", self.events[0][1])
        return None

    def dint(self):
        e = self.sigma
        for i in range(len(self.events)):
            self.events[i] = (self.events[i][0] - e, self.events[i][1])

        self.events.pop(0)

        if self.events:
            self.sigma = self.events[0][0]
        else:
            self.sigma = math.inf


class RouterModel(AtomicModel):
    """
    Formal DEVS Atomic Model for the Sx routing point.
    Decides if a pallet enters the station or bypasses it.
    It takes 0 delay (passes through instantly) but modifies routing.
    """

    def __init__(self, name: str, station_model: StationModel, is_a1: bool = False):
        super().__init__(name)
        self.station_model = station_model
        self.is_a1 = is_a1
        self.queue: list[tuple[Pallet, str]] = []  # (pallet, destination_port)
        self.arrival_counter = 0
        self.alternative_a6: StationModel | None = None

    def dext(self, e: float, message: Message):
        if message.port == "in":
            pallet: Pallet = message.value
            self.arrival_counter += 1

            needs_processing = False
            s_name = self.station_model.config.name

            if self.is_a1:
                required = {"A2", "A3", "A4", "A5"}
                # A1 loads an initially empty pallet and unloads only a
                # finished workpiece.  An incomplete pallet stays on B1 for
                # another circuit instead of being counted as throughput.
                needs_processing = not pallet.in_system or required.issubset(
                    pallet.operations_done
                )
            elif not pallet.in_system:
                # Initially empty pallets must reach A1 before any assembly.
                needs_processing = False
            elif s_name.startswith("A2"):
                group = pallet.operations_done & {"A3", "A4", "A5"}
                if "A2" not in pallet.operations_done and group in (
                    set(), {"A3", "A4", "A5"}
                ):
                    stride = {"A2_1": 3, "A2_2": 2, "A2_3": 1}[s_name]
                    needs_processing = self.arrival_counter % stride == 0
            elif s_name == "A3" and "A3" not in pallet.operations_done:
                a6_occupancy = 0
                if self.alternative_a6 is not None:
                    a6_occupancy = self.alternative_a6.buffer_load
                needs_processing = not pallet.fallback_to_a6 and a6_occupancy >= 3
                if not needs_processing:
                    pallet.fallback_to_a6 = True
            elif s_name == "A4" and "A4" not in pallet.operations_done:
                needs_processing = (
                    not pallet.fallback_to_a6 and "A3" in pallet.operations_done
                )
            elif s_name == "A5" and "A5" not in pallet.operations_done:
                needs_processing = not pallet.fallback_to_a6 and {"A3", "A4"}.issubset(
                    pallet.operations_done
                )
            elif s_name == "A6":
                needs_processing = pallet.fallback_to_a6 or not {
                    "A3",
                    "A4",
                    "A5",
                }.issubset(pallet.operations_done)

            # Check buffer occupancy. We peek into the station model's state.
            # In pure DEVS, this would be coupled via a port, but peeking is equivalent to
            # a zero-delay status port for the sake of this reference implementation.

            # buffer_occupancy = buffer_queue + items currently shifting in + processing
            # We can count events destined for SHIFT_IN_DONE, plus len(buffer_queue), plus 1 if processing
            occupancy = self.station_model.occupancy

            can_shift = (
                needs_processing
                and occupancy < self.station_model.config.buffer_capacity
            )

            if needs_processing and not can_shift and s_name in {"A3", "A4", "A5"}:
                pallet.fallback_to_a6 = True

            if can_shift:
                self.station_model.reserved_admissions.add(pallet.id)
                self.queue.append((pallet, "to_station"))
            else:
                self.queue.append((pallet, "to_conveyor"))

            self.sigma = 0.0  # route immediately

    def out(self) -> Message | None:
        if self.queue:
            pallet, port = self.queue[0]
            return Message(port, pallet)
        return None

    def dint(self):
        self.queue.pop(0)
        if self.queue:
            self.sigma = 0.0
        else:
            self.sigma = math.inf


class SourceSinkModel(AtomicModel):
    """
    Handles the overall throughput collection at A1 and initial pallet injection.
    """

    def __init__(self, constants: C02Constants, num_pallets: int):
        super().__init__("SourceSink")
        self.constants = constants
        self.num_pallets = num_pallets
        self.pallets = [Pallet(id=i) for i in range(num_pallets)]
        self.queue: list[Pallet] = []
        self.coordinator: Coordinator | None = None

    def dext(self, e: float, message: Message):
        if message.port == "in":
            pallet: Pallet = message.value
            # Output record if it completed a loop
            time = self.coordinator.time if self.coordinator else HyperTime.at(0)
            if (
                pallet.in_system
                and time.macro >= self.constants.warmup_minutes * 60
                and self.coordinator
            ):
                self.coordinator.throughput += 1
                self.coordinator.total_throughput_time += float(
                    time.macro - pallet.arrival_time.macro
                )

            pallet.reset(time)
            self.queue.append(pallet)
            self.sigma = 0.0

    def out(self) -> Message | None:
        if self.queue:
            return Message("out", self.queue[0])
        return None

    def dint(self):
        self.queue.pop(0)
        if self.queue:
            self.sigma = 0.0
        else:
            self.sigma = math.inf


def _station_configs(constants: C02Constants) -> tuple[StationConfig, ...]:
    return tuple(
        StationConfig.create(
            name,
            operation,
            length,
            buffer,
            constants.pallet_length,
            shift_time=constants.shift_time,
        )
        for name, operation, length, buffer in (
            ("A1", 15.0, 2.0, 1.2),
            ("A2_1", 60.0, 1.6, 0.8),
            ("A2_2", 60.0, 1.6, 0.8),
            ("A2_3", 60.0, 1.6, 0.8),
            ("A3", 20.0, 1.6, 0.8),
            ("A4", 20.0, 1.6, 0.8),
            ("A5", 20.0, 1.6, 0.8),
            ("A6", 30.0, 2.0, 1.2),
        )
    )


def solve_c02_legacy(num_pallets: int) -> dict[str, float | None]:
    """Run the partial C02 transport abstraction, not a validated plant model.

    Belt blocking and merge contention are not implemented. ``deadlock`` is
    therefore unknown (None). High-load cases requiring those mechanisms are
    rejected rather than returning a published deadlock as a simulated result.
    See ARGESIM_AUDIT.md for the remaining timing and transport mismatches.
    """
    if (
        isinstance(num_pallets, bool)
        or not isinstance(num_pallets, int)
        or num_pallets <= 0
    ):
        raise ValueError("num_pallets must be a positive integer")

    if num_pallets >= 50:
        raise NotImplementedError(
            "C02 high-load cases require belt blocking and merge contention; "
            "deadlock detection is not implemented"
        )

    constants = C02Constants()
    coord = Coordinator(constants.end_minutes)

    station_configs = _station_configs(constants)

    distances = [0.4, 0.4, 0.4, 0.0, 0.4, 0.4, 0.4, 0.0]

    stations = []
    routers = []
    conveyor_b1s = []
    conveyor_gaps = []

    source_sink = SourceSinkModel(constants, num_pallets)
    source_sink.coordinator = coord
    coord.add_model(source_sink)

    for i, config in enumerate(station_configs):
        is_a1 = i == 0
        station = StationModel(f"Station_{config.name}", config, constants, is_a1)
        router = RouterModel(f"Router_{config.name}", station, is_a1)
        b1 = ConveyorModel(
            f"B1_{config.name}", config.b1_transport_length(constants), constants
        )
        gap_len = distances[i]

        # We model the gap to the next station as another conveyor segment
        if gap_len > 0:
            gap = ConveyorModel(f"Gap_{config.name}", gap_len, constants)
        else:
            gap = None

        stations.append(station)
        routers.append(router)
        conveyor_b1s.append(b1)
        conveyor_gaps.append(gap)

        coord.add_model(station)
        coord.add_model(router)
        coord.add_model(b1)
        if gap:
            coord.add_model(gap)

    # A3's benchmark routing rule depends on the current load of A6's B2 lane.
    routers[4].alternative_a6 = stations[7]

    # Connect them
    for i in range(8):
        # 1. Router to Station (Shift to B2)
        coord.add_coupling(routers[i], "to_station", stations[i], "in")

        # 2. Router to B1 (Bypass)
        coord.add_coupling(routers[i], "to_conveyor", conveyor_b1s[i], "in")

        # 3. Station (Shift to B1 done) -> Gap or Next Router
        if conveyor_gaps[i]:
            coord.add_coupling(stations[i], "out", conveyor_gaps[i], "in")
            coord.add_coupling(conveyor_b1s[i], "out", conveyor_gaps[i], "in")
            coord.add_coupling(conveyor_gaps[i], "out", routers[(i + 1) % 8], "in")
        else:
            coord.add_coupling(stations[i], "out", routers[(i + 1) % 8], "in")
            coord.add_coupling(conveyor_b1s[i], "out", routers[(i + 1) % 8], "in")

    # Connect A1 logic to SourceSink
    # Actually, the problem says A1 unloads and loads.
    # Let's intercept the flow at A1's router or station out.
    # To correctly measure throughput, we route pallets from Station_A1's out to SourceSink,
    # and from SourceSink out to Conveyor Gap_A1.

    # Remove existing coupling from A1 out
    coord.couplings[(stations[0], "out")] = []

    # New couplings for A1 out -> SourceSink -> Gap_A1
    coord.add_coupling(stations[0], "out", source_sink, "in")
    coord.add_coupling(source_sink, "out", conveyor_gaps[0], "in")

    # Inject pallets initially.
    # We simulate them being evenly spaced.
    total_b1_length = sum(
        s.b1_transport_length(constants) for s in station_configs
    ) + sum(distances)
    spacing = total_b1_length / num_pallets

    # We will use an Injector model to send them at time 0 to various segments.
    # For simplicity of DEVS setup, we can just pre-load the gap conveyors' events arrays.
    for i, pallet in enumerate(source_sink.pallets):
        pos = i * spacing
        current_dist = 0.0
        for s_idx, config in enumerate(station_configs):
            segment_len = config.b1_transport_length(constants) + distances[s_idx]
            if current_dist + segment_len >= pos or s_idx == 7:
                dist_to_end = current_dist + segment_len - pos
                travel_time = dist_to_end / constants.speed_m_s

                # Schedule initial placements as real external events.  Calling
                # ``dext`` here with a future elapsed time corrupts DEVS state
                # and is overwritten by coordinator initialization.
                target_router = routers[(s_idx + 1) % 8]
                coord.schedule_external(
                    HyperTime.at(travel_time), target_router, Message("in", pallet)
                )
                break
            current_dist += segment_len

    coord.run()

    avg_throughput_time = (
        coord.total_throughput_time / coord.throughput if coord.throughput > 0 else 0.0
    )

    return {
        "throughput": float(coord.throughput),
        "average_throughput_time": avg_throughput_time,
        "deadlock": None,
    }


def solve_c02(
    num_pallets: int,
    *,
    controller: str = "first-eligible",
    unit_timing: str = "exclusive",
    initial_seed: int | None = None,
) -> dict:
    """Run the standard 120-to-600-minute C02 experiment for one pallet count.

    The mean part time spans completion of loading to the start of unloading.
    Also report means through completed unloading and with both A1 handling
    operations. Means are None when no part completes in the counting window.
    The optional service-only timing assigns approach and clearance to the
    adjoining conveyors to quantify sensitivity to processor occupancy.
    An integer initial_seed samples occupied B1 slots without replacement.
    """
    from .c02_transport import C02Plant

    return C02Plant(
        num_pallets,
        controller=controller,
        unit_timing=unit_timing,
        initial_seed=initial_seed,
    ).run()
