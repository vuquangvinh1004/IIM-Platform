"""state.py — State versioning cho pso_logistics_map (chuẩn IIMP)."""
from __future__ import annotations

STATE_VERSION = "1.1.0"


def default_state() -> dict:
    """Trả về dict state mặc định có thể serialize JSON."""
    return {
        "_state_version": STATE_VERSION,
        # Map
        "bbox_name": "hcm_q1",
        "pbf_file": "assets/pbf/hcm_q1.pbf",
        "network_type": "driving",
        # Bài toán
        "problem_type": "tsp",
        "n_customers": 10,
        "n_vehicles": 3,
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
        # VRP
        "vehicle_capacity": 50.0,
        "demand_seed": 7,
        "max_demand": 15.0,
        # VRPTW
        "vehicle_speed_kmph": 30.0,
        "tw_seed": 13,
        "tw_width_s": 1800.0,
        "service_time_max_s": 300.0,
        "tw_penalty": 10.0,
        "overload_penalty": 1000.0,
        # Display
        "step_delay_ms": 50,
        "replay_speed_ms": 200,
        "active_tab": 0,
    }
