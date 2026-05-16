"""TSP problem instance and generator. road_mode=True uses BFS road distances."""
from __future__ import annotations
import math
import random

import numpy as np

from modules.logistics.pso_logistics.core.route_evaluator import (
    build_distance_matrix,
    tsp_tour_distance,
)
from modules.logistics.pso_logistics.models.entities import Customer, Depot


class TSPProblem:
    """Holds a single TSP instance (depot + customers + distance matrix)."""

    def __init__(
        self,
        depot: Depot,
        customers: list[Customer],
        dist_matrix: np.ndarray,
        road_network=None,
        road_node_indices=None,
    ) -> None:
        self.depot = depot
        self.customers = customers
        self.n_customers = len(customers)
        self.dist_matrix = dist_matrix
        self.road_network = road_network
        self.road_node_indices = road_node_indices

    # ------------------------------------------------------------------
    # Factory methods
    # ------------------------------------------------------------------

    @classmethod
    def generate(
        cls,
        n_customers: int,
        coord_range: float,
        data_seed: int,
        road_mode: bool = False,
    ) -> "TSPProblem":
        """Generate a random instance. road_mode=True: BFS grid distances."""
        if road_mode:
            return cls._generate_road(n_customers, coord_range, data_seed)
        return cls._generate_euclidean(n_customers, coord_range, data_seed)

    @classmethod
    def _generate_euclidean(
        cls,
        n_customers: int,
        coord_range: float,
        data_seed: int,
    ) -> "TSPProblem":
        """Classic Euclidean TSP — depot at centre, customers random."""
        rng = random.Random(data_seed)
        depot = Depot(id=0, x=coord_range / 2.0, y=coord_range / 2.0)
        customers = [
            Customer(
                id=i + 1,
                x=rng.uniform(0, coord_range),
                y=rng.uniform(0, coord_range),
            )
            for i in range(n_customers)
        ]
        coords = [(c.x, c.y) for c in customers]
        dist_matrix = build_distance_matrix((depot.x, depot.y), coords)
        return cls(depot, customers, dist_matrix)

    @classmethod
    def _generate_road(
        cls,
        n_customers: int,
        coord_range: float,
        data_seed: int,
    ) -> "TSPProblem":
        """Road-network TSP — nodes at grid intersections, BFS distances."""
        from modules.logistics.pso_logistics.core.road_network import RoadNetwork

        grid_steps = max(8, math.ceil(math.sqrt(n_customers + 1)))
        road_net = RoadNetwork.generate(coord_range, grid_steps, 0.15, data_seed)

        rng = random.Random(data_seed)
        half = grid_steps // 2
        depot_node = half * road_net.cols + half
        dx, dy = road_net.node_xy(depot_node)
        depot = Depot(id=0, x=dx, y=dy)

        available = [i for i in range(road_net.n_nodes) if i != depot_node]
        rng.shuffle(available)
        customer_nodes = available[:n_customers]

        customers = [
            Customer(
                id=i + 1,
                x=road_net.node_xy(n)[0],
                y=road_net.node_xy(n)[1],
            )
            for i, n in enumerate(customer_nodes)
        ]

        node_indices = [depot_node] + customer_nodes
        dist_matrix = road_net.build_dist_matrix(node_indices)

        return cls(depot, customers, dist_matrix, road_net, node_indices)

    # ------------------------------------------------------------------
    # PSO interface
    # ------------------------------------------------------------------

    def evaluate(self, perm: list[int]) -> float:
        """Return total tour distance for a permutation of customer indices."""
        return tsp_tour_distance(perm, self.dist_matrix)

    def initial_position(self, rng: random.Random) -> list[int]:
        """Return a random permutation of customer indices."""
        perm = list(range(self.n_customers))
        rng.shuffle(perm)
        return perm

    def decode_route_ids(self, perm: list[int]) -> list[int]:
        """Convert index permutation to customer IDs."""
        return [self.customers[i].id for i in perm]
