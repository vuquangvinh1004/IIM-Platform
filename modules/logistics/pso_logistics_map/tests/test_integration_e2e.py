"""test_integration_e2e.py — Integration tests dùng cache graph thật (hcm_q1_driving.pkl).

Các test này dùng pickle cache đã được tạo sẵn từ vietnam-260413.osm.pbf.
Bỏ qua toàn bộ nếu cache không tồn tại (CI không có file .pbf).
"""
from __future__ import annotations

import pickle
import random
from pathlib import Path

import numpy as np
import pytest

_MODULE_DIR = Path(__file__).parent.parent
_CACHE_PATH = _MODULE_DIR / "cache" / "hcm_q1_driving.pkl"

pytestmark = pytest.mark.skipif(
    not _CACHE_PATH.exists(),
    reason=f"Cache graph không tìm thấy: {_CACHE_PATH}",
)

# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def real_graph():
    """Tải graph NetworkX đã cache từ hcm_q1_driving.pkl."""
    with open(_CACHE_PATH, "rb") as f:
        return pickle.load(f)


@pytest.fixture(scope="module")
def sampled_matrix(real_graph):
    """Matrix 6×6 lấy từ 6 node ngẫu nhiên (1 depot + 5 customers)."""
    from modules.logistics.pso_logistics_map.core.distance_matrix import build_matrix

    rng = random.Random(42)
    all_nodes = list(real_graph.nodes())
    node_ids = rng.sample(all_nodes, 6)
    matrix = build_matrix(real_graph, node_ids)
    return matrix, node_ids


# ── Graph sanity ──────────────────────────────────────────────────────────────


class TestCachedGraph:
    def test_graph_has_nodes(self, real_graph):
        assert real_graph.number_of_nodes() > 100

    def test_graph_has_edges(self, real_graph):
        assert real_graph.number_of_edges() > 100

    def test_all_nodes_have_coords(self, real_graph):
        for n in list(real_graph.nodes())[:50]:
            assert "x" in real_graph.nodes[n], f"node {n} missing 'x'"
            assert "y" in real_graph.nodes[n], f"node {n} missing 'y'"


# ── Distance matrix ───────────────────────────────────────────────────────────


class TestDistanceMatrixIntegration:
    def test_shape(self, sampled_matrix):
        matrix, node_ids = sampled_matrix
        assert matrix.shape == (6, 6)

    def test_diagonal_zero(self, sampled_matrix):
        matrix, _ = sampled_matrix
        for i in range(6):
            assert matrix[i, i] == 0.0

    def test_finite_values_exist(self, sampled_matrix):
        """Ít nhất một số ô (ngoài đường chéo) phải hữu hạn."""
        matrix, _ = sampled_matrix
        off_diag = matrix.copy()
        np.fill_diagonal(off_diag, np.inf)
        assert np.any(np.isfinite(off_diag))


# ── TSP headless ───────────────────────────────────────────────────────────────


class TestTSPIntegration:
    def test_evaluate_finite(self, sampled_matrix):
        from modules.logistics.pso_logistics_map.problems.tsp_problem import TSPProblem

        matrix, _ = sampled_matrix
        n_cust = matrix.shape[0] - 1
        problem = TSPProblem(matrix, n_cust)
        perm = problem.initial_position(np.random.default_rng(42))
        fitness = problem.evaluate(perm)
        assert np.isfinite(fitness) or fitness == float("inf")  # inf allowed for disconnected

    def test_evaluate_deterministic(self, sampled_matrix):
        from modules.logistics.pso_logistics_map.problems.tsp_problem import TSPProblem

        matrix, _ = sampled_matrix
        n_cust = matrix.shape[0] - 1
        problem = TSPProblem(matrix, n_cust)
        perm = problem.initial_position(np.random.default_rng(0))
        assert problem.evaluate(perm) == problem.evaluate(perm)

    def test_swarm_converges(self, sampled_matrix):
        from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig
        from modules.logistics.pso_logistics_map.problems.tsp_problem import TSPProblem
        from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm

        matrix, _ = sampled_matrix
        n_cust = matrix.shape[0] - 1
        problem = TSPProblem(matrix, n_cust)
        config = MapLogisticsPSOConfig(n_customers=n_cust, n_particles=10, n_iterations=30,
                                       w=0.5, c1=1.5, c2=1.5, n_ops_max=2, topology="star")
        swarm = DiscreteSwarm(
            config=config,
            problem=problem,
            rng=random.Random(42),
        )
        initial_fitness = swarm.gbest_fitness
        for _ in range(30):
            swarm.step()
        # gBest can only improve or stay (monotonically non-increasing)
        assert swarm.gbest_fitness <= initial_fitness + 1e-9

    def test_swarm_gbest_position_valid(self, sampled_matrix):
        from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig
        from modules.logistics.pso_logistics_map.problems.tsp_problem import TSPProblem
        from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm

        matrix, _ = sampled_matrix
        n_cust = matrix.shape[0] - 1
        problem = TSPProblem(matrix, n_cust)
        config = MapLogisticsPSOConfig(n_customers=n_cust, n_particles=8, n_iterations=10,
                                       w=0.5, c1=1.5, c2=1.5, n_ops_max=2, topology="star")
        swarm = DiscreteSwarm(config=config, problem=problem, rng=random.Random(1))
        for _ in range(10):
            swarm.step()
        pos = swarm.gbest_position
        assert sorted(pos) == list(range(n_cust))


# ── VRP headless ───────────────────────────────────────────────────────────────


class TestVRPIntegration:
    def test_vrp_evaluate(self, sampled_matrix):
        from modules.logistics.pso_logistics_map.problems.vrp_problem import VRPProblem

        matrix, _ = sampled_matrix
        n_cust = matrix.shape[0] - 1
        demands = np.ones(n_cust, dtype=np.float64) * 10.0
        problem = VRPProblem(matrix, n_cust, n_vehicles=2, demands=demands, vehicle_capacity=30.0)
        perm = problem.initial_position(np.random.default_rng(42))
        fitness = problem.evaluate(perm)
        assert fitness >= 0.0

    def test_vrp_decode_routes_covers_all_customers(self, sampled_matrix):
        from modules.logistics.pso_logistics_map.problems.vrp_problem import VRPProblem

        matrix, _ = sampled_matrix
        n_cust = matrix.shape[0] - 1
        demands = np.ones(n_cust, dtype=np.float64) * 10.0
        problem = VRPProblem(matrix, n_cust, n_vehicles=2, demands=demands, vehicle_capacity=30.0)
        perm = problem.initial_position(np.random.default_rng(0))
        routes = problem.decode_routes(perm)
        visited = set()
        for r in routes:
            visited.update(r["customer_indices"])
        assert visited == set(range(n_cust))

    def test_vrp_swarm_converges(self, sampled_matrix):
        from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig
        from modules.logistics.pso_logistics_map.problems.vrp_problem import VRPProblem
        from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm

        matrix, _ = sampled_matrix
        n_cust = matrix.shape[0] - 1
        demands = np.ones(n_cust, dtype=np.float64) * 10.0
        problem = VRPProblem(matrix, n_cust, n_vehicles=2, demands=demands, vehicle_capacity=30.0)
        config = MapLogisticsPSOConfig(n_customers=n_cust, n_particles=10, n_iterations=30,
                                       w=0.5, c1=1.5, c2=1.5, n_ops_max=2, topology="star")
        swarm = DiscreteSwarm(config=config, problem=problem, rng=random.Random(42))
        initial = swarm.gbest_fitness
        for _ in range(30):
            swarm.step()
        assert swarm.gbest_fitness <= initial + 1e-9
