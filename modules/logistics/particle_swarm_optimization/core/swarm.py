"""PSO Swarm — orchestrates particles through the iterative search process.

Design notes:
  - Topology 'star' : global best shared by all particles (fast convergence)
  - Topology 'ring' : each particle only references the best within its two
                      immediate neighbors (slower but more diverse exploration)
  - Inertia weight w: decays linearly from w_start to w_end over n_iterations
  - Vmax            : clamps velocity to [-Vmax, Vmax] per dimension
  - Boundary 'clip' : positions outside [lb, ub] are clamped to the boundary
  - Boundary 'reflect': positions outside [lb, ub] are reflected back; velocity
                        component is negated on the violated dimension
"""
from __future__ import annotations

from typing import Callable

import numpy as np

from modules.logistics.particle_swarm_optimization.core.objective_functions import (
    ObjectiveFunction,
)
from modules.logistics.particle_swarm_optimization.core.particle import Particle
from modules.logistics.particle_swarm_optimization.models.config import PSOConfig


class Swarm:
    """PSO swarm.

    Usage::

        config = PSOConfig(n_particles=30, n_dimensions=2, ...)
        obj    = Sphere()
        swarm  = Swarm(config, obj)
        result = swarm.run(on_iteration=my_callback)
    """

    def __init__(self, config: PSOConfig, obj_func: ObjectiveFunction) -> None:
        self._cfg = config
        self._func = obj_func
        self._iteration: int = 0

        rng = np.random.default_rng(config.seed)
        lb, ub = config.lower_bound, config.upper_bound
        v_max = config.v_max_ratio * (ub - lb)
        n = config.n_particles
        d = config.n_dimensions

        # ── Initialise positions and velocities ───────────────────────────────
        positions = rng.uniform(lb, ub, (n, d))
        velocities = rng.uniform(-v_max, v_max, (n, d))
        fitnesses = np.array([obj_func.evaluate(p) for p in positions])

        self._particles: list[Particle] = [
            Particle(positions[i], velocities[i], float(fitnesses[i]))
            for i in range(n)
        ]

        # ── Initialise global best ────────────────────────────────────────────
        best_idx = int(np.argmin(fitnesses))
        self._gbest_position: np.ndarray = positions[best_idx].copy()
        self._gbest_fitness: float = float(fitnesses[best_idx])

        # ── Ring topology: local best cache (updated each iteration) ──────────
        self._lbest_positions: list[np.ndarray] = [
            p.pbest_position.copy() for p in self._particles
        ]

        # ── History (iteration 0 = initial state) ─────────────────────────────
        self._convergence: list[float] = [self._gbest_fitness]
        self._positions_history: list[np.ndarray] = [positions.copy()]

        self._rng = rng
        self._v_max: float = v_max

    # ── Public read-only properties ───────────────────────────────────────────

    @property
    def gbest_position(self) -> np.ndarray:
        return self._gbest_position.copy()

    @property
    def gbest_fitness(self) -> float:
        return self._gbest_fitness

    @property
    def convergence_history(self) -> list[float]:
        return list(self._convergence)

    @property
    def positions_history(self) -> list[np.ndarray]:
        return list(self._positions_history)

    @property
    def iteration(self) -> int:
        return self._iteration

    @property
    def current_positions(self) -> np.ndarray:
        return np.array([p.position for p in self._particles])

    @property
    def current_fitnesses(self) -> np.ndarray:
        return np.array([p.fitness for p in self._particles])

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _w(self, t: int) -> float:
        """Linear inertia weight decay from w_start → w_end over n_iterations."""
        cfg = self._cfg
        if cfg.n_iterations <= 1:
            return cfg.w_end
        return cfg.w_start + (cfg.w_end - cfg.w_start) * t / (cfg.n_iterations - 1)

    def _apply_boundary(
        self, position: np.ndarray, velocity: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Apply boundary constraint. Returns (position, velocity)."""
        lb, ub = self._cfg.lower_bound, self._cfg.upper_bound
        if self._cfg.boundary == "clip":
            position = np.clip(position, lb, ub)
        elif self._cfg.boundary == "reflect":
            for i in range(len(position)):
                if position[i] < lb:
                    position[i] = 2.0 * lb - position[i]
                    velocity[i] = -velocity[i]
                    position[i] = max(lb, min(ub, position[i]))
                elif position[i] > ub:
                    position[i] = 2.0 * ub - position[i]
                    velocity[i] = -velocity[i]
                    position[i] = max(lb, min(ub, position[i]))
        return position, velocity

    def _update_lbest(self) -> None:
        """Refresh ring-topology local best cache (ring neighborhood radius = 1)."""
        n = len(self._particles)
        for i in range(n):
            neighbors = [(i - 1) % n, i, (i + 1) % n]
            best_f = float("inf")
            best_p = self._particles[i].pbest_position
            for j in neighbors:
                f = self._particles[j].pbest_fitness
                if f < best_f:
                    best_f = f
                    best_p = self._particles[j].pbest_position
            self._lbest_positions[i] = best_p.copy()

    # ── Single iteration ──────────────────────────────────────────────────────

    def step(self) -> dict:
        """Advance swarm by one iteration.

        Returns a dict with:
          iteration     (int)
          gbest_fitness (float)
          gbest_position (np.ndarray)
          positions     (np.ndarray, shape (n_particles, n_dim))
        """
        cfg = self._cfg
        t = self._iteration
        w = self._w(t)

        if cfg.topology == "ring":
            self._update_lbest()

        for i, prt in enumerate(self._particles):
            r1 = self._rng.random(cfg.n_dimensions)
            r2 = self._rng.random(cfg.n_dimensions)

            # Social attractor: global best (star) or local best (ring)
            attractor = (
                self._lbest_positions[i]
                if cfg.topology == "ring"
                else self._gbest_position
            )

            # ── Velocity update (canonical PSO) ───────────────────────────────
            # v(t+1) = w·v(t) + c1·r1·(pbest - x) + c2·r2·(attractor - x)
            new_v = (
                w * prt.velocity
                + cfg.c1 * r1 * (prt.pbest_position - prt.position)
                + cfg.c2 * r2 * (attractor - prt.position)
            )
            # Clamp velocity to [-Vmax, Vmax]
            new_v = np.clip(new_v, -self._v_max, self._v_max)

            # ── Position update ───────────────────────────────────────────────
            # x(t+1) = x(t) + v(t+1)
            new_p = prt.position + new_v

            # Apply boundary constraint
            new_p, new_v = self._apply_boundary(new_p.copy(), new_v.copy())

            # Evaluate fitness
            new_f = self._func.evaluate(new_p)

            # Update particle state
            prt.position = new_p
            prt.velocity = new_v
            prt.fitness = new_f

            # Update personal best
            prt.update_pbest()

            # Update global best (star topology: immediate update so later
            # particles in the same iteration can benefit — single-loop gbest)
            if new_f < self._gbest_fitness:
                self._gbest_fitness = new_f
                self._gbest_position = new_p.copy()

        self._iteration += 1
        self._convergence.append(self._gbest_fitness)
        self._positions_history.append(self.current_positions.copy())

        return {
            "iteration": self._iteration,
            "gbest_fitness": self._gbest_fitness,
            "gbest_position": self._gbest_position.copy(),
            "positions": self.current_positions,
        }

    # ── Full run ──────────────────────────────────────────────────────────────

    def run(
        self,
        on_iteration: Callable[[int, float, np.ndarray, np.ndarray], None] | None = None,
        stop_flag: Callable[[], bool] | None = None,
    ) -> dict:
        """Run all n_iterations steps.

        Args:
            on_iteration: optional callback(iter, gbest_f, gbest_pos, positions)
                          called after each step.
            stop_flag:    optional callable; if it returns True the loop exits
                          early.

        Returns:
            dict with keys:
              gbest_position   (list[float])
              gbest_fitness    (float)
              convergence_history (list[float])
              iterations_done  (int)
        """
        for _ in range(self._cfg.n_iterations):
            if stop_flag and stop_flag():
                break
            result = self.step()
            if on_iteration:
                on_iteration(
                    result["iteration"],
                    result["gbest_fitness"],
                    result["gbest_position"],
                    result["positions"],
                )

        return {
            "gbest_position": self._gbest_position.tolist(),
            "gbest_fitness": self._gbest_fitness,
            "convergence_history": list(self._convergence),
            "iterations_done": self._iteration,
        }
