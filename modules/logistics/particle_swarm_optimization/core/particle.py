"""Particle class for PSO — represents a single agent in the swarm."""
from __future__ import annotations

import numpy as np


class Particle:
    """A single particle in the PSO swarm.

    Attributes:
        position      : current position in the search space, shape (n_dim,)
        velocity      : current velocity, shape (n_dim,)
        fitness       : objective function value at current position
        pbest_position: personal best position found so far
        pbest_fitness : objective function value at personal best position
    """

    __slots__ = ("position", "velocity", "fitness", "pbest_position", "pbest_fitness")

    def __init__(
        self,
        position: np.ndarray,
        velocity: np.ndarray,
        fitness: float,
    ) -> None:
        self.position: np.ndarray = position.copy()
        self.velocity: np.ndarray = velocity.copy()
        self.fitness: float = fitness
        self.pbest_position: np.ndarray = position.copy()
        self.pbest_fitness: float = fitness

    def update_pbest(self) -> None:
        """Update personal best if current fitness is strictly better (lower)."""
        if self.fitness < self.pbest_fitness:
            self.pbest_fitness = self.fitness
            self.pbest_position = self.position.copy()
