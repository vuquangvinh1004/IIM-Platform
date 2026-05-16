"""VRP (Capacitated Vehicle Routing Problem) trên ma trận khoảng cách thực.

Encoding strategy — Giant Tour + Greedy Split:
    PSO operates on a permutation of 0-based customer indices (same search
    space as TSP).  The decoder splits this "giant tour" into vehicle routes
    by greedily assigning customers until the vehicle's capacity is exceeded,
    then starting a new route.

Penalty for excess vehicles:
    If the decoder needs more routes than n_vehicles, each extra route adds
    _penalty_per_extra = max_finite_dist × n_customers to the fitness.
    This strongly discourages infeasible solutions while still allowing the
    swarm to explore them temporarily.
"""
from __future__ import annotations

import random

import numpy as np


# ── Internal route distance helper ───────────────────────────────────────────

def _route_distance(route_indices: list[int], dist_matrix: np.ndarray) -> float:
    """depot → customers → depot round-trip distance (metres)."""
    if not route_indices:
        return 0.0
    total = float(dist_matrix[0, route_indices[0] + 1])
    for k in range(len(route_indices) - 1):
        total += float(dist_matrix[route_indices[k] + 1, route_indices[k + 1] + 1])
    total += float(dist_matrix[route_indices[-1] + 1, 0])
    return total


class VRPProblem:
    """Capacitated VRP instance on a real-road distance matrix.

    Parameters
    ----------
    dist_matrix      : (n_customers+1) × (n_customers+1) matrix, metres.
                       Index 0 = depot; index k+1 = customer k (0-based).
    n_customers      : number of customers.
    n_vehicles       : maximum vehicles allowed (soft constraint via penalty).
    demands          : array of shape (n_customers,) — cargo demand per customer.
    vehicle_capacity : max cargo per vehicle.
    overload_penalty : reserved (kept for API parity with VRPTW).
    """

    def __init__(
        self,
        dist_matrix: np.ndarray,
        n_customers: int,
        n_vehicles: int,
        demands: np.ndarray,
        vehicle_capacity: float,
        overload_penalty: float = 1000.0,  # noqa: ARG002 — API parity
    ) -> None:
        if len(demands) != n_customers:
            raise ValueError(
                f"demands length {len(demands)} != n_customers {n_customers}"
            )
        if n_vehicles < 1:
            raise ValueError("n_vehicles must be ≥ 1")
        if vehicle_capacity <= 0:
            raise ValueError("vehicle_capacity must be > 0")
        self.dist_matrix = dist_matrix
        self.n_customers = n_customers
        self.n_vehicles = n_vehicles
        self.demands = np.asarray(demands, dtype=np.float64)
        self.vehicle_capacity = float(vehicle_capacity)
        finite = dist_matrix[np.isfinite(dist_matrix)]
        self._penalty_per_extra = float(finite.max()) * n_customers if len(finite) > 0 else 1e9

    # ── Giant-tour decoder ─────────────────────────────────────────────────

    def decode_giant_tour(self, perm: list[int]) -> list[list[int]]:
        """Split a giant-tour permutation into vehicle routes by capacity.

        Greedy sequential split: add customer to current route if cumulative
        demand ≤ vehicle_capacity; otherwise start a new route.

        Returns a list of routes (each is a list of 0-based customer indices).
        Always returns at least one route.
        """
        routes: list[list[int]] = []
        current: list[int] = []
        current_load: float = 0.0

        for idx in perm:
            d = float(self.demands[idx])
            if current and current_load + d > self.vehicle_capacity:
                routes.append(current)
                current = [idx]
                current_load = d
            else:
                current.append(idx)
                current_load += d

        if current:
            routes.append(current)
        return routes

    # ── PSO interface ──────────────────────────────────────────────────────

    def evaluate(self, perm: list[int]) -> float:
        """Fitness = total_distance + penalty_per_extra × n_extra_vehicles."""
        routes = self.decode_giant_tour(perm)
        total = sum(_route_distance(r, self.dist_matrix) for r in routes)
        n_extra = max(0, len(routes) - self.n_vehicles)
        return total + n_extra * self._penalty_per_extra

    def initial_position(self, rng: random.Random) -> list[int]:
        """Random permutation of customer indices (0-based)."""
        perm = list(range(self.n_customers))
        rng.shuffle(perm)
        return perm

    # ── Route decoding for display ─────────────────────────────────────────

    def decode_routes(self, perm: list[int]) -> list[dict]:
        """Decode perm → list of route dicts for result display.

        Each dict keys: ``vehicle_id`` (1-based int), ``customer_indices``
        (list of 0-based), ``distance`` (metres float), ``load`` (demand units float).
        """
        result = []
        for v_idx, route_idxs in enumerate(self.decode_giant_tour(perm)):
            dist = _route_distance(route_idxs, self.dist_matrix)
            load = float(np.sum(self.demands[route_idxs]))
            result.append(
                {
                    "vehicle_id": v_idx + 1,
                    "customer_indices": route_idxs,
                    "distance": dist,
                    "load": load,
                }
            )
        return result
