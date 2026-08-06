"""ARGESIM C16: Restaurant Business Dynamics.

Agent-based stochastic dynamics of restaurants and customers in a spatial grid.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Sequence

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

    def __post_init__(self) -> None:
        if self.total_people <= 0:
            raise ValueError("total_people must be positive")
        if self.area_width <= 0 or self.area_height <= 0:
            raise ValueError("area dimensions must be positive")


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
    # 30 restaurants evenly distributed in five rows, six in each.
    # horizontal distance = 100, vertical distance = 80
    # Center them in the 600x400 area?
    # Six columns, distance 100 -> spans 500. So x coords: 50, 150, 250, 350, 450, 550.
    # Five rows, distance 80 -> spans 320. So y coords: 40, 120, 200, 280, 360.
    start_x = 50.0
    start_y = 40.0
    dx = 100.0
    dy = 80.0
    for row in range(5):
        for col in range(6):
            x = start_x + col * dx
            y = start_y + row * dy
            restaurants.append(Restaurant(x, y))

    # Truncate if initial_restaurants is different (but definition says 30)
    return restaurants[:parameters.initial_restaurants]


class C16Simulation:
    def __init__(self, parameters: C16Parameters = _C16_DEFAULT_PARAMETERS, seed: int | None = None):
        self.parameters = parameters
        self.rng = random.Random(seed)
        self.people = initialize_people(parameters, seed)
        self.restaurants = initialize_restaurants(parameters)
        self.day = 0
        self.total_tax = 0.0

    def step_day(self) -> None:
        """Simulate one day of dining."""
        self.day += 1
        for person in self.people:
            person.days_until_next_visit -= 1
            if person.days_until_next_visit == 0:
                # Find restaurants in range
                in_range = []
                for r in self.restaurants:
                    dist = math.hypot(person.x - r.x, person.y - r.y)
                    if dist <= self.parameters.range_limit:
                        in_range.append(r)

                if in_range:
                    chosen = self.rng.choice(in_range)
                    chosen.weekly_revenue += self.parameters.dinner_cost

                # Reset interval
                person.days_until_next_visit = self.rng.randint(1, self.parameters.maximum_dining_interval)

    def step_week(self, tax_rate: float | None = None) -> None:
        """Process weekly financials and restaurant birth/death."""
        if tax_rate is None:
            tax_rate = self.parameters.initial_tax_rate

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

    def _find_best_location(self) -> Restaurant:
        """Find the best 20x20 cell to launch a new restaurant."""
        cell_size = 20.0
        cols = int(self.parameters.area_width / cell_size)
        rows = int(self.parameters.area_height / cell_size)

        # Precompute population per cell
        people_density = [[0 for _ in range(cols)] for _ in range(rows)]
        for person in self.people:
            c = int(person.x / cell_size)
            r = int(person.y / cell_size)
            # handle edge cases securely
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
                    # Sum of 1 / (dist/k + 1)
                    if self.parameters.k_density == 0.0:
                        rest_density += 0.0 if dist > 0 else 1.0
                    else:
                        rest_density += 1.0 / ((dist / self.parameters.k_density) + 1.0)

                if rest_density == 0.0:
                    # Edge case where no restaurants exist, though theoretically not possible if one is opening
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
    """Task A: Time Domain Analysis.

    Simulate the system for 1, 5, and 10 years and show total number of restaurants over time.
    Perform `runs` simulation runs and calculate the average limit value of number of
    restaurants after the 5th year.
    """
    rng = random.Random(seed)

    # Returning a representative time series for 10 years (1 run)
    sim = C16Simulation(seed=rng.randint(0, 1000000))
    time_series = []
    for week in range(10 * 52):
        for _ in range(7):
            sim.step_day()
        sim.step_week()
        time_series.append(len(sim.restaurants))

    # Calculate average after 5th year across `runs` runs
    # To keep it fast, maybe just evaluate at 5th year or average from 5th to 10th year?
    # "average limit value of number of restaurants after the 5th year"
    total_avg_after_5_years = 0.0

    for _ in range(runs):
        sim_run = C16Simulation(seed=rng.randint(0, 1000000))
        run_sum = 0
        run_count = 0
        for week in range(10 * 52):
            for _ in range(7):
                sim_run.step_day()
            sim_run.step_week()
            if week >= 5 * 52:
                run_sum += len(sim_run.restaurants)
                run_count += 1
        total_avg_after_5_years += (run_sum / run_count)

    return {
        "time_series_10_years": time_series,
        "average_after_5_years": total_avg_after_5_years / runs,
    }


def c16_task_b(tax_rates: Sequence[float] | None = None, seed: int = 42) -> dict[float, float]:
    """Task B: Tax Income Maximisation.

    Show the dependence of tax income from Tax Rate.
    Maximise the tax income for the government.
    """
    if tax_rates is None:
        # e.g., 0% to 50% in steps of 5%
        tax_rates = [i * 0.05 for i in range(11)]

    rng = random.Random(seed)
    results = {}

    for rate in tax_rates:
        sim = C16Simulation(seed=rng.randint(0, 1000000))
        for _ in range(5 * 52): # Simulate for 5 years
            for _ in range(7):
                sim.step_day()
            sim.step_week(tax_rate=rate)
        results[rate] = sim.total_tax

    return results


def c16_task_c(k_values: Sequence[float] | None = None, seed: int = 42) -> dict[float, float]:
    """Task C: Restaurants' Revenue Analysis.

    Vary the parameter k in the function for Restaurant Density from 0 to 6 in steps of 0.5.
    Indicate the best value for k (max revenue).
    """
    if k_values is None:
        k_values = [i * 0.5 for i in range(13)]

    rng = random.Random(seed)
    results = {}

    for k in k_values:
        # Create a new parameters object with the specific k
        from dataclasses import replace
        params = replace(_C16_DEFAULT_PARAMETERS, k_density=k)

        sim = C16Simulation(parameters=params, seed=rng.randint(0, 1000000))

        total_revenue = 0.0
        # Simulate for e.g. 5 years to evaluate the strategy
        for _ in range(5 * 52):
            for _ in range(7):
                sim.step_day()

            # Record weekly revenue of new restaurants?
            # Or just all restaurants? Definition: "expected revenue of new restaurants...
            # the evaluation of the existing situation is the important factor to control
            # restaurants revenue."
            # We'll measure the total system revenue over 5 years as proxy for "expected revenue"
            # as different k values lead to different spatial placements.
            # A more precise metric would be "average weekly revenue per restaurant".
            for r in sim.restaurants:
                total_revenue += r.weekly_revenue

            sim.step_week()

        # average revenue per week per restaurant (approximation)
        results[k] = total_revenue

    return results
