"""Tests for VRPProblem on real-road distance matrix.

Test categories:
    1. Constructor validation (shape mismatch, n_vehicles < 1, capacity <= 0)
    2. decode_giant_tour — capacity split correctness
    3. evaluate — fitness structure (no-penalty vs. with-penalty)
    4. initial_position — valid permutation
    5. decode_routes — dict keys and value ranges
    6. Headless swarm — fitness non-increasing, deterministic, gbest is valid perm
"""
from __future__ import annotations

import random

import numpy as np
import pytest

from modules.logistics.pso_logistics_map.problems.vrp_problem import VRPProblem

# ── Shared fixtures ───────────────────────────────────────────────────────────

N = 5  # 5 customers

# Simple 6×6 fully-connected distance matrix (all distances = 100m)
_DIST_FULL = np.full((N + 1, N + 1), 100.0, dtype=np.float64)
np.fill_diagonal(_DIST_FULL, 0.0)

# Demands: each customer needs 10.0 units
_DEMANDS = np.full(N, 10.0, dtype=np.float64)


def _make_vrp(
    demands=None,
    n_vehicles: int = 3,
    vehicle_capacity: float = 15.0,
    dist_matrix=None,
) -> VRPProblem:
    d = _DEMANDS if demands is None else demands
    m = _DIST_FULL if dist_matrix is None else dist_matrix
    return VRPProblem(m, N, n_vehicles, d, vehicle_capacity)


# ── 1. Constructor validation ─────────────────────────────────────────────────

class TestConstructorValidation:
    def test_demands_length_mismatch(self):
        with pytest.raises(ValueError, match="demands length"):
            VRPProblem(_DIST_FULL, N, 3, np.array([1.0, 2.0]), 50.0)

    def test_n_vehicles_zero(self):
        with pytest.raises(ValueError, match="n_vehicles"):
            VRPProblem(_DIST_FULL, N, 0, _DEMANDS, 50.0)

    def test_vehicle_capacity_zero(self):
        with pytest.raises(ValueError, match="vehicle_capacity"):
            VRPProblem(_DIST_FULL, N, 3, _DEMANDS, 0.0)

    def test_vehicle_capacity_negative(self):
        with pytest.raises(ValueError, match="vehicle_capacity"):
            VRPProblem(_DIST_FULL, N, 3, _DEMANDS, -5.0)

    def test_valid_construction(self):
        prob = _make_vrp()
        assert prob.n_customers == N
        assert prob.n_vehicles == 3
        assert prob.vehicle_capacity == 15.0

    def test_penalty_is_positive(self):
        prob = _make_vrp()
        assert prob._penalty_per_extra > 0


# ── 2. decode_giant_tour ──────────────────────────────────────────────────────

class TestDecodeGiantTour:
    def test_all_fit_one_vehicle(self):
        """With capacity=50, all 5 customers (5×10=50) fit in one route."""
        prob = VRPProblem(_DIST_FULL, N, 3, _DEMANDS, 50.0)
        routes = prob.decode_giant_tour([0, 1, 2, 3, 4])
        assert len(routes) == 1
        assert routes[0] == [0, 1, 2, 3, 4]

    def test_split_two_vehicles(self):
        """Capacity=15 ⇒ each vehicle takes 1 customer (10 ≤ 15)."""
        # demand=10, cap=15: customer 0 → load 10 ≤ 15 OK; add customer 1 → 20 > 15 → split
        prob = VRPProblem(_DIST_FULL, N, 5, _DEMANDS, 15.0)
        routes = prob.decode_giant_tour([0, 1, 2, 3, 4])
        # Each route holds exactly 1 customer
        assert len(routes) == 5
        for r in routes:
            assert len(r) == 1

    def test_empty_perm(self):
        prob = _make_vrp()
        routes = prob.decode_giant_tour([])
        assert routes == []

    def test_single_customer(self):
        prob = _make_vrp()
        routes = prob.decode_giant_tour([2])
        assert routes == [[2]]

    def test_all_indices_preserved(self):
        """decode_giant_tour must preserve every customer index exactly once."""
        prob = _make_vrp(vehicle_capacity=25.0)
        perm = [3, 0, 4, 1, 2]
        routes = prob.decode_giant_tour(perm)
        flat = [idx for r in routes for idx in r]
        assert sorted(flat) == sorted(perm)


# ── 3. evaluate ───────────────────────────────────────────────────────────────

class TestEvaluate:
    def test_within_n_vehicles_no_penalty(self):
        """If routes ≤ n_vehicles, penalty is zero, fitness = total distance."""
        # capacity=50 → 1 route for 5 customers (50 ≤ 50)
        prob = VRPProblem(_DIST_FULL, N, 3, _DEMANDS, 50.0)
        perm = [0, 1, 2, 3, 4]
        fit = prob.evaluate(perm)
        # 1 vehicle route: depot→0→1→2→3→4→depot = 6 edges × 100 = 600m
        assert fit == pytest.approx(600.0)

    def test_excess_vehicles_adds_penalty(self):
        """If routes > n_vehicles, penalty is added."""
        prob = VRPProblem(_DIST_FULL, N, 1, _DEMANDS, 15.0)
        perm = [0, 1, 2, 3, 4]
        fit_no_pen = sum(200.0 for _ in range(5))  # each route: depot→k→depot = 200m
        fit = prob.evaluate(perm)
        # 5 routes needed > 1 allowed → 4 extra routes
        assert fit > fit_no_pen  # penalty added

    def test_fitness_is_finite(self):
        prob = _make_vrp()
        rng = random.Random(42)
        perm = list(range(N))
        rng.shuffle(perm)
        fit = prob.evaluate(perm)
        assert np.isfinite(fit)

    def test_fitness_fully_inf_matrix(self):
        """All-inf dist matrix → fitness is finite when penalty_per_extra is 1e9
        (because finite fallback kicks in) — actually 0 finite values → penalizes correctly."""
        inf_mat = np.full((N + 1, N + 1), np.inf)
        np.fill_diagonal(inf_mat, 0.0)
        demands = np.ones(N)
        prob = VRPProblem(inf_mat, N, 3, demands, 2.0)
        # With inf distance all routes sum to inf — fitness should be inf
        fit = prob.evaluate([0, 1, 2, 3, 4])
        assert not np.isfinite(fit)


# ── 4. initial_position ───────────────────────────────────────────────────────

class TestInitialPosition:
    def test_is_permutation(self):
        prob = _make_vrp()
        rng = random.Random(0)
        pos = prob.initial_position(rng)
        assert sorted(pos) == list(range(N))

    def test_deterministic_with_same_seed(self):
        prob = _make_vrp()
        pos1 = prob.initial_position(random.Random(7))
        pos2 = prob.initial_position(random.Random(7))
        assert pos1 == pos2

    def test_different_seeds_differ(self):
        prob = _make_vrp()
        pos_a = prob.initial_position(random.Random(1))
        pos_b = prob.initial_position(random.Random(9999))
        # Very unlikely to match for N=5
        assert pos_a != pos_b


# ── 5. decode_routes ─────────────────────────────────────────────────────────

class TestDecodeRoutes:
    def test_returns_list_of_dicts(self):
        prob = _make_vrp(vehicle_capacity=50.0)
        routes = prob.decode_routes([0, 1, 2, 3, 4])
        assert isinstance(routes, list)
        for r in routes:
            assert "vehicle_id" in r
            assert "customer_indices" in r
            assert "distance" in r
            assert "load" in r

    def test_vehicle_ids_are_1based(self):
        prob = _make_vrp(vehicle_capacity=50.0)
        routes = prob.decode_routes([0, 1, 2, 3, 4])
        ids = [r["vehicle_id"] for r in routes]
        assert ids[0] == 1

    def test_total_distance_matches_evaluate(self):
        """Sum of per-route distances should equal evaluate (when no extra penalty)."""
        prob = VRPProblem(_DIST_FULL, N, 3, _DEMANDS, 50.0)
        perm = [0, 1, 2, 3, 4]
        routes = prob.decode_routes(perm)
        dist_sum = sum(r["distance"] for r in routes)
        assert dist_sum == pytest.approx(prob.evaluate(perm))

    def test_load_matches_demands(self):
        prob = VRPProblem(_DIST_FULL, N, 3, _DEMANDS, 50.0)
        routes = prob.decode_routes([0, 1, 2, 3, 4])
        total_load = sum(r["load"] for r in routes)
        assert total_load == pytest.approx(_DEMANDS.sum())


# ── 6. Headless swarm ─────────────────────────────────────────────────────────

class TestHeadlessSwarm:
    """Run a small DiscreteSwarm with VRPProblem — headless, no Qt."""

    def _run_swarm(self, n_iter: int = 20, seed: int = 0) -> dict:
        from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm
        from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig

        prob = VRPProblem(_DIST_FULL, N, 3, _DEMANDS, 25.0)  # 2 customers per vehicle
        cfg = MapLogisticsPSOConfig(
            n_customers=N,
            problem_type="vrp",
            n_vehicles=3,
            vehicle_capacity=25.0,
            n_particles=10,
            n_iterations=n_iter,
            pso_seed=seed,
        )
        rng = random.Random(seed)
        swarm = DiscreteSwarm(cfg, prob, rng)
        for _ in range(n_iter):
            swarm.step()
        return {"fitness": swarm.gbest_fitness, "pos": list(swarm.gbest_position)}

    def test_fitness_is_finite(self):
        r = self._run_swarm()
        assert np.isfinite(r["fitness"])

    def test_gbest_is_permutation(self):
        r = self._run_swarm()
        assert sorted(r["pos"]) == list(range(N))

    def test_deterministic(self):
        r1 = self._run_swarm(seed=42)
        r2 = self._run_swarm(seed=42)
        assert r1["fitness"] == r2["fitness"]
        assert r1["pos"] == r2["pos"]

    def test_fitness_non_increasing(self):
        from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm
        from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig

        prob = VRPProblem(_DIST_FULL, N, 3, _DEMANDS, 25.0)
        cfg = MapLogisticsPSOConfig(n_customers=N, problem_type="vrp",
                                    n_vehicles=3, vehicle_capacity=25.0,
                                    n_particles=10, n_iterations=30, pso_seed=7)
        rng = random.Random(7)
        swarm = DiscreteSwarm(cfg, prob, rng)
        prev = float("inf")
        for _ in range(30):
            r = swarm.step()
            assert r["gbest_fitness"] <= prev + 1e-9
            prev = r["gbest_fitness"]
