"""Tests for TSPProblem — bài toán TSP trên ma trận khoảng cách thật."""
from __future__ import annotations

import random

import numpy as np
import pytest

from modules.logistics.pso_logistics_map.problems.tsp_problem import TSPProblem
from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm
from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig


# --------------------------------------------------------------------------- #
#  Fixtures                                                                    #
# --------------------------------------------------------------------------- #

@pytest.fixture
def simple_matrix() -> np.ndarray:
    """Ma trận 4×4: depot + 3 customers, cung đối xứng đều = 1000 m.

    Layout:  index 0 = depot, 1 = A, 2 = B, 3 = C.
    d(depot,A)=1000, d(depot,B)=2000, d(depot,C)=1500,
    d(A,B)=800, d(A,C)=900, d(B,C)=700.
    """
    mat = np.full((4, 4), np.inf)
    np.fill_diagonal(mat, 0.0)
    edges = [
        (0, 1, 1000.0),
        (0, 2, 2000.0),
        (0, 3, 1500.0),
        (1, 2,  800.0),
        (1, 3,  900.0),
        (2, 3,  700.0),
    ]
    for u, v, w in edges:
        mat[u][v] = w
        mat[v][u] = w
    return mat


@pytest.fixture
def three_customers(simple_matrix) -> TSPProblem:
    return TSPProblem(simple_matrix, n_customers=3)


# --------------------------------------------------------------------------- #
#  Constructor validation                                                      #
# --------------------------------------------------------------------------- #

class TestTSPProblemInit:
    def test_valid_creation(self, simple_matrix):
        p = TSPProblem(simple_matrix, n_customers=3)
        assert p.n_customers == 3

    def test_wrong_shape_raises(self):
        mat = np.zeros((3, 3))
        with pytest.raises(ValueError, match="shape"):
            TSPProblem(mat, n_customers=3)  # expects (4,4)

    def test_1d_raises(self):
        with pytest.raises(ValueError, match="2D"):
            TSPProblem(np.zeros(4), n_customers=3)

    def test_zero_customers_raises(self):
        mat = np.zeros((1, 1))
        with pytest.raises(ValueError, match="n_customers"):
            TSPProblem(mat, n_customers=0)


# --------------------------------------------------------------------------- #
#  initial_position                                                            #
# --------------------------------------------------------------------------- #

class TestInitialPosition:
    def test_is_permutation(self, three_customers):
        rng = random.Random(0)
        perm = three_customers.initial_position(rng)
        assert sorted(perm) == [0, 1, 2]

    def test_different_seeds_can_differ(self, three_customers):
        results = {
            tuple(three_customers.initial_position(random.Random(s)))
            for s in range(20)
        }
        assert len(results) > 1, "hoán vị nên đa dạng theo seed"

    def test_length_correct(self, three_customers):
        rng = random.Random(42)
        assert len(three_customers.initial_position(rng)) == 3


# --------------------------------------------------------------------------- #
#  evaluate                                                                    #
# --------------------------------------------------------------------------- #

class TestEvaluate:
    def test_known_tour(self, three_customers):
        # depot→A→B→C→depot = 1000+800+700+1500 = 4000
        assert three_customers.evaluate([0, 1, 2]) == pytest.approx(4000.0)

    def test_known_tour_reversed(self, three_customers):
        # depot→C→B→A→depot = 1500+700+800+1000 = 4000 (symmetric)
        assert three_customers.evaluate([2, 1, 0]) == pytest.approx(4000.0)

    def test_diagonal_tour(self, three_customers):
        # depot→A→C→B→depot = 1000+900+700+2000 = 4600
        assert three_customers.evaluate([0, 2, 1]) == pytest.approx(4600.0)

    def test_inf_edge_returns_inf(self, simple_matrix):
        # Tạo ma trận chứa cung không đi được
        mat = simple_matrix.copy()
        mat[1][2] = np.inf  # cắt cung A–B
        mat[2][1] = np.inf
        p = TSPProblem(mat, n_customers=3)
        assert p.evaluate([0, 1, 2]) == float("inf")

    def test_single_customer(self):
        mat = np.array([[0.0, 500.0], [500.0, 0.0]])
        p = TSPProblem(mat, n_customers=1)
        assert p.evaluate([0]) == pytest.approx(1000.0)


# --------------------------------------------------------------------------- #
#  Headless swarm — fitness phải giảm hoặc giữ nguyên                         #
# --------------------------------------------------------------------------- #

class TestHeadlessSwarm:
    def test_fitness_non_increasing(self, simple_matrix):
        """gbest_fitness không tăng sau mỗi iteration."""
        config = MapLogisticsPSOConfig(
            n_customers=3,
            n_particles=10,
            n_iterations=30,
            w=0.5,
            c1=1.5,
            c2=1.5,
            n_ops_max=3,
            pso_seed=7,
            step_delay_ms=0,
        )
        problem = TSPProblem(simple_matrix, n_customers=3)
        rng = random.Random(config.pso_seed)
        swarm = DiscreteSwarm(config, problem, rng)

        prev_fitness = swarm.gbest_fitness
        for _ in range(config.n_iterations):
            result = swarm.step()
            assert result["gbest_fitness"] <= prev_fitness + 1e-9, (
                f"fitness tăng: {prev_fitness} → {result['gbest_fitness']}"
            )
            prev_fitness = result["gbest_fitness"]

    def test_gbest_is_valid_permutation(self, simple_matrix):
        """gbest_position luôn là hoán vị hợp lệ."""
        config = MapLogisticsPSOConfig(
            n_customers=3,
            n_particles=10,
            n_iterations=20,
            pso_seed=0,
            step_delay_ms=0,
        )
        problem = TSPProblem(simple_matrix, n_customers=3)
        swarm = DiscreteSwarm(config, problem, random.Random(0))
        swarm.run()
        assert sorted(swarm.gbest_position) == [0, 1, 2]

    def test_run_returns_summary(self, simple_matrix):
        config = MapLogisticsPSOConfig(
            n_customers=3,
            n_particles=5,
            n_iterations=10,
            pso_seed=1,
            step_delay_ms=0,
        )
        problem = TSPProblem(simple_matrix, n_customers=3)
        summary = DiscreteSwarm(config, problem, random.Random(1)).run()
        assert "gbest_position" in summary
        assert "gbest_fitness" in summary
        assert "convergence_history" in summary
        assert summary["iterations_done"] == 10
        assert len(summary["convergence_history"]) == 11  # init + 10 steps

    def test_deterministic_with_same_seed(self, simple_matrix):
        config = MapLogisticsPSOConfig(
            n_customers=3,
            n_particles=8,
            n_iterations=15,
            pso_seed=99,
            step_delay_ms=0,
        )
        problem = TSPProblem(simple_matrix, n_customers=3)

        r1 = DiscreteSwarm(config, problem, random.Random(99)).run()
        r2 = DiscreteSwarm(config, problem, random.Random(99)).run()
        assert r1["gbest_fitness"] == r2["gbest_fitness"]
        assert r1["gbest_position"] == r2["gbest_position"]
