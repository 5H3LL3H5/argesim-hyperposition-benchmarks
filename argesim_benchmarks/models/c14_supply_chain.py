"""ARGESIM C14: Supply Chain.

Discrete-time supply chain simulation benchmark.

The system consists of 4 factories, 4 distributors, and a group of wholesalers.
Factories produce 12 types of products continuously.
Wholesalers place stochastic orders.
Distributors try to fulfill wholesalers' orders, ordering from factories.

Tasks a, b, c involve different ordering strategies.
"""

import random

# Simulation time is up to 30 days. Each day has 24 hours. Each hour has 3600 seconds.
# Total time: 30 days = 720 hours = 2,592,000 seconds.
#
# Interarrival time of products at factory: exponential with mean 600s.
# Rate lambda = 1/600 per second. Expected 6 products per hour per factory.
# However, each factory randomly picks one of its 6 products.
# So expected 1 product per type per hour.
#
# Orders at wholesalers: uniformly between [600, 3600]s.
# Time is discrete, measured in seconds from 0 to 2,592,000.

SUPPLY_LEAD_TIMES = {
    # D1, D2, D3, D4 mapping to F1, F2, F3, F4 (in hours)
    (1, 1): 16.0, (1, 2): 22.0, (1, 3): 20.0, (1, 4): 12.0,
    (2, 1): 15.0, (2, 2): 16.0, (2, 3): 13.0, (2, 4): 19.0,
    (3, 1): 14.0, (3, 2): 16.5, (3, 3): 20.0, (3, 4): 17.0,
    (4, 1): 22.0, (4, 2): 13.0, (4, 3): 16.5, (4, 4): 18.0,
}

FACTORY_PRODUCTS = {
    1: [1, 2, 3, 4, 5, 6],
    2: [7, 8, 9, 10, 11, 12],
    3: [4, 5, 6, 7, 8, 9],
    4: [10, 11, 12, 1, 2, 3],
}

DEFAULT_FACTORY_MAPPING = {
    1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1,
    7: 2, 8: 2, 9: 2, 10: 2, 11: 2, 12: 2,
}

TASK_A_B_MAPPING = {
    1: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1},
    2: {1: 1, 2: 1, 3: 1, 4: 1, 5: 1, 6: 1, 7: 2, 8: 2, 9: 2, 10: 2, 11: 2, 12: 2},
    3: {4: 3, 5: 3, 6: 3, 7: 3, 8: 3, 9: 3},
    4: {1: 4, 2: 4, 3: 4, 10: 4, 11: 4, 12: 4},
}

class Factory:
    def __init__(self, id: int, rng: random.Random):
        self.id = id
        self.products = FACTORY_PRODUCTS[id]
        self.stock = {p: 0 for p in self.products}
        self.rng = rng
        self.next_production_time = int(self.rng.expovariate(1/600))

class Distributor:
    def __init__(self, id: int):
        self.id = id
        self.stock = {p: 0 for p in range(1, 13)}
        self.incoming_deliveries = [] # list of tuples: (arrival_time, product, amount)
        self.wholesaler_demand = {p: 0 for p in range(1, 13)} # tracked for task b
        self.backlogged_orders = [] # task b & c: deferred factory orders

        # metrics
        self.total_cost = 0.0
        self.delivered_products = 0

    def calculate_storage_cost(self):
        # 1 euro per product per day
        total_products = sum(self.stock.values())
        self.total_cost += total_products * 1.0

    def fulfill_wholesaler_order(self, product: int) -> bool:
        self.wholesaler_demand[product] += 1
        if self.stock[product] > 0:
            self.stock[product] -= 1
            self.delivered_products += 1
            return True
        return False

class SupplyChainSim:
    def __init__(self, task: str, seed: int = 42):
        self.task = task
        self.rng = random.Random(seed)
        self.factories = {i: Factory(i, self.rng) for i in range(1, 5)}
        self.distributors = {i: Distributor(i) for i in range(1, 5)}

        self.current_time = 0
        self.next_wholesaler_order_time = 192 * 3600 + self.rng.randint(600, 3600)

    def advance_time(self, new_time: int):
        # Event loop to process events in chronological order up to new_time
        while True:
            next_event_time = float('inf')
            event_type = None
            event_data = None

            # Check factories
            for f_id, f in self.factories.items():
                if f.next_production_time < next_event_time:
                    next_event_time = f.next_production_time
                    event_type = "factory"
                    event_data = f_id

            # Check wholesaler orders
            if self.next_wholesaler_order_time < next_event_time:
                next_event_time = self.next_wholesaler_order_time
                event_type = "wholesaler"

            # Check deliveries
            for d_id, d in self.distributors.items():
                for arr_time, prod, amt in d.incoming_deliveries:
                    if arr_time < next_event_time:
                        next_event_time = arr_time
                        event_type = "delivery"
                        event_data = (d_id, arr_time, prod, amt)

            if next_event_time > new_time:
                break

            self.current_time = next_event_time

            if event_type == "factory":
                f = self.factories[event_data]
                product = self.rng.choice(f.products)
                f.stock[product] += 1
                f.next_production_time += int(self.rng.expovariate(1/600))
            elif event_type == "wholesaler":
                dist_id = self.rng.randint(1, 4)
                # Pick a valid product for the chosen distributor based on assortments
                prod = self.rng.choice(list(TASK_A_B_MAPPING[dist_id].keys()))
                self.distributors[dist_id].fulfill_wholesaler_order(prod)
                self.next_wholesaler_order_time += self.rng.randint(600, 3600)
            elif event_type == "delivery":
                d_id, arr_time, prod, amt = event_data
                self.distributors[d_id].stock[prod] += amt
                self.distributors[d_id].incoming_deliveries.remove((arr_time, prod, amt))

        self.current_time = new_time

    def place_factory_order(self, dist_id: int, fac_id: int, product: int, amount: int, current_time: int) -> bool:
        if amount == 0:
            return True
        if self.factories[fac_id].stock.get(product, 0) >= amount:
            self.factories[fac_id].stock[product] -= amount
            lead_time_sec = int(SUPPLY_LEAD_TIMES[(dist_id, fac_id)] * 3600)
            self.distributors[dist_id].incoming_deliveries.append((current_time + lead_time_sec, product, amount))
            self.distributors[dist_id].total_cost += 10.0 # 10 euro per order
            return True
        return False

    def run(self, days: int = 30):
        # 1st day to 7th day: only production
        # 8th day 00:00 (168h): distributors order 10 of each
        self.advance_time(168 * 3600)

        for d_id in range(1, 5):
            # Only order products that are in the distributor's assortment
            for p in TASK_A_B_MAPPING[d_id]:
                # find factory mapping
                f_id = TASK_A_B_MAPPING[d_id][p]

                # Minimum supply time logic could apply but definition says "regardless of strategy"
                # actually definition says: "regardless of the ordering strategy used ... order 10 pieces ... to fill their storages"
                # From table 3 or minimal? Let's use minimal for task c if requested, but table 3 is standard.
                if self.task == "c":
                    # Task c orders initial 10 from minimal time
                    best_f = None
                    min_time = float("inf")
                    for cand_f in range(1, 5):
                        if p in self.factories[cand_f].products:
                            if SUPPLY_LEAD_TIMES[(d_id, cand_f)] < min_time:
                                min_time = SUPPLY_LEAD_TIMES[(d_id, cand_f)]
                                best_f = cand_f
                    f_id = best_f

                # Force order? Definition says "If an order cannot be fulfilled, it is postponed"
                # We will add it to backlog if it can't be fulfilled.
                success = self.place_factory_order(d_id, f_id, p, 10, self.current_time)
                if not success:
                    self.distributors[d_id].backlogged_orders.append((p, 10, f_id))

        d1_stock_history = []
        d1_stock_history.append((self.current_time, dict(self.distributors[1].stock)))

        # Advance day by day
        for day in range(8, days + 1): # 8th day has already started (orders placed), next order is at 9th day 00:00
            target_time = day * 24 * 3600
            self.advance_time(target_time)

            # calculate storage cost
            for d in self.distributors.values():
                d.calculate_storage_cost()

            # Process backlog from previous days
            for d_id, dist in self.distributors.items():
                new_backlog = []
                for p, amt, f_id in dist.backlogged_orders:
                    success = False
                    if self.task == "c":
                        # Try factories in order of min time
                        cands = []
                        for cand_f in range(1, 5):
                            if p in self.factories[cand_f].products:
                                cands.append((SUPPLY_LEAD_TIMES[(d_id, cand_f)], cand_f))
                        cands.sort()
                        for _, cand_f in cands:
                            if self.place_factory_order(d_id, cand_f, p, amt, target_time):
                                success = True
                                break
                    else:
                        success = self.place_factory_order(d_id, f_id, p, amt, target_time)

                    if not success:
                        new_backlog.append((p, amt, f_id))
                dist.backlogged_orders = new_backlog

            # Place new orders at target_time (00:00 of the current day)
            for d_id, dist in self.distributors.items():
                if self.task == "a":
                    # order 2 of each product in the assortment
                    for p in TASK_A_B_MAPPING[d_id]:
                        f_id = TASK_A_B_MAPPING[d_id][p]
                        if not self.place_factory_order(d_id, f_id, p, 2, target_time):
                            dist.backlogged_orders.append((p, 2, f_id))
                elif self.task == "b":
                    # order whatever wholesalers demanded yesterday
                    for p in TASK_A_B_MAPPING[d_id]:
                        amt = dist.wholesaler_demand[p]
                        if amt > 0:
                            f_id = TASK_A_B_MAPPING[d_id][p]
                            if not self.place_factory_order(d_id, f_id, p, amt, target_time):
                                dist.backlogged_orders.append((p, amt, f_id))
                    # reset demand
                    dist.wholesaler_demand = {p: 0 for p in range(1, 13)}
                elif self.task == "c":
                    # Same logic as B for amount, but minimal time strategy
                    for p in TASK_A_B_MAPPING[d_id]:
                        amt = dist.wholesaler_demand[p]
                        if amt > 0:
                            cands = []
                            for cand_f in range(1, 5):
                                if p in self.factories[cand_f].products:
                                    cands.append((SUPPLY_LEAD_TIMES[(d_id, cand_f)], cand_f))
                            cands.sort()
                            success = False
                            for _, cand_f in cands:
                                if self.place_factory_order(d_id, cand_f, p, amt, target_time):
                                    success = True
                                    break
                            if not success:
                                dist.backlogged_orders.append((p, amt, cands[0][1])) # store preferred for retry
                    dist.wholesaler_demand = {p: 0 for p in range(1, 13)}

            d1_stock_history.append((target_time, dict(self.distributors[1].stock)))

        return d1_stock_history

def c14_task_a1(seed: int = 42) -> list[tuple[int, dict[int, int]]]:
    """Task a1: Simulate the system once for 30 days and show stock of D1 over time."""
    sim = SupplyChainSim("a", seed=seed)
    return sim.run(30)


def c14_task_a2(seed: int = 42, runs: int = 100) -> dict[str, dict[str, float]]:
    """Task a2: Perform 100 simulation runs, calculate metrics for D1."""
    rng = random.Random(seed)
    costs, delivered, relative_costs = [], [], []
    for _ in range(runs):
        sim = SupplyChainSim("a", seed=rng.randint(0, 1000000))
        sim.run(30)
        d1 = sim.distributors[1]
        costs.append(d1.total_cost)
        delivered.append(d1.delivered_products)
        if d1.delivered_products > 0:
            relative_costs.append(d1.total_cost / d1.delivered_products)
        else:
            relative_costs.append(float('inf'))

    def stats(data):
        import statistics
        valid = [d for d in data if d != float('inf')]
        if not valid:
            return {"max": 0.0, "min": 0.0, "mean": 0.0, "dev": 0.0}
        return {
            "max": max(valid),
            "min": min(valid),
            "mean": sum(valid) / len(valid),
            "dev": statistics.stdev(valid) if len(valid) > 1 else 0.0
        }

    return {
        "C": stats(costs),
        "N": stats(delivered),
        "R": stats(relative_costs)
    }


def c14_task_b1(seed: int = 42) -> list[tuple[int, dict[int, int]]]:
    """Task b1: Simulate the system once for 30 days and show stock of D1 over time."""
    sim = SupplyChainSim("b", seed=seed)
    return sim.run(30)


def c14_task_b2(seed: int = 42, runs: int = 100) -> dict[str, dict[str, float]]:
    """Task b2: Perform 100 simulation runs, calculate metrics for D1."""
    rng = random.Random(seed)
    costs, delivered, relative_costs = [], [], []
    for _ in range(runs):
        sim = SupplyChainSim("b", seed=rng.randint(0, 1000000))
        sim.run(30)
        d1 = sim.distributors[1]
        costs.append(d1.total_cost)
        delivered.append(d1.delivered_products)
        if d1.delivered_products > 0:
            relative_costs.append(d1.total_cost / d1.delivered_products)
        else:
            relative_costs.append(float('inf'))

    def stats(data):
        import statistics
        valid = [d for d in data if d != float('inf')]
        if not valid:
            return {"max": 0.0, "min": 0.0, "mean": 0.0, "dev": 0.0}
        return {
            "max": max(valid),
            "min": min(valid),
            "mean": sum(valid) / len(valid),
            "dev": statistics.stdev(valid) if len(valid) > 1 else 0.0
        }

    return {
        "C": stats(costs),
        "N": stats(delivered),
        "R": stats(relative_costs)
    }


def c14_task_c1(seed: int = 42, runs: int = 100) -> dict[str, dict[str, float]]:
    """Task c1: Perform 100 simulation runs, calculate metrics for D1."""
    rng = random.Random(seed)
    costs, delivered, relative_costs = [], [], []
    for _ in range(runs):
        sim = SupplyChainSim("c", seed=rng.randint(0, 1000000))
        sim.run(30)
        d1 = sim.distributors[1]
        costs.append(d1.total_cost)
        delivered.append(d1.delivered_products)
        if d1.delivered_products > 0:
            relative_costs.append(d1.total_cost / d1.delivered_products)
        else:
            relative_costs.append(float('inf'))

    def stats(data):
        import statistics
        valid = [d for d in data if d != float('inf')]
        if not valid:
            return {"max": 0.0, "min": 0.0, "mean": 0.0, "dev": 0.0}
        return {
            "max": max(valid),
            "min": min(valid),
            "mean": sum(valid) / len(valid),
            "dev": statistics.stdev(valid) if len(valid) > 1 else 0.0
        }

    return {
        "C": stats(costs),
        "N": stats(delivered),
        "R": stats(relative_costs)
    }


def c14_task_c2(seed: int = 42, runs: int = 100) -> dict[str, dict[str, dict[str, float]]]:
    """Task c2: Compute comparative table for D1 for all three strategies."""
    return {
        "Strategy A": c14_task_a2(seed, runs),
        "Strategy B": c14_task_b2(seed, runs),
        "Strategy C": c14_task_c1(seed, runs),
    }
