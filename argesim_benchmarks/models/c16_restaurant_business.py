"""ARGESIM C16: Restaurant Business Dynamics.

Agent-based stochastic dynamics of restaurants and customers in a spatial grid.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass, replace
from enum import Enum, auto

from nsa_devs import DesScheduler, HyperTime

from ..parallel import ordered_map


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
        for name, value, allow_zero in (
            ("total_people", self.total_people, False),
            ("initial_restaurants", self.initial_restaurants, True),
            ("maximum_dining_interval", self.maximum_dining_interval, False),
        ):
            if (
                isinstance(value, bool)
                or not isinstance(value, int)
                or value < 0
                or (not allow_zero and value == 0)
            ):
                qualifier = "non-negative" if allow_zero else "positive"
                raise ValueError(f"{name} must be a {qualifier} integer")
        for name, value, allow_zero in (
            ("area_width", self.area_width, False),
            ("area_height", self.area_height, False),
            ("cell_size", self.cell_size, False),
            ("dinner_cost", self.dinner_cost, True),
            ("range_limit", self.range_limit, False),
            ("running_cost", self.running_cost, True),
            ("profit_threshold", self.profit_threshold, True),
            ("k_density", self.k_density, True),
        ):
            if not math.isfinite(value) or value < 0.0 or (not allow_zero and value == 0.0):
                qualifier = "non-negative" if allow_zero else "positive"
                raise ValueError(f"{name} must be finite and {qualifier}")
        if self.cell_size > min(self.area_width, self.area_height):
            raise ValueError("cell_size must fit within both area dimensions")
        if not 0.0 <= self.initial_tax_rate <= 1.0:
            raise ValueError("initial_tax_rate must be between zero and one")
        if not 0.0 <= self.opening_probability <= 1.0:
            raise ValueError("opening_probability must be between zero and one")
        if not 0.0 <= self.closing_probability <= 1.0:
            raise ValueError("closing_probability must be between zero and one")


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
    id: int = -1
    is_initial: bool = True
    weekly_revenue: float = 0.0
    lifetime_revenue: float = 0.0


def restaurant_density_at(
    x: float,
    y: float,
    restaurants: Sequence[Restaurant],
    k: float,
) -> float:
    """Evaluate the official ``sum((1 / distance) ** k)`` density."""

    if not all(math.isfinite(value) for value in (x, y, k)) or k < 0.0:
        raise ValueError("coordinates and non-negative density exponent must be finite")
    density = 0.0
    for restaurant in restaurants:
        distance = math.hypot(x - restaurant.x, y - restaurant.y)
        if k == 0.0:
            density += 1.0
        elif distance == 0.0:
            return math.inf
        else:
            density += (1.0 / distance) ** k
    return density


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
        dx = max(0.0, -city.x, city.x - parameters.area_width)
        dy = max(0.0, -city.y, city.y - parameters.area_height)
        if count and math.hypot(dx, dy) >= city.max_r:
            raise ValueError(f"population of city {city.name} cannot be placed inside the area")
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

    # The official benchmark uses six columns and five rows, with 100 units
    # horizontally and 80 vertically.  Half-spacing margins centre that grid
    # in the 600 x 400 area.
    if (
        n <= 30
        and parameters.area_width == 600.0
        and parameters.area_height == 400.0
    ):
        cols = 6
        dx = 100.0
        dy = 80.0
        x0 = 50.0
        y0 = 40.0
    else:
        cols = max(1, math.ceil(math.sqrt(n * parameters.area_width / parameters.area_height)))
        rows = max(1, math.ceil(n / cols))
        dx = parameters.area_width / cols
        dy = parameters.area_height / rows
        x0 = 0.5 * dx
        y0 = 0.5 * dy

    count = 0
    rows = math.ceil(n / cols)
    for row in range(rows):
        for col in range(cols):
            if count >= n:
                break
            x = x0 + col * dx
            y = y0 + row * dy
            restaurants.append(Restaurant(x, y, id=count))
            count += 1

    return restaurants


class EventType(Enum):
    DINNER = auto()
    END_OF_WEEK = auto()

class C16Simulation:
    def __init__(self, parameters: C16Parameters = _C16_DEFAULT_PARAMETERS, seed: int | None = None):
        self.parameters = parameters
        self.rng = random.Random(seed)
        self.people = initialize_people(parameters, seed)
        self.restaurants = initialize_restaurants(parameters)

        self.total_tax = 0.0
        self._cumulative_revenue = 0.0
        self._closed_new_restaurant_revenues: list[float] = []
        self._next_restaurant_id = len(self.restaurants)
        self.scheduler = DesScheduler()
        self._active_tax_rate = parameters.initial_tax_rate

        # Schedule initial events
        for idx, p in enumerate(self.people):
            # p.days_until_next_visit is 1 to max interval
            t = HyperTime.at(p.days_until_next_visit)
            self._schedule(t, EventType.DINNER, person_idx=idx)
        self._schedule(HyperTime.at(7), EventType.END_OF_WEEK)

    @property
    def current_time(self) -> HyperTime:
        return self.scheduler.time

    @property
    def queue(self):
        """Expose the shared scheduler queue for compatibility and inspection."""

        return self.scheduler.events

    def _schedule(self, time: HyperTime, event_type: EventType, person_idx: int = -1) -> None:
        # All dinners at a week boundary contribute before financial accounting.
        microstep = 0 if event_type == EventType.DINNER else 1
        target = HyperTime(time.macro, microstep)
        self.scheduler.schedule_at(
            target,
            f"C16:{event_type.name.lower()}",
            self._dispatch,
            event_type,
            person_idx,
        )

    def _dispatch(self, event_type: EventType, person_idx: int) -> None:
        if event_type == EventType.DINNER:
            self._handle_dinner(person_idx)
        elif event_type == EventType.END_OF_WEEK:
            self._handle_end_of_week(self._active_tax_rate)

    def run_until(
        self,
        max_days: float,
        tax_rate: float | None = None,
        *,
        max_events: int | None = None,
    ) -> int:
        """Run through the horizon, with an optional explicit limit on this call."""
        if tax_rate is None:
            tax_rate = self.parameters.initial_tax_rate
        if isinstance(max_days, bool) or not isinstance(max_days, (int, float)):
            raise TypeError("max_days must be a real number")
        if not math.isfinite(max_days) or max_days < float(self.current_time.macro):
            raise ValueError("max_days must be finite and cannot move time backwards")
        if isinstance(tax_rate, bool) or not isinstance(tax_rate, (int, float)):
            raise TypeError("tax_rate must be a real number")
        if not math.isfinite(tax_rate) or not 0.0 <= tax_rate <= 1.0:
            raise ValueError("tax_rate must be finite and between zero and one")
        if max_events is None:
            # Each person can dine at most once per day, with one weekly close.
            # Include the current day when resuming after a caller's event limit.
            days = math.floor(max_days) - math.floor(self.current_time.macro) + 1
            max_events = max(1_000_000, days * len(self.people) + (days + 6) // 7)
        self._active_tax_rate = tax_rate
        return self.scheduler.run(max_days, max_events=max_events)

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
            chosen.lifetime_revenue += self.parameters.dinner_cost
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
                    if not r.is_initial:
                        self._closed_new_restaurant_revenues.append(r.lifetime_revenue)
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

                rest_density = restaurant_density_at(
                    cx,
                    cy,
                    self.restaurants,
                    self.parameters.k_density,
                )

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
        restaurant = Restaurant(
            new_x,
            new_y,
            id=self._next_restaurant_id,
            is_initial=False,
        )
        self._next_restaurant_id += 1
        return restaurant

    def new_restaurant_revenues(self) -> tuple[float, ...]:
        """Return lifetime revenue observed for every restaurant opened in-run."""

        surviving = [
            restaurant.lifetime_revenue
            for restaurant in self.restaurants
            if not restaurant.is_initial
        ]
        return tuple(self._closed_new_restaurant_revenues + surviving)


def _weekly_restaurant_counts(parameters: C16Parameters, seed: int, weeks: int) -> list[int]:
    sim = C16Simulation(parameters=parameters, seed=seed)
    counts = []
    for week in range(1, weeks + 1):
        sim.run_until(week * 7)
        counts.append(len(sim.restaurants))
    return counts


def _year_five_observations(workload: tuple[C16Parameters, int, int]) -> tuple[int, float]:
    counts = _weekly_restaurant_counts(*workload)
    following_weeks = counts[5 * 52:]
    return counts[5 * 52 - 1], sum(following_weeks) / len(following_weeks)


def c16_task_a(
    runs: int = 50,
    seed: int = 42,
    *,
    parameters: C16Parameters = _C16_DEFAULT_PARAMETERS,
    years: int = 10,
    workers: int = 1,
) -> dict[str, object]:
    """Report the year-five endpoint and subsequent time average over independent runs."""
    if isinstance(runs, bool) or not isinstance(runs, int) or runs <= 0:
        raise ValueError("runs must be a positive integer")
    if isinstance(years, bool) or not isinstance(years, int) or years < 6:
        raise ValueError("Task A requires at least six years to estimate the post-year-5 limit")
    rng = random.Random(seed)

    total_weeks = years * 52
    trajectory_seed = rng.randint(0, 1_000_000)
    workloads = ((parameters, rng.randint(0, 1_000_000), total_weeks) for _ in range(runs))
    observations = ordered_map(_year_five_observations, workloads, workers=workers, backend="process")
    year_five_counts = [count for count, _ in observations]
    time_series = _weekly_restaurant_counts(parameters, trajectory_seed, total_weeks)

    return {
        "time_series_1_year": time_series[:52],
        "time_series_5_years": time_series[: 5 * 52],
        "time_series_10_years": time_series,
        "restaurants_at_year_5": year_five_counts,
        "mean_at_year_5": sum(year_five_counts) / runs,
        "average_after_5_years": sum(mean for _, mean in observations) / runs,
    }


def c16_task_b(
    tax_rates: Sequence[float] | None = None,
    seed: int = 42,
    *,
    runs: int = 5,
    years: int = 5,
    parameters: C16Parameters = _C16_DEFAULT_PARAMETERS,
) -> dict[float, float]:
    """Task B: Tax Income Maximisation."""
    if tax_rates is None:
        tax_rates = [i * 0.05 for i in range(21)]

    rates = tuple(float(rate) for rate in tax_rates)
    if not rates or any(not math.isfinite(rate) or not 0.0 <= rate <= 1.0 for rate in rates):
        raise ValueError("tax rates must be a non-empty finite sequence in [0, 1]")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in (runs, years)
    ):
        raise ValueError("runs and years must be positive integers")

    rng = random.Random(seed)
    run_seeds = tuple(rng.randint(0, 1000000) for _ in range(runs))
    results = {}

    for rate in rates:
        taxes = []
        for run_seed in run_seeds:
            sim = C16Simulation(parameters=parameters, seed=run_seed)
            sim.run_until(years * 52 * 7, tax_rate=rate)
            taxes.append(sim.total_tax)
        results[rate] = sum(taxes) / len(taxes)

    return results


def c16_task_c(
    k_values: Sequence[float] | None = None,
    seed: int = 42,
    *,
    runs: int = 5,
    years: int = 10,
    parameters: C16Parameters = _C16_DEFAULT_PARAMETERS,
) -> dict[float, float]:
    """Task C: Restaurants' Revenue Analysis."""
    if k_values is None:
        k_values = [i * 0.5 for i in range(13)]

    values = tuple(float(k) for k in k_values)
    if not values or any(not math.isfinite(k) or k < 0.0 or k > 6.0 for k in values):
        raise ValueError("k values must be a non-empty finite sequence in [0, 6]")
    if any(
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
        for value in (runs, years)
    ):
        raise ValueError("runs and years must be positive integers")

    rng = random.Random(seed)
    run_seeds = tuple(rng.randint(0, 1000000) for _ in range(runs))
    results = {}

    for k in values:
        params = replace(parameters, k_density=k)
        observed_revenues: list[float] = []
        for run_seed in run_seeds:
            sim = C16Simulation(parameters=params, seed=run_seed)
            sim.run_until(years * 52 * 7)
            observed_revenues.extend(sim.new_restaurant_revenues())

        results[k] = (
            sum(observed_revenues) / len(observed_revenues)
            if observed_revenues
            else 0.0
        )

    return results
