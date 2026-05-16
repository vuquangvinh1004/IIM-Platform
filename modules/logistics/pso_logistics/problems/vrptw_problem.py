"""VRPTW (Vehicle Routing Problem with Time Windows) instance and generator.

Encoding strategy — Giant Tour + Greedy Split (same as VRP v1.1):
    The PSO operates on a permutation of all customer indices.  The decoder
    splits the giant tour into vehicle routes using both capacity AND time
    window considerations.

Soft time windows:
    Arriving after a customer's due_time is penalised (tw_penalty per unit
    of lateness) but NOT rejected.  This keeps the PSO search space connected
    during early exploration and avoids the "all solutions infeasible" trap.

Fitness:
    fitness = total_distance
            + n_extra_vehicles × penalty_per_extra
            + tw_penalty × total_lateness

Time model (per route):
    speed           = vehicle_speed (distance units per time unit)
    travel_time(a→b) = dist_matrix[a,b] / speed
    arrival_time[0]  = travel_time(depot → c0)
    start_service[k] = max(arrival_time[k], ready_time[k])
    lateness[k]      = max(0, arrival_time[k] - due_time[k])
    departure[k]     = start_service[k] + service_time[k]
    arrival_time[k+1]= departure[k] + travel_time(c_k → c_{k+1})
"""
from __future__ import annotations

import math
import random

import numpy as np

from modules.logistics.pso_logistics.core.route_evaluator import (
    build_distance_matrix,
    vrptw_route_cost,
    vrptw_total_cost,
)
from modules.logistics.pso_logistics.models.entities import (
    Customer,
    Depot,
    Route,
)


class VRPTWProblem:
    """VRPTW instance — PSO-compatible (same interface as VRPProblem).

    Attributes
    ----------
    depot            : Depot at (coord_range/2, coord_range/2)
    customers        : list[Customer] with demand, service_time, ready_time, due_time
    n_customers      : number of customers
    dist_matrix      : (n+1)×(n+1) Euclidean distance matrix (0 = depot)
    n_vehicles       : maximum vehicles allowed without penalty
    vehicle_capacity : max cargo per vehicle
    vehicle_speed    : distance per time unit
    tw_penalty       : penalty per unit of lateness (applied to fitness)
    """

    def __init__(
        self,
        depot: Depot,
        customers: list[Customer],
        dist_matrix: np.ndarray,
        n_vehicles: int,
        vehicle_capacity: float,
        vehicle_speed: float,
        tw_penalty: float,
    ) -> None:
        self.depot = depot
        self.customers = customers
        self.n_customers = len(customers)
        self.dist_matrix = dist_matrix
        self.n_vehicles = n_vehicles
        self.vehicle_capacity = vehicle_capacity
        self.vehicle_speed = max(vehicle_speed, 1e-9)
        self.tw_penalty = tw_penalty
        # Precompute penalty per extra vehicle (same scale as VRPProblem)
        self._penalty_per_extra = float(dist_matrix.max()) * self.n_customers

    # ------------------------------------------------------------------
    # Factory method
    # ------------------------------------------------------------------

    @classmethod
    def generate(
        cls,
        n_customers: int,
        coord_range: float,
        data_seed: int,
        demand_seed: int,
        n_vehicles: int,
        vehicle_capacity: float,
        max_demand: float = 15.0,
        vehicle_speed: float = 1.0,
        tw_seed: int = 13,
        tw_width: float = 30.0,
        service_time_max: float = 5.0,
        tw_penalty: float = 10.0,
    ) -> "VRPTWProblem":
        """Generate a random VRPTW instance.

        Spatial layout and demands are generated identically to VRPProblem so
        that the same data_seed / demand_seed produce the same map.  Time
        windows are generated separately via tw_seed so they can be varied
        independently.

        Time window generation:
            The "natural" visit time for customer i when departing from the
            depot is: departure_time = dist(depot, c_i) / speed.
            Each window is centred on departure_time ± (tw_width/2).
                ready_time[i] = max(0, natural_i - tw_width / 2)
                due_time[i]   = natural_i + tw_width / 2
            service_time[i] ∈ U[0, service_time_max] via tw_seed.

        Capacity feasibility guard same as VRPProblem.
        """
        # ── spatial layout ──────────────────────────────────────────────────
        rng_data = random.Random(data_seed)
        depot = Depot(id=0, x=coord_range / 2.0, y=coord_range / 2.0)
        customers: list[Customer] = [
            Customer(
                id=i + 1,
                x=rng_data.uniform(0, coord_range),
                y=rng_data.uniform(0, coord_range),
            )
            for i in range(n_customers)
        ]

        # ── demands (independent seed) ──────────────────────────────────────
        rng_dem = random.Random(demand_seed)
        for c in customers:
            c.demand = round(rng_dem.uniform(1.0, max_demand), 1)

        # ── feasibility guard ───────────────────────────────────────────────
        total_demand = sum(c.demand for c in customers)
        min_capacity = total_demand / n_vehicles
        if vehicle_capacity < min_capacity:
            vehicle_capacity = float(np.ceil(min_capacity))

        # ── distance matrix ─────────────────────────────────────────────────
        coords = [(c.x, c.y) for c in customers]
        dist_matrix = build_distance_matrix((depot.x, depot.y), coords)

        effective_speed = max(vehicle_speed, 1e-9)

        # ── time windows (tw_seed) ──────────────────────────────────────────
        rng_tw = random.Random(tw_seed)
        half = tw_width / 2.0
        for i, c in enumerate(customers):
            # natural travel time from depot to this customer
            natural = float(dist_matrix[0, i + 1]) / effective_speed
            c.ready_time = max(0.0, natural - half)
            c.due_time = natural + half
            c.service_time = round(rng_tw.uniform(0.0, service_time_max), 2)

        return cls(depot, customers, dist_matrix, n_vehicles, vehicle_capacity,
                   vehicle_speed, tw_penalty)

    # ------------------------------------------------------------------
    # Core decoder (capacity + time-window-aware greedy split)
    # ------------------------------------------------------------------

    def decode_giant_tour(self, perm: list[int]) -> list[list[int]]:
        """Split giant-tour perm into vehicle routes respecting capacity.

        Splitting criterion: capacity only (same as VRPProblem.decode_giant_tour).
        Time windows are SOFT — evaluated in fitness, not used to force splits.
        This preserves the same split behaviour baseline as VRP and allows the
        PSO to explore freely; TW compliance improves under penalty pressure.

        Returns a list of routes (each route is a list of 0-based customer
        indices).  The list always has at least one route.
        """
        routes: list[list[int]] = []
        current: list[int] = []
        current_load: float = 0.0

        for idx in perm:
            demand = self.customers[idx].demand
            if current and current_load + demand > self.vehicle_capacity:
                routes.append(current)
                current = [idx]
                current_load = demand
            else:
                current.append(idx)
                current_load += demand

        if current:
            routes.append(current)

        return routes

    # ------------------------------------------------------------------
    # PSO interface
    # ------------------------------------------------------------------

    def evaluate(self, perm: list[int]) -> float:
        """Fitness = total_distance + excess_vehicle_penalty + tw_lateness_penalty.

        Soft TW: all permutations yield a finite fitness to keep the search
        space fully connected.
        """
        routes = self.decode_giant_tour(perm)
        total_dist, total_late = vrptw_total_cost(
            routes, self.dist_matrix, self.customers, self.vehicle_speed
        )
        n_extra = max(0, len(routes) - self.n_vehicles)
        return (
            total_dist
            + n_extra * self._penalty_per_extra
            + self.tw_penalty * total_late
        )

    def initial_position(self, rng: random.Random) -> list[int]:
        """Random permutation of customer indices."""
        perm = list(range(self.n_customers))
        rng.shuffle(perm)
        return perm

    # ------------------------------------------------------------------
    # Decode to Route objects (for result display)
    # ------------------------------------------------------------------

    def decode_routes(self, perm: list[int]) -> list[Route]:
        """Decode perm → list[Route] with distance, load, and TW time fields."""
        routes: list[Route] = []
        for v_idx, cust_idxs in enumerate(self.decode_giant_tour(perm)):
            dist, lateness = vrptw_route_cost(
                cust_idxs, self.dist_matrix, self.customers, self.vehicle_speed
            )
            load = sum(self.customers[i].demand for i in cust_idxs)

            # Build detailed time arrays for display
            arrival_times: list[float] = []
            start_service_times: list[float] = []
            waiting_times: list[float] = []
            lateness_times: list[float] = []

            effective_speed = max(self.vehicle_speed, 1e-9)
            current_time: float = 0.0

            for k, ci in enumerate(cust_idxs):
                dm_idx = ci + 1
                if k == 0:
                    travel = float(self.dist_matrix[0, dm_idx]) / effective_speed
                else:
                    prev_dm = cust_idxs[k - 1] + 1
                    travel = float(self.dist_matrix[prev_dm, dm_idx]) / effective_speed

                arrival = current_time + travel
                c = self.customers[ci]
                start_svc = max(arrival, c.ready_time)
                wait = start_svc - arrival
                late = max(0.0, arrival - c.due_time)

                arrival_times.append(round(arrival, 4))
                start_service_times.append(round(start_svc, 4))
                waiting_times.append(round(wait, 4))
                lateness_times.append(round(late, 4))

                current_time = start_svc + c.service_time

            routes.append(
                Route(
                    vehicle_id=v_idx + 1,
                    customer_ids=[self.customers[i].id for i in cust_idxs],
                    distance=dist,
                    load=load,
                    arrival_times=arrival_times,
                    start_service_times=start_service_times,
                    waiting_times=waiting_times,
                    lateness_times=lateness_times,
                )
            )
        return routes

    def decode_route_ids(self, perm: list[int]) -> list[list[int]]:
        """Convenience: returns list-of-lists of customer IDs per vehicle."""
        return [r.customer_ids for r in self.decode_routes(perm)]

    # ------------------------------------------------------------------
    # Summary helpers
    # ------------------------------------------------------------------

    def total_lateness(self, perm: list[int]) -> float:
        """Return raw total lateness (sum of max(0, arrival-due_time)) for perm."""
        routes = self.decode_giant_tour(perm)
        _, total_late = vrptw_total_cost(
            routes, self.dist_matrix, self.customers, self.vehicle_speed
        )
        return total_late

    def on_time_ratio(self, perm: list[int]) -> float:
        """Fraction of customers served before their due_time (0.0 – 1.0)."""
        on_time = 0
        for route in self.decode_routes(perm):
            on_time += sum(1 for lt in route.lateness_times if lt == 0.0)
        return on_time / max(1, self.n_customers)
