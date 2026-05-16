"""State versioning for pso_logistics module (BUG-03 compliant)."""
from __future__ import annotations

STATE_VERSION = "1.0.0"


def default_state() -> dict:
    """Return a default serializable state dict."""
    return {
        "_state_version": STATE_VERSION,
        # Problem settings
        "n_customers": 10,
        "coord_range": 100.0,
        "data_seed": 42,
        # PSO
        "n_particles": 30,
        "n_iterations": 100,
        "w": 0.5,
        "c1": 1.5,
        "c2": 1.5,
        "n_ops_max": 3,
        "topology": "star",
        "pso_seed": 42,
        # Display
        "step_delay_ms": 50,
        "show_all_particles": False,
        "replay_speed_ms": 200,
        "active_tab": 0,
        "road_mode": False,
        # VRP settings (v1.1)
        "problem_type": "tsp",
        "n_vehicles": 3,
        "vehicle_capacity": 50.0,
        "demand_seed": 7,
        "max_demand": 15.0,
        # VRPTW settings (v1.2)
        "vehicle_speed": 1.0,
        "tw_seed": 13,
        "tw_width": 30.0,
        "service_time_max": 5.0,
        "tw_penalty": 10.0,
        # Last result (None if not yet run)
        "last_gbest_fitness": None,
        "last_gbest_perm": None,
        "last_convergence": [],
        "last_n_iterations": None,
    }
