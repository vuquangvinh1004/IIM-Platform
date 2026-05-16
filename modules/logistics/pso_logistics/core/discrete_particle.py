"""Discrete PSO particle — position is a permutation or route structure."""
from __future__ import annotations


class DiscreteParticle:
    """Single particle whose position is a discrete structure (list, not vector).

    For TSP: position is a permutation of customer indices (list[int]).
    For VRP/VRPTW (v1.1+): position will be a list of route lists.

    Uses __slots__ for memory efficiency when swarms have many particles.
    """

    __slots__ = ("position", "fitness", "pbest_position", "pbest_fitness")

    def __init__(self, position: list, fitness: float = float("inf")) -> None:
        self.position: list = list(position)
        self.fitness: float = float(fitness)
        self.pbest_position: list = list(position)
        self.pbest_fitness: float = float(fitness)

    def update_pbest(self) -> bool:
        """Update personal best if current position is strictly better.

        Returns True if pbest was updated, False otherwise.
        """
        if self.fitness < self.pbest_fitness:
            self.pbest_fitness = self.fitness
            self.pbest_position = list(self.position)
            return True
        return False
