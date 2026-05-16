"""VRP (Capacitated Vehicle Routing Problem) instance and generator.

Encoding strategy — Giant Tour + Greedy Split:
    The PSO operates on a permutation of all customer indices (same search
    space as TSP).  The decoder splits this "giant tour" into vehicle routes
    by greedily assigning customers until the vehicle's capacity is exceeded,
    then starting a new route.  This lets the identical DiscreteSwarm /
    DiscreteParticle machinery handle VRP without any changes.

Penalty for excess vehicles:
    If the decoder needs more routes than n_vehicles, each extra route adds
    a fixed penalty equal to (n_customers × max_dist_in_matrix) to the
    fitness.  This strongly discourages infeasible solutions while still
    allowing the swarm to explore them temporarily.
"""
from __future__ import annotations

import random

import numpy as np

from modules.logistics.pso_logistics.core.route_evaluator import (
    build_distance_matrix,
    vrp_route_distance,
    vrp_total_distance,
)
from modules.logistics.pso_logistics.models.entities import (
    Customer,
    Depot,
    Route,
)


class VRPProblem:
    """Capacitated VRP instance.

    Attributes
    ----------
    depot            : Depot at (coord_range/2, coord_range/2)
    customers        : list of Customer with .demand assigned
    n_customers      : number of customers
    dist_matrix      : (n+1)×(n+1) Euclidean distance matrix
    n_vehicles       : maximum vehicles allowed
    vehicle_capacity : maximum load per vehicle
    """

    def __init__(
        self,
        depot: Depot,
        customers: list[Customer],
        dist_matrix: np.ndarray,
        n_vehicles: int,
        vehicle_capacity: float,
    ) -> None:
        self.depot = depot
        self.customers = customers
        self.n_customers = len(customers)
        self.dist_matrix = dist_matrix
        self.n_vehicles = n_vehicles
        self.vehicle_capacity = vehicle_capacity
        # Precompute penalty scale (set once, used every evaluate() call)
        self._penalty_per_extra = (
            float(dist_matrix.max()) * self.n_customers
        )

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
    ) -> "VRPProblem":
        """Generate a random CVRP instance.

        Customer *demands* are drawn from U[1, max_demand] using demand_seed,
        independently from spatial layout (data_seed).  This ensures changing
        the demand seed does not shuffle customer positions.

        A safety check ensures the total demand does not exceed
        n_vehicles × vehicle_capacity.  If it does, vehicle_capacity is
        silently raised to ceil(total_demand / n_vehicles) to guarantee
        feasibility.
        """
        # --- spatial layout (same logic as TSPProblem._generate_euclidean) ---
        rng_data = random.Random(data_seed)
        depot = Depot(id=0, x=coord_range / 2.0, y=coord_range / 2.0)
        customers = [
            Customer(
                id=i + 1,
                x=rng_data.uniform(0, coord_range),
                y=rng_data.uniform(0, coord_range),
            )
            for i in range(n_customers)
        ]

        # --- assign demands ---
        rng_dem = random.Random(demand_seed)
        for c in customers:
            c.demand = round(rng_dem.uniform(1.0, max_demand), 1)

        # --- feasibility guard ---
        total_demand = sum(c.demand for c in customers)
        min_capacity = total_demand / n_vehicles
        if vehicle_capacity < min_capacity:
            vehicle_capacity = float(np.ceil(min_capacity))

        coords = [(c.x, c.y) for c in customers]
        dist_matrix = build_distance_matrix((depot.x, depot.y), coords)
        return cls(depot, customers, dist_matrix, n_vehicles, vehicle_capacity)

    # ------------------------------------------------------------------
    # Core decoder
    # ------------------------------------------------------------------

    def decode_giant_tour(self, perm: list[int]) -> list[list[int]]:
        """Split a giant-tour permutation into vehicle routes by capacity.

        Greedy sequential split:
            Traverse customers in perm order.  Add to current route if
            cumulative demand ≤ vehicle_capacity; otherwise start new route.

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
    # PSO interface (same protocol as TSPProblem)
    # ------------------------------------------------------------------

    def evaluate(self, perm: list[int]) -> float:
        """Fitness = total distance + penalty per vehicle over n_vehicles.

        A giant-tour permutation that can be served by ≤ n_vehicles has no
        penalty.  Each extra vehicle needed adds _penalty_per_extra to the
        fitness, heavily discouraging infeasible solutions.
        """
        routes = self.decode_giant_tour(perm)
        total = vrp_total_distance(routes, self.dist_matrix)
        n_extra = max(0, len(routes) - self.n_vehicles)
        return total + n_extra * self._penalty_per_extra

    def initial_position(self, rng: random.Random) -> list[int]:
        """Random permutation of customer indices."""
        perm = list(range(self.n_customers))
        rng.shuffle(perm)
        return perm

    # ------------------------------------------------------------------
    # Decode to Route objects (for result display)
    # ------------------------------------------------------------------

    def decode_routes(self, perm: list[int]) -> list[Route]:
        """Decode perm → list[Route] with distance and load filled in."""
        routes: list[Route] = []
        for v_idx, customer_indices in enumerate(self.decode_giant_tour(perm)):
            dist = vrp_route_distance(customer_indices, self.dist_matrix)
            load = sum(self.customers[i].demand for i in customer_indices)
            routes.append(
                Route(
                    vehicle_id=v_idx + 1,
                    customer_ids=[self.customers[i].id for i in customer_indices],
                    distance=dist,
                    load=load,
                )
            )
        return routes

    def decode_route_ids(self, perm: list[int]) -> list[list[int]]:
        """Convenience: returns list-of-lists of customer IDs per vehicle."""
        return [r.customer_ids for r in self.decode_routes(perm)]
