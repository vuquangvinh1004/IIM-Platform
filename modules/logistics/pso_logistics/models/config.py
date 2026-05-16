"""LogisticsPSOConfig — all tunable parameters for pso_logistics module."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LogisticsPSOConfig:
    """All tunable parameters for the PSO Logistics simulation.

    Problem generation
    ------------------
    n_customers   : number of customer nodes (TSP: all on one tour)
    coord_range   : customers placed in [0, coord_range] × [0, coord_range]
                    depot fixed at (coord_range/2, coord_range/2)
    data_seed     : seed for customer placement; same seed → same layout

    PSO parameters
    --------------
    n_particles   : swarm size
    n_iterations  : maximum iterations
    w             : inertia weight — controls fraction of random operators
    c1            : cognitive (personal best) acceleration coefficient
    c2            : social (global/local best) acceleration coefficient
    n_ops_max     : max number of operators per component per step
    topology      : "star" (global gbest) or "ring" (ring lbest)
    pso_seed      : seed for PSO random; None = non-deterministic

    Animation / display
    -------------------
    step_delay_ms : milliseconds to sleep between iterations (0 = max speed)
    """

    # ── Problem ──────────────────────────────────────────────────────────────
    n_customers: int = 10
    coord_range: float = 100.0
    data_seed: int = 42

    # ── PSO ──────────────────────────────────────────────────────────────────
    n_particles: int = 30
    n_iterations: int = 100
    w: float = 0.5
    c1: float = 1.5
    c2: float = 1.5
    n_ops_max: int = 3
    topology: str = "star"     # "star" | "ring"
    pso_seed: int | None = 42

    # ── Animation ────────────────────────────────────────────────────────────
    step_delay_ms: int = 50
    # ── Mode ──────────────────────────────────────────────────────────────
    road_mode: bool = False  # True = grid road network; False = Euclidean

    # ── Swarm dynamics ────────────────────────────────────────────────────────
    mutation_rate: float = 0.05   # probability each particle undergoes random swap after update (0 = disabled)

    # ── VRP (v1.1) ───────────────────────────────────────────────────────────
    problem_type: str = "tsp"       # "tsp" | "vrp" | "vrptw"
    n_vehicles: int = 3
    vehicle_capacity: float = 50.0
    demand_seed: int = 7
    max_demand: float = 15.0

    # ── VRPTW (v1.2) ─────────────────────────────────────────────────────────
    vehicle_speed: float = 1.0       # distance units per time unit
    tw_seed: int = 13                # seed for time window / service time generation
    tw_width: float = 30.0           # full width of each time window (ready±half, due+half)
    service_time_max: float = 5.0    # max service time per customer drawn from U[0, max]
    tw_penalty: float = 10.0         # fitness penalty per unit of lateness