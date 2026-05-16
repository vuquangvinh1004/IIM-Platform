"""VRPTW (Vehicle Routing Problem with Time Windows) trên ma trận khoảng cách thực.

Encoding: Giant-tour + greedy-split (capacity only) — giống VRPProblem.
Time windows là SOFT: đến muộn tích luỹ penalty nhưng không từ chối route.

Fitness = total_distance
        + n_extra_vehicles × penalty_per_extra
        + tw_penalty × total_lateness_seconds

Time model (distance in metres, speed in m/s):
    travel_time(a→b)  = dist_matrix[a,b] / speed_mps
    arrival[0]        = travel_time(depot → c0)
    start_service[k]  = max(arrival[k], ready_time[k])  # wait if early
    lateness[k]       = max(0, arrival[k] − due_time[k])  # soft TW violation
    departure[k]      = start_service[k] + service_time[k]
    arrival[k+1]      = departure[k] + travel_time(c_k → c_{k+1})
"""
from __future__ import annotations

import random

import numpy as np


# ── Internal route cost helper ─────────────────────────────────────────────

def _route_cost(
    route_indices: list[int],
    dist_matrix: np.ndarray,
    speed_mps: float,
    time_windows: np.ndarray,  # shape (n_customers, 2): (ready_s, due_s)
    service_times: np.ndarray,  # shape (n_customers,) in seconds
) -> tuple[float, float]:
    """Return (distance_metres, total_lateness_seconds) for one vehicle route."""
    if not route_indices:
        return 0.0, 0.0

    eff_speed = max(speed_mps, 1e-9)
    total_dist = 0.0
    total_late = 0.0

    # depot → first customer
    first_dm = route_indices[0] + 1
    d0 = float(dist_matrix[0, first_dm])
    total_dist += d0
    arrival = d0 / eff_speed

    c0 = route_indices[0]
    total_late += max(0.0, arrival - float(time_windows[c0, 1]))
    current_time = max(arrival, float(time_windows[c0, 0])) + float(service_times[c0])

    # subsequent customers
    for k in range(1, len(route_indices)):
        prev_dm = route_indices[k - 1] + 1
        curr_dm = route_indices[k] + 1
        d = float(dist_matrix[prev_dm, curr_dm])
        total_dist += d
        arrival = current_time + d / eff_speed
        ck = route_indices[k]
        total_late += max(0.0, arrival - float(time_windows[ck, 1]))
        current_time = max(arrival, float(time_windows[ck, 0])) + float(service_times[ck])

    # return to depot
    total_dist += float(dist_matrix[route_indices[-1] + 1, 0])
    return total_dist, total_late


class VRPTWProblem:
    """VRPTW instance (PSO-compatible — same interface as VRPProblem).

    Parameters
    ----------
    dist_matrix       : (n_customers+1) × (n_customers+1) matrix, metres.
                        Index 0 = depot; index k+1 = customer k (0-based).
    n_customers       : number of customers.
    n_vehicles        : maximum vehicles allowed without penalty.
    demands           : array (n_customers,) — cargo demands.
    vehicle_capacity  : max cargo per vehicle.
    vehicle_speed_mps : vehicle speed in metres/second.
    time_windows      : array (n_customers, 2) — (ready_time_s, due_time_s).
    service_times     : array (n_customers,) — service duration in seconds.
    tw_penalty        : penalty per second of lateness.
    overload_penalty  : reserved (API parity with VRPProblem).
    """

    def __init__(
        self,
        dist_matrix: np.ndarray,
        n_customers: int,
        n_vehicles: int,
        demands: np.ndarray,
        vehicle_capacity: float,
        vehicle_speed_mps: float,
        time_windows: np.ndarray,
        service_times: np.ndarray,
        tw_penalty: float = 10.0,
        overload_penalty: float = 1000.0,  # noqa: ARG002 — API parity
    ) -> None:
        if len(demands) != n_customers:
            raise ValueError(
                f"demands length {len(demands)} != n_customers {n_customers}"
            )
        if time_windows.shape != (n_customers, 2):
            raise ValueError(
                f"time_windows shape {time_windows.shape} != ({n_customers}, 2)"
            )
        if len(service_times) != n_customers:
            raise ValueError(
                f"service_times length {len(service_times)} != n_customers {n_customers}"
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
        self.vehicle_speed_mps = max(float(vehicle_speed_mps), 1e-9)
        self.time_windows = np.asarray(time_windows, dtype=np.float64)
        self.service_times = np.asarray(service_times, dtype=np.float64)
        self.tw_penalty = float(tw_penalty)
        finite = dist_matrix[np.isfinite(dist_matrix)]
        self._penalty_per_extra = float(finite.max()) * n_customers if len(finite) > 0 else 1e9

    # ── Giant-tour decoder ─────────────────────────────────────────────────

    def decode_giant_tour(self, perm: list[int]) -> list[list[int]]:
        """Split by capacity only (TW are soft — evaluated in fitness, not used
        to force splits).  Same logic as VRPProblem.decode_giant_tour."""
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
        """Fitness = total_distance + excess_vehicle_penalty + tw_lateness_penalty."""
        routes = self.decode_giant_tour(perm)
        total_dist = 0.0
        total_late = 0.0
        for r in routes:
            d, l = _route_cost(
                r, self.dist_matrix, self.vehicle_speed_mps,
                self.time_windows, self.service_times,
            )
            total_dist += d
            total_late += l
        n_extra = max(0, len(routes) - self.n_vehicles)
        return total_dist + n_extra * self._penalty_per_extra + self.tw_penalty * total_late

    def initial_position(self, rng: random.Random) -> list[int]:
        """Random permutation of customer indices (0-based)."""
        perm = list(range(self.n_customers))
        rng.shuffle(perm)
        return perm

    # ── Route decoding for display ─────────────────────────────────────────

    def decode_routes(self, perm: list[int]) -> list[dict]:
        """Decode perm → list of route dicts for result display.

        Each dict keys: ``vehicle_id`` (1-based), ``customer_indices`` (0-based),
        ``distance`` (metres), ``load``, ``total_lateness_s`` (seconds).
        """
        result = []
        for v_idx, route_idxs in enumerate(self.decode_giant_tour(perm)):
            dist, late = _route_cost(
                route_idxs, self.dist_matrix, self.vehicle_speed_mps,
                self.time_windows, self.service_times,
            )
            load = float(np.sum(self.demands[route_idxs]))
            result.append(
                {
                    "vehicle_id": v_idx + 1,
                    "customer_indices": route_idxs,
                    "distance": dist,
                    "load": load,
                    "total_lateness_s": late,
                }
            )
        return result

    # ── Summary helpers ────────────────────────────────────────────────────

    def total_lateness(self, perm: list[int]) -> float:
        """Total lateness in seconds for the given permutation."""
        routes = self.decode_giant_tour(perm)
        return sum(
            _route_cost(r, self.dist_matrix, self.vehicle_speed_mps,
                        self.time_windows, self.service_times)[1]
            for r in routes
        )
