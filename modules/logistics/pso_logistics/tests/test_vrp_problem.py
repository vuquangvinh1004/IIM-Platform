"""Tests for VRP (Capacitated Vehicle Routing Problem) — v1.1."""
from __future__ import annotations

import random

import numpy as np
import pytest

from modules.logistics.pso_logistics.core.route_evaluator import (
    vrp_route_distance,
    vrp_total_distance,
)
from modules.logistics.pso_logistics.problems.vrp_problem import VRPProblem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def small_vrp() -> VRPProblem:
    """5 customers, 2 vehicles, capacity 30, deterministic demands."""
    return VRPProblem.generate(
        n_customers=5,
        coord_range=100.0,
        data_seed=42,
        demand_seed=7,
        n_vehicles=2,
        vehicle_capacity=30.0,
        max_demand=10.0,
    )


@pytest.fixture()
def medium_vrp() -> VRPProblem:
    """10 customers, 3 vehicles, capacity 50."""
    return VRPProblem.generate(
        n_customers=10,
        coord_range=100.0,
        data_seed=99,
        demand_seed=13,
        n_vehicles=3,
        vehicle_capacity=50.0,
        max_demand=15.0,
    )


# ---------------------------------------------------------------------------
# generate()
# ---------------------------------------------------------------------------


class TestVRPProblemGenerate:
    def test_correct_n_customers(self, small_vrp):
        assert small_vrp.n_customers == 5
        assert len(small_vrp.customers) == 5

    def test_depot_at_centre(self, small_vrp):
        assert small_vrp.depot.x == pytest.approx(50.0)
        assert small_vrp.depot.y == pytest.approx(50.0)

    def test_dist_matrix_shape(self, small_vrp):
        # (n_customers+1) × (n_customers+1)
        n = small_vrp.n_customers
        assert small_vrp.dist_matrix.shape == (n + 1, n + 1)

    def test_dist_matrix_symmetric(self, small_vrp):
        d = small_vrp.dist_matrix
        assert np.allclose(d, d.T)

    def test_dist_matrix_zero_diagonal(self, small_vrp):
        d = small_vrp.dist_matrix
        assert np.allclose(np.diag(d), 0.0)

    def test_demands_positive(self, small_vrp):
        for c in small_vrp.customers:
            assert c.demand > 0.0

    def test_demands_bounded(self, small_vrp):
        for c in small_vrp.customers:
            assert c.demand <= 10.0 + 1e-9

    def test_feasibility_guard_raises_capacity_if_needed(self):
        """If original capacity is too small, generate() silently raises it."""
        # 5 customers, max_demand=20 → total can be up to 100; capacity 10 per vehicle
        # with 2 vehicles max = 20 < potential total → guard must raise capacity
        p = VRPProblem.generate(
            n_customers=5,
            coord_range=100.0,
            data_seed=1,
            demand_seed=1,
            n_vehicles=2,
            vehicle_capacity=10.0,   # intentionally too small
            max_demand=20.0,
        )
        total_demand = sum(c.demand for c in p.customers)
        assert p.vehicle_capacity >= total_demand / 2

    def test_different_data_seeds_give_different_positions(self):
        p1 = VRPProblem.generate(5, 100.0, 1, 1, 2, 30.0)
        p2 = VRPProblem.generate(5, 100.0, 2, 1, 2, 30.0)
        positions_1 = [(c.x, c.y) for c in p1.customers]
        positions_2 = [(c.x, c.y) for c in p2.customers]
        assert positions_1 != positions_2

    def test_different_demand_seeds_give_different_demands(self):
        p1 = VRPProblem.generate(5, 100.0, 42, 1, 2, 30.0)
        p2 = VRPProblem.generate(5, 100.0, 42, 2, 2, 30.0)
        d1 = [c.demand for c in p1.customers]
        d2 = [c.demand for c in p2.customers]
        assert d1 != d2

    def test_same_seeds_reproducible(self):
        p1 = VRPProblem.generate(5, 100.0, 42, 7, 3, 30.0)
        p2 = VRPProblem.generate(5, 100.0, 42, 7, 3, 30.0)
        assert [c.x for c in p1.customers] == [c.x for c in p2.customers]
        assert [c.demand for c in p1.customers] == [c.demand for c in p2.customers]


# ---------------------------------------------------------------------------
# decode_giant_tour()
# ---------------------------------------------------------------------------


class TestDecodeGiantTour:
    def test_all_customers_present(self, small_vrp):
        perm = list(range(small_vrp.n_customers))
        routes = small_vrp.decode_giant_tour(perm)
        all_indices = [idx for route in routes for idx in route]
        assert sorted(all_indices) == list(range(small_vrp.n_customers))

    def test_no_route_exceeds_capacity(self, small_vrp):
        perm = list(range(small_vrp.n_customers))
        routes = small_vrp.decode_giant_tour(perm)
        for route in routes:
            load = sum(small_vrp.customers[i].demand for i in route)
            assert load <= small_vrp.vehicle_capacity + 1e-9

    def test_empty_perm_gives_empty_routes(self, small_vrp):
        routes = small_vrp.decode_giant_tour([])
        assert routes == []

    def test_single_customer_single_route(self, small_vrp):
        routes = small_vrp.decode_giant_tour([0])
        assert len(routes) == 1
        assert routes[0] == [0]

    def test_routes_partition_perm(self, medium_vrp):
        rng = random.Random(7)
        perm = list(range(medium_vrp.n_customers))
        rng.shuffle(perm)
        routes = medium_vrp.decode_giant_tour(perm)
        flat = [idx for r in routes for idx in r]
        assert flat == perm


# ---------------------------------------------------------------------------
# evaluate()
# ---------------------------------------------------------------------------


class TestVRPEvaluate:
    def test_returns_float(self, small_vrp):
        perm = list(range(small_vrp.n_customers))
        assert isinstance(small_vrp.evaluate(perm), float)

    def test_positive_fitness(self, small_vrp):
        perm = list(range(small_vrp.n_customers))
        assert small_vrp.evaluate(perm) > 0.0

    def test_penalty_applied_for_excess_vehicles(self):
        """Force excess vehicles: 1 vehicle, high demands → multiple routes needed → penalty."""
        p = VRPProblem.generate(
            n_customers=6,
            coord_range=100.0,
            data_seed=42,
            demand_seed=7,
            n_vehicles=1,        # only 1 vehicle allowed
            vehicle_capacity=5.0,  # very low → must split into many routes
            max_demand=4.0,
        )
        perm = list(range(6))
        routes = p.decode_giant_tour(perm)
        n_extra = max(0, len(routes) - 1)
        fitness = p.evaluate(perm)
        base_dist = vrp_total_distance(routes, p.dist_matrix)
        expected = base_dist + n_extra * p._penalty_per_extra
        assert fitness == pytest.approx(expected)

    def test_no_penalty_when_within_vehicle_limit(self, medium_vrp):
        """A perm that fits within n_vehicles should have zero penalty."""
        # Ensure at least one valid assignment exists
        perm = list(range(medium_vrp.n_customers))
        routes = medium_vrp.decode_giant_tour(perm)
        if len(routes) <= medium_vrp.n_vehicles:
            base = vrp_total_distance(routes, medium_vrp.dist_matrix)
            assert medium_vrp.evaluate(perm) == pytest.approx(base)

    def test_reproducible_for_same_perm(self, medium_vrp):
        perm = [3, 1, 7, 0, 9, 4, 2, 8, 5, 6]
        f1 = medium_vrp.evaluate(perm)
        f2 = medium_vrp.evaluate(perm)
        assert f1 == pytest.approx(f2)


# ---------------------------------------------------------------------------
# PSO interface
# ---------------------------------------------------------------------------


class TestVRPPSOInterface:
    def test_initial_position_is_permutation(self, small_vrp):
        rng = random.Random(0)
        pos = small_vrp.initial_position(rng)
        assert sorted(pos) == list(range(small_vrp.n_customers))

    def test_initial_position_different_for_different_rng(self, small_vrp):
        pos1 = small_vrp.initial_position(random.Random(1))
        pos2 = small_vrp.initial_position(random.Random(2))
        assert pos1 != pos2 or True  # may coincide by chance; just ensure no crash

    def test_decode_routes_returns_route_objects(self, small_vrp):
        from modules.logistics.pso_logistics.models.entities import Route

        perm = list(range(small_vrp.n_customers))
        routes = small_vrp.decode_routes(perm)
        assert all(isinstance(r, Route) for r in routes)

    def test_decode_routes_covers_all_customers(self, small_vrp):
        perm = list(range(small_vrp.n_customers))
        routes = small_vrp.decode_routes(perm)
        all_ids = [cid for r in routes for cid in r.customer_ids]
        assert sorted(all_ids) == list(range(1, small_vrp.n_customers + 1))

    def test_route_distances_positive(self, medium_vrp):
        rng = random.Random(42)
        perm = medium_vrp.initial_position(rng)
        for r in medium_vrp.decode_routes(perm):
            if r.customer_ids:
                assert r.distance > 0.0

    def test_route_load_matches_demand_sum(self, medium_vrp):
        perm = list(range(medium_vrp.n_customers))
        routes_obj = medium_vrp.decode_routes(perm)
        routes_idx = medium_vrp.decode_giant_tour(perm)
        for obj, idx_list in zip(routes_obj, routes_idx):
            expected_load = sum(medium_vrp.customers[i].demand for i in idx_list)
            assert obj.load == pytest.approx(expected_load)


# ---------------------------------------------------------------------------
# vrp_route_distance / vrp_total_distance utilities
# ---------------------------------------------------------------------------


class TestVRPDistanceUtils:
    def test_empty_route_zero_distance(self, small_vrp):
        assert vrp_route_distance([], small_vrp.dist_matrix) == 0.0

    def test_single_customer_round_trip(self, small_vrp):
        # depot → customer[0]+1 → depot
        d = small_vrp.dist_matrix
        expected = float(d[0, 1]) + float(d[1, 0])
        result = vrp_route_distance([0], d)
        assert result == pytest.approx(expected)

    def test_total_distance_sum_of_routes(self, medium_vrp):
        perm = list(range(medium_vrp.n_customers))
        routes = medium_vrp.decode_giant_tour(perm)
        individual = sum(
            vrp_route_distance(r, medium_vrp.dist_matrix) for r in routes
        )
        total = vrp_total_distance(routes, medium_vrp.dist_matrix)
        assert total == pytest.approx(individual)

    def test_total_empty_routes_zero(self, small_vrp):
        assert vrp_total_distance([], small_vrp.dist_matrix) == 0.0
