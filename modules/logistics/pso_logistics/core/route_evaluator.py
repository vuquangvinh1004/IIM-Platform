"""Route distance utilities for PSO logistics problems.

build_distance_matrix  — Euclidean (n+1)×(n+1) matrix (index 0 = depot)
tsp_tour_distance      — total round-trip length for a permutation
vrp_route_distance     — single vehicle round-trip (depot→customers→depot)
vrp_total_distance     — sum of distances across all vehicle routes
"""
from __future__ import annotations

import math

import numpy as np


def build_distance_matrix(
    depot_xy: tuple[float, float],
    customers_xy: list[tuple[float, float]],
) -> np.ndarray:
    """Build a symmetric Euclidean distance matrix.

    Index 0  → depot
    Index i+1 → customers_xy[i]

    Returns an ndarray of shape (n+1, n+1) where n = len(customers_xy).
    """
    points = [depot_xy] + list(customers_xy)
    n = len(points)
    dist = np.zeros((n, n), dtype=np.float64)
    for i in range(n):
        for j in range(i + 1, n):
            d = math.hypot(
                points[i][0] - points[j][0],
                points[i][1] - points[j][1],
            )
            dist[i, j] = d
            dist[j, i] = d
    return dist


def tsp_tour_distance(perm: list[int], dist_matrix: np.ndarray) -> float:
    """Compute the total round-trip distance for a TSP permutation.

    perm        : 0-based customer indices (perm[k] is the k-th customer
                  visited; index into dist_matrix is perm[k]+1).
    dist_matrix : (n_customers+1) × (n_customers+1); row/col 0 = depot.

    Tour: depot → perm[0]+1 → perm[1]+1 → … → perm[-1]+1 → depot.
    Returns 0.0 for an empty permutation.
    """
    if not perm:
        return 0.0
    total: float = float(dist_matrix[0, perm[0] + 1])
    for k in range(len(perm) - 1):
        total += float(dist_matrix[perm[k] + 1, perm[k + 1] + 1])
    total += float(dist_matrix[perm[-1] + 1, 0])
    return total


def vrp_route_distance(
    route_customer_indices: list[int],
    dist_matrix: np.ndarray,
) -> float:
    """Distance for one vehicle route: depot → customers → depot.

    route_customer_indices : 0-based customer indices for this vehicle's route.
    dist_matrix            : (n_customers+1)×(n_customers+1); row/col 0 = depot.

    Returns 0.0 for an empty route.
    """
    if not route_customer_indices:
        return 0.0
    total: float = float(dist_matrix[0, route_customer_indices[0] + 1])
    for k in range(len(route_customer_indices) - 1):
        a = route_customer_indices[k] + 1
        b = route_customer_indices[k + 1] + 1
        total += float(dist_matrix[a, b])
    total += float(dist_matrix[route_customer_indices[-1] + 1, 0])
    return total


def vrp_total_distance(
    routes: list[list[int]],
    dist_matrix: np.ndarray,
) -> float:
    """Sum of vrp_route_distance across all vehicle routes."""
    return sum(vrp_route_distance(r, dist_matrix) for r in routes)


# ── VRPTW (v1.2) ──────────────────────────────────────────────────────────────

def vrptw_route_cost(
    route_customer_indices: list[int],
    dist_matrix: np.ndarray,
    customers: list,          # list[Customer] with .service_time, .ready_time, .due_time
    speed: float,
) -> tuple[float, float]:
    """Compute (route_distance, total_lateness) for one VRPTW vehicle route.

    Soft time windows: arrival after due_time accumulates lateness (penalty
    applied by caller) but does NOT reject the route.  This keeps the PSO
    search space connected during early exploration.

    Time model:
        travel_time(a→b)  = dist_matrix[a,b] / speed
        arrival_time[0]   = travel_time(depot→c0)
        start_service[k]  = max(arrival_time[k], ready_time[k])   # wait if early
        lateness[k]       = max(0, arrival_time[k] - due_time[k]) # soft violation
        departure[k]      = start_service[k] + service_time[k]
        arrival_time[k+1] = departure[k] + travel_time(c_k → c_{k+1})

    Returns (0.0, 0.0) for an empty route.
    """
    if not route_customer_indices:
        return 0.0, 0.0

    effective_speed = max(speed, 1e-9)
    total_distance: float = 0.0
    total_lateness: float = 0.0

    # depot → first customer
    first_dm_idx = route_customer_indices[0] + 1
    d0 = float(dist_matrix[0, first_dm_idx])
    total_distance += d0
    arrival = d0 / effective_speed

    c0 = customers[route_customer_indices[0]]
    total_lateness += max(0.0, arrival - c0.due_time)
    current_time = max(arrival, c0.ready_time) + c0.service_time

    # subsequent customers
    for k in range(1, len(route_customer_indices)):
        a = route_customer_indices[k - 1] + 1
        b = route_customer_indices[k] + 1
        d = float(dist_matrix[a, b])
        total_distance += d
        arrival = current_time + d / effective_speed

        ck = customers[route_customer_indices[k]]
        total_lateness += max(0.0, arrival - ck.due_time)
        current_time = max(arrival, ck.ready_time) + ck.service_time

    # return to depot
    last_dm_idx = route_customer_indices[-1] + 1
    total_distance += float(dist_matrix[last_dm_idx, 0])

    return total_distance, total_lateness


def vrptw_total_cost(
    routes: list[list[int]],
    dist_matrix: np.ndarray,
    customers: list,
    speed: float,
) -> tuple[float, float]:
    """Sum of vrptw_route_cost across all routes.

    Returns (total_distance, total_lateness).
    """
    total_dist: float = 0.0
    total_late: float = 0.0
    for r in routes:
        d, l = vrptw_route_cost(r, dist_matrix, customers, speed)
        total_dist += d
        total_late += l
    return total_dist, total_late
