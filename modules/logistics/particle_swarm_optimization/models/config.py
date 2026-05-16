"""PSO configuration dataclass — all tunable parameters in one place."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PSOConfig:
    """All tunable PSO parameters.

    Attributes:
        n_particles   : number of particles in the swarm
        n_dimensions  : dimensionality of the search space
        n_iterations  : maximum number of iterations
        lower_bound   : uniform lower bound for all dimensions
        upper_bound   : uniform upper bound for all dimensions
        w_start       : initial inertia weight
        w_end         : final inertia weight (linear decay)
        c1            : cognitive (personal best) acceleration coefficient
        c2            : social (global/local best) acceleration coefficient
        v_max_ratio   : Vmax = v_max_ratio × (upper_bound - lower_bound)
        topology      : 'star' (global best) or 'ring' (ring neighborhood)
        boundary      : 'clip' (clamp) or 'reflect' (mirror + flip velocity)
        seed          : random seed for reproducibility (None = random)
        objective     : function key, e.g. 'sphere' or 'ackley'
    """

    n_particles: int = 30
    n_dimensions: int = 2
    n_iterations: int = 100
    lower_bound: float = -5.12
    upper_bound: float = 5.12
    w_start: float = 0.9
    w_end: float = 0.4
    c1: float = 1.5
    c2: float = 1.5
    v_max_ratio: float = 0.20   # Vmax = ratio × (ub − lb)
    topology: str = "star"      # "star" | "ring"
    boundary: str = "clip"      # "clip" | "reflect"
    seed: int | None = None
    objective: str = "sphere"
    step_delay_ms: int = 0      # ms sleep between iterations (0 = max speed)

    @property
    def v_max(self) -> float:
        """Computed maximum velocity per dimension."""
        return self.v_max_ratio * (self.upper_bound - self.lower_bound)
