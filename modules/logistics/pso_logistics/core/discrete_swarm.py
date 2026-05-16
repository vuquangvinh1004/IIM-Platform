"""Discrete PSO swarm for routing problems.

Update rule per iteration:
    n_inertia = max(1, round(w × n_ops_max))
    n_cog     = max(0, round(c1 × r1 × n_ops_max / 2))   r1 ~ U[0,1]
    n_soc     = max(0, round(c2 × r2 × n_ops_max / 2))   r2 ~ U[0,1]

    new_pos = apply_random_ops(pos, n_inertia)
    new_pos = move_toward(new_pos, pbest, n_cog)
    new_pos = move_toward(new_pos, social_best, n_soc)

Topology:
    "star"  — all particles share a single gbest attractor
    "ring"  — each particle uses the best among {left, self, right} neighbors
"""
from __future__ import annotations

import random
from typing import Any, Callable

from modules.logistics.pso_logistics.core.discrete_particle import (
    DiscreteParticle,
)
from modules.logistics.pso_logistics.core.operators import (
    apply_random_ops,
    move_toward,
)
from modules.logistics.pso_logistics.models.config import LogisticsPSOConfig


class DiscreteSwarm:
    """PSO swarm operating on discrete / permutation solution spaces."""

    def __init__(
        self,
        config: LogisticsPSOConfig,
        problem: Any,
        rng: random.Random,
    ) -> None:
        """
        Args:
            config  : full logistics PSO configuration
            problem : any object with evaluate(perm) → float and
                      initial_position(rng) → list[int]
            rng     : seeded random.Random instance for reproducibility
        """
        self.config = config
        self.problem = problem
        self.rng = rng
        self.particles: list[DiscreteParticle] = []
        self.gbest_position: list[int] = []
        self.gbest_fitness: float = float("inf")
        self.convergence_history: list[float] = []
        self.iteration: int = 0
        self._init()

    # ── Initialisation ────────────────────────────────────────────────────────

    def _init(self) -> None:
        for _ in range(self.config.n_particles):
            pos = self.problem.initial_position(self.rng)
            fit = float(self.problem.evaluate(pos))
            self.particles.append(DiscreteParticle(pos, fit))

        best = min(self.particles, key=lambda p: p.fitness)
        self.gbest_position = list(best.position)
        self.gbest_fitness = best.fitness
        self.convergence_history = [self.gbest_fitness]

    # ── Private helpers ───────────────────────────────────────────────────────

    def _ring_lbest(self) -> list[list[int]]:
        """Compute ring-topology local best for every particle."""
        n = len(self.particles)
        lbests: list[list[int]] = []
        for i in range(n):
            neighbors = [
                self.particles[(i - 1) % n],
                self.particles[i],
                self.particles[(i + 1) % n],
            ]
            best_nb = min(neighbors, key=lambda p: p.pbest_fitness)
            lbests.append(list(best_nb.pbest_position))
        return lbests

    def _n_ops(self, weight: float) -> int:
        """Convert PSO weight to a random integer number of operators."""
        return max(0, round(weight * self.rng.random() * self.config.n_ops_max / 2))

    # ── Public API ────────────────────────────────────────────────────────────

    def step(self) -> dict:
        """Advance the swarm by one iteration.

        Returns a dict with keys:
            iteration        int
            gbest_fitness    float
            gbest_position   list[int]
            positions        list[list[int]]   — current position of every particle
        """
        self.iteration += 1

        social_bests: list[list[int]] = (
            self._ring_lbest()
            if self.config.topology == "ring"
            else [self.gbest_position] * len(self.particles)
        )

        for i, p in enumerate(self.particles):
            n_inertia = max(1, round(self.config.w * self.config.n_ops_max))
            n_cog = self._n_ops(self.config.c1)
            n_soc = self._n_ops(self.config.c2)

            new_pos = apply_random_ops(p.position, n_inertia, self.rng)
            if n_cog > 0:
                new_pos = move_toward(new_pos, p.pbest_position, self.rng, n_cog)
            if n_soc > 0:
                new_pos = move_toward(new_pos, social_bests[i], self.rng, n_soc)

            p.position = new_pos
            p.fitness = float(self.problem.evaluate(new_pos))
            p.update_pbest()

            # ── Mutation: random swap to escape local optima ──────────────────
            if (
                self.config.mutation_rate > 0
                and self.rng.random() < self.config.mutation_rate
            ):
                p.position = apply_random_ops(p.position, 1, self.rng)
                p.fitness = float(self.problem.evaluate(p.position))
                p.update_pbest()

        # Update gbest
        best = min(self.particles, key=lambda p: p.pbest_fitness)
        if best.pbest_fitness < self.gbest_fitness:
            self.gbest_fitness = best.pbest_fitness
            self.gbest_position = list(best.pbest_position)

        self.convergence_history.append(self.gbest_fitness)

        return {
            "iteration": self.iteration,
            "gbest_fitness": self.gbest_fitness,
            "gbest_position": list(self.gbest_position),
            "positions": [list(p.position) for p in self.particles],
        }

    def run(
        self,
        on_iteration: Callable[[dict], None] | None = None,
        stop_flag: Callable[[], bool] | None = None,
    ) -> dict:
        """Run all iterations, calling `on_iteration` after each step.

        Args:
            on_iteration : optional callback(result_dict) called each step
            stop_flag    : optional callable returning True to stop early

        Returns final summary dict (same shape as simulation_done signal).
        """
        for _ in range(self.config.n_iterations):
            if stop_flag and stop_flag():
                break
            result = self.step()
            if on_iteration:
                on_iteration(result)

        return {
            "gbest_position": list(self.gbest_position),
            "gbest_fitness": self.gbest_fitness,
            "convergence_history": list(self.convergence_history),
            "iterations_done": self.iteration,
        }
