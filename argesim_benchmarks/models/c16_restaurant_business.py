"""ARGESIM C16: Restaurant Business Dynamics.

Agent-based stochastic dynamics of restaurants and customers in a spatial grid.
"""

from __future__ import annotations

import heapq
import math
import random
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence

from nsa_devs import HyperTime

@dataclass(frozen=True)
class C16Parameters:
    """Parameters in the notation of the official C16 definition."""

    total_people: int = 3000
    initial_restaurants: int = 30
    area_width: float = 600.0
    area_height: float = 400.0
    maximum_dining_interval: int = 8
    dinner_cost: float = 1.0
    range_limit: float = 100.0
    running_cost: float = 150.0
    initial_tax_rate: float = 0.20
    profit_threshold: float = 350.0
    opening_probability: float = 0.10
    closing_probability: float = 0.20
    k_density: float = 4.0
    cell_size: float = 20.0

    def __post_init__(self) -> None:
        if self.total_people <= 0:
            raise ValueError("total_people must be positive")
        if self.area_width <= 0 or self.area_height <= 0:
            raise ValueError("area dimensions must be positive")
        if self.cell_size <= 0:
            raise ValueError("cell_size must be positive")


_C16_DEFAULT_PARAMETERS = C16Parameters()


@dataclass(frozen=True)
class City:
    name: str
    x: float
    y: float
    max_r: float
    population_fraction: float


CITIES: tuple[City, ...] = (
    City("A", 100.0, 70.0, 100.0, 0.10),
    City("B", 360.0, 90.0, 250.0, 0.25),
    City("C", 180.0, 250.0, 250.0, 0.25),
    City("D", 510.0, 130.0, 100.0, 0.10),
    City("E", 480.0, 300.0, 300.0, 0.30),
)


@dataclass
class Person:
    x: float
    y: float
    days_until_next_visit: int


@dataclass
class Restaurant:
    x: float
    y: float
    weekly_revenue: float = 0.0


def initialize_people(parameters: C16Parameters, seed: int | None = None) -> list[Person]:
    rng = random.Random(seed)
    people = []

    city_counts = [int(parameters.total_people * city.population_fraction) for city in CITIES]
    # Ensure total is exactly total_people
    diff = parameters.total_people - sum(city_counts)
    if diff > 0:
        city_counts[0] += diff
    elif diff < 0:
        city_counts[0] -= -diff

    for city, count in zip(CITIES, city_counts):
        for _ in range(count):
            while True:
                angle = rng.uniform(0, 2 * math.pi)
                # Triangular distribution from 0 to MaxR with mean at 0 (mode at 0).
                # To simulate this, we can use the inverse transform sampling for a triangular
                # distribution with min=0, mode=0, max=MaxR: r = MaxR * (1 - sqrt(1 - U))
                u = rng.uniform(0, 1)
                r = city.max_r * (1.0 - math.sqrt(1.0 - u))

                x = city.x + r * math.cos(angle)
                y = city.y + r * math.sin(angle)

                if 0 <= x < parameters.area_width and 0 <= y < parameters.area_height:
                    interval = rng.randint(1, parameters.maximum_dining_interval)
                    people.append(Person(x, y, interval))
                    break
    return people


def initialize_restaurants(parameters: C16Parameters) -> list[Restaurant]:
    restaurants = []
    n = parameters.initial_restaurants
    if n <= 0:
        return restaurants

    # Calculate a grid that fits n restaurants approximately as a rectangle
    # similar to 6x5 for 30.
    cols = int(math.ceil(math.sqrt(n * 1.2)))
    rows = int(math.ceil(n / cols))

    # Avoid div by zero if only 1 col/row
    dx = parameters.area_width / (cols + 1)
    dy = parameters.area_height / (rows + 1)

    count = 0
    for row in range(rows):
        for col in range(cols):
            if count >= n:
                break
            x = dx + col * dx
            y = dy + row * dy
            restaurants.append(Restaurant(x, y))
            count += 1

    return restaurants


class EventType(Enum):
    DINNER = auto()
    END_OF_WEEK = auto()

@dataclass(order=True)
class ScheduledEvent:
    time: HyperTime
    sequence: int
    event_type: EventType = field(compare=False)
    person_idx: int = field(compare=False, default=-1)

class C16Simulation:
    def __init__(self, parameters: C16Parameters = _C16_DEFAULT_PARAMETERS, seed: int | None = None):
        self.parameters = parameters
        self.rng = random.Random(seed)
        self.people = initialize_people(parameters, seed)
        self.restaurants = initialize_restaurants(parameters)

        self.total_tax = 0.0
        self._cumulative_revenue = 0.0
        self.current_time = HyperTime.at(0)

        self.queue: list[ScheduledEvent] = []
        self._seq = 0

        # Schedule initial events
        self._schedule(HyperTime.at(7), EventType.END_OF_WEEK)
        for idx, p in enumerate(self.people):
            # p.days_until_next_visit is 1 to max interval
            t = HyperTime.at(p.days_until_next_visit)
            self._schedule(t, EventType.DINNER, person_idx=idx)

    def _schedule(self, time: HyperTime, event_type: EventType, person_idx: int = -1) -> None:
        heapq.heappush(self.queue, ScheduledEvent(time, self._seq, event_type, person_idx))
        self._seq += 1

    def run_until(self, max_days: int, tax_rate: float | None = None) -> None:
        """Run the event-driven simulation until the specified macro time."""
        if tax_rate is None:
            tax_rate = self.parameters.initial_tax_rate

        bound = HyperTime.at(max_days)

        while self.queue and self.queue[0].time <= bound:
            event = heapq.heappop(self.queue)
            self.current_time = event.time

            if event.event_type == EventType.DINNER:
                self._handle_dinner(event.person_idx)
            elif event.event_type == EventType.END_OF_WEEK:
                self._handle_end_of_week(tax_rate)

    def _handle_dinner(self, person_idx: int) -> None:
        person = self.people[person_idx]

        # Find restaurants in range
        in_range = []
        for r in self.restaurants:
            dist = math.hypot(person.x - r.x, person.y - r.y)
            if dist <= self.parameters.range_limit:
                in_range.append(r)

        if in_range:
            chosen = self.rng.choice(in_range)
            chosen.weekly_revenue += self.parameters.dinner_cost
            self._cumulative_revenue += self.parameters.dinner_cost

        # Reschedule next dinner
        interval = self.rng.randint(1, self.parameters.maximum_dining_interval)
        next_time = self.current_time.after_finite(interval)
        self._schedule(next_time, EventType.DINNER, person_idx)

    def _handle_end_of_week(self, tax_rate: float) -> None:
        new_restaurants = []
        restaurants_to_keep = []

        for r in self.restaurants:
            taxable = r.weekly_revenue - self.parameters.running_cost
            if taxable > 0:
                tax = taxable * tax_rate
                self.total_tax += tax
            else:
                tax = 0.0
            profit = r.weekly_revenue - self.parameters.running_cost - tax

            r.weekly_revenue = 0.0  # Reset for next week

            if profit > self.parameters.profit_threshold:
                if self.rng.random() < self.parameters.opening_probability:
                    new_restaurants.append(self._find_best_location())
                restaurants_to_keep.append(r)
            elif profit < self.parameters.profit_threshold:
                if self.rng.random() < self.parameters.closing_probability:
                    # closes down
                    pass
                else:
                    restaurants_to_keep.append(r)
            else:
                restaurants_to_keep.append(r)

        self.restaurants = restaurants_to_keep + new_restaurants

        # Schedule next end of week
        next_week = self.current_time.after_finite(7)
        self._schedule(next_week, EventType.END_OF_WEEK)

    def _find_best_location(self) -> Restaurant:
        """Find the best cell to launch a new restaurant."""
        cell_size = self.parameters.cell_size
        cols = int(self.parameters.area_width / cell_size)
        rows = int(self.parameters.area_height / cell_size)

        # Precompute population per cell
        people_density = [[0 for _ in range(cols)] for _ in range(rows)]
        for person in self.people:
            c = int(person.x / cell_size)
            r = int(person.y / cell_size)
            c = min(c, cols - 1)
            r = min(r, rows - 1)
            people_density[r][c] += 1

        best_ratio = -1.0
        best_cells = []

        for r in range(rows):
            for c in range(cols):
                cx = (c + 0.5) * cell_size
                cy = (r + 0.5) * cell_size

                rest_density = 0.0
                for rest in self.restaurants:
                    dist = math.hypot(cx - rest.x, cy - rest.y)
                    if self.parameters.k_density == 0.0:
                        rest_density += 0.0 if dist > 0 else 1.0
                    else:
                        rest_density += 1.0 / ((dist / self.parameters.k_density) + 1.0)

                if rest_density == 0.0:
                    ratio = float('inf') if people_density[r][c] > 0 else 0.0
                else:
                    ratio = people_density[r][c] / rest_density

                if ratio > best_ratio:
                    best_ratio = ratio
                    best_cells = [(r, c)]
                elif abs(ratio - best_ratio) < 1e-9:
                    best_cells.append((r, c))

        best_r, best_c = self.rng.choice(best_cells)
        new_x = best_c * cell_size + self.rng.uniform(0, cell_size)
        new_y = best_r * cell_size + self.rng.uniform(0, cell_size)
        return Restaurant(new_x, new_y)

def c16_task_a(runs: int = 50, seed: int = 42) -> dict[str, object]:
    """Task A: Time Domain Analysis."""
    rng = random.Random(seed)

    sim = C16Simulation(seed=rng.randint(0, 1000000))
    time_series = []

    for week in range(10 * 52):
        sim.run_until((week + 1) * 7)
        time_series.append(len(sim.restaurants))

    total_avg_after_5_years = 0.0

    for _ in range(runs):
        sim_run = C16Simulation(seed=rng.randint(0, 1000000))
        run_sum = 0
        run_count = 0
        for week in range(10 * 52):
            sim_run.run_until((week + 1) * 7)
            if week >= 5 * 52:
                run_sum += len(sim_run.restaurants)
                run_count += 1
        total_avg_after_5_years += (run_sum / run_count)

    return {
        "time_series_10_years": time_series,
        "average_after_5_years": total_avg_after_5_years / runs,
    }


def c16_task_b(tax_rates: Sequence[float] | None = None, seed: int = 42) -> dict[float, float]:
    """Task B: Tax Income Maximisation."""
    if tax_rates is None:
        tax_rates = [i * 0.05 for i in range(11)]

    rng = random.Random(seed)
    results = {}

    for rate in tax_rates:
        sim = C16Simulation(seed=rng.randint(0, 1000000))
        sim.run_until(5 * 52 * 7, tax_rate=rate)
        results[rate] = sim.total_tax

    return results


def c16_task_c(k_values: Sequence[float] | None = None, seed: int = 42) -> dict[float, float]:
    """Task C: Restaurants' Revenue Analysis."""
    if k_values is None:
        k_values = [i * 0.5 for i in range(13)]

    rng = random.Random(seed)
    results = {}

    for k in k_values:
        from dataclasses import replace
        params = replace(_C16_DEFAULT_PARAMETERS, k_density=k)

        sim = C16Simulation(parameters=params, seed=rng.randint(0, 1000000))

        # We need a way to track total revenue. We can just add a tracker to handle_end_of_week
        # but since we want to avoid changing too much, let's inject a tracker.
        total_revenue = 0.0

        for week in range(5 * 52):
            # Run up to just before END_OF_WEEK triggers at week*7 + 7.
            # Actually, END_OF_WEEK at day 7 will run.
            # We can't easily intercept without adding state to C16Simulation.
            # Let's add `cumulative_revenue` to C16Simulation.
            sim.run_until((week + 1) * 7)

        results[k] = sim._cumulative_revenue

    return results
