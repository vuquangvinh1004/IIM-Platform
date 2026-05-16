"""State schema for PSO module session persistence.

The state dict is versioned so that StateManager can detect schema changes
and call migrate_state() if needed (BUG-03 resolution).
"""
from __future__ import annotations

from typing import Any

STATE_VERSION = "1.0.0"


def default_state() -> dict[str, Any]:
    """Return a fresh default state dict with _state_version injected."""
    return {
        "_state_version": STATE_VERSION,
        # Config params
        "objective": "sphere",
        "n_dimensions": 2,
        "lower_bound": -5.12,
        "upper_bound": 5.12,
        "n_particles": 30,
        "n_iterations": 100,
        "w_start": 0.9,
        "w_end": 0.4,
        "c1": 1.5,
        "c2": 1.5,
        "v_max_ratio": 0.20,
        "topology": "star",
        "boundary": "clip",
        "seed": 42,
        # Last result
        "last_gbest_fitness": None,
        "last_gbest_position": None,
        "last_convergence": [],
        "active_tab": 0,
    }
