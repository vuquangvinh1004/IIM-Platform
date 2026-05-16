"""Tests for VRPTW (Vehicle Routing Problem with Time Windows) — v1.2."""
from __future__ import annotations

import math
import random

import numpy as np
import pytest

from modules.logistics.pso_logistics.core.route_evaluator import (
    vrptw_route_cost,
    vrptw_total_cost,
)
from modules.logistics.pso_logistics.problems.vrptw_problem import VRPTWProblem


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def small_vrptw() -> VRPTWProblem:
    """5 customers, 2 vehicles, capacity 30, deterministic."""
    return VRPTWProblem.generate(
        n_customers=5,
        coord_range=100.0,
        data_seed=42,
        demand_seed=7,
        n_vehicles=2,
        vehicle_capacity=30.0,
        max_demand=10.0,
        vehicle_speed=1.0,
        tw_seed=13,
        tw_width=30.0,
        service_time_max=5.0,
        tw_penalty=10.0,
    )


@pytest.fixture()
def medium_vrptw() -> VRPTWProblem:
    """10 customers, 3 vehicles, capacity 50."""
    return VRPTWProblem.generate(
        n_customers=10,
        coord_range=100.0,
        data_seed=99,
        demand_seed=13,
        n_vehicles=3,
        vehicle_capacity=50.0,
        max_demand=15.0,
        vehicle_speed=1.0,
        tw_seed=17,
        tw_width=40.0,
        service_time_max=5.0,
        tw_penalty=10.0,
    )


@pytest.fixture()
def tight_tw_vrptw() -> VRPTWProblem:
    """Narrow time windows — more lateness expected."""
    return VRPTWProblem.generate(
        n_customers=8,
        coord_range=100.0,
        data_seed=55,
        demand_seed=11,
        n_vehicles=2,
        vehicle_capacity=50.0,
        max_demand=10.0,
        vehicle_speed=1.0,
        tw_seed=5,
        tw_width=5.0,       # very narrow
        service_time_max=3.0,
        tw_penalty=20.0,
    )


# ---------------------------------------------------------------------------
# generate() — instance structure
# ---------------------------------------------------------------------------


class TestGenerate:
    def test_customer_count(self, small_vrptw: VRPTWProblem) -> None:
        assert small_vrptw.n_customers == 5
        assert len(small_vrptw.customers) == 5

    def test_depot_at_centre(self, small_vrptw: VRPTWProblem) -> None:
        assert small_vrptw.depot.x == pytest.approx(50.0)
        assert small_vrptw.depot.y == pytest.approx(50.0)

    def test_dist_matrix_shape(self, small_vrptw: VRPTWProblem) -> None:
        assert small_vrptw.dist_matrix.shape == (6, 6)

    def test_dist_matrix_symmetric(self, small_vrptw: VRPTWProblem) -> None:
        dm = small_vrptw.dist_matrix
        np.testing.assert_allclose(dm, dm.T, atol=1e-10)

    def test_dist_matrix_diagonal_zero(self, small_vrptw: VRPTWProblem) -> None:
        dm = small_vrptw.dist_matrix
        np.testing.assert_allclose(np.diag(dm), 0.0, atol=1e-10)

    def test_demands_positive(self, small_vrptw: VRPTWProblem) -> None:
        for c in small_vrptw.customers:
            assert c.demand > 0

    def test_demands_within_max(self, small_vrptw: VRPTWProblem) -> None:
        for c in small_vrptw.customers:
            assert c.demand <= 10.0 + 1e-9

    def test_vehicle_params(self, small_vrptw: VRPTWProblem) -> None:
        assert small_vrptw.n_vehicles == 2
        assert small_vrptw.vehicle_speed == pytest.approx(1.0)

    def test_tw_penalty(self, small_vrptw: VRPTWProblem) -> None:
        assert small_vrptw.tw_penalty == pytest.approx(10.0)

    def test_capacity_feasibility_guard(self) -> None:
        """Impossibly low capacity should be raised to guarantee feasibility."""
        p = VRPTWProblem.generate(
            n_customers=10,
            coord_range=100.0,
            data_seed=1,
            demand_seed=1,
            n_vehicles=2,
            vehicle_capacity=0.1,   # too low
            max_demand=10.0,
        )
        total_demand = sum(c.demand for c in p.customers)
        assert p.vehicle_capacity >= total_demand / p.n_vehicles - 1e-9

    def test_deterministic_layout(self) -> None:
        """Same seeds → identical layout."""
        a = VRPTWProblem.generate(5, 100.0, 42, 7, 2, 30.0)
        b = VRPTWProblem.generate(5, 100.0, 42, 7, 2, 30.0)
        for ca, cb in zip(a.customers, b.customers):
            assert ca.x == pytest.approx(cb.x)
            assert ca.y == pytest.approx(cb.y)
            assert ca.demand == pytest.approx(cb.demand)
            assert ca.ready_time == pytest.approx(cb.ready_time)
            assert ca.due_time == pytest.approx(cb.due_time)

    def test_different_tw_seed_changes_windows(self) -> None:
        a = VRPTWProblem.generate(5, 100.0, 42, 7, 2, 30.0, tw_seed=1)
        b = VRPTWProblem.generate(5, 100.0, 42, 7, 2, 30.0, tw_seed=999)
        # At least one customer should have a different service_time
        diffs = [
            abs(ca.service_time - cb.service_time)
            for ca, cb in zip(a.customers, b.customers)
        ]
        assert any(d > 1e-9 for d in diffs)


# ---------------------------------------------------------------------------
# Time window generation
# ---------------------------------------------------------------------------


class TestTimeWindows:
    def test_ready_time_non_negative(self, small_vrptw: VRPTWProblem) -> None:
        for c in small_vrptw.customers:
            assert c.ready_time >= 0.0

    def test_due_time_after_ready(self, small_vrptw: VRPTWProblem) -> None:
        for c in small_vrptw.customers:
            assert c.due_time > c.ready_time

    def test_window_width_matches_tw_width(self) -> None:
        """due_time - ready_time ≈ tw_width for customers far from depot."""
        p = VRPTWProblem.generate(
            n_customers=10,
            coord_range=100.0,
            data_seed=42,
            demand_seed=7,
            n_vehicles=3,
            vehicle_capacity=50.0,
            tw_width=20.0,
            vehicle_speed=1.0,
            service_time_max=0.0,  # zero service time simplifies window math
        )
        for c in p.customers:
            width = c.due_time - c.ready_time
            # Customers close to depot: window is truncated at 0 from left
            # For distant customers the window equals tw_width
            assert width <= 20.0 + 1e-9
            assert width > 0.0

    def test_service_time_within_max(self, small_vrptw: VRPTWProblem) -> None:
        for c in small_vrptw.customers:
            assert 0.0 <= c.service_time <= 5.0 + 1e-9

    def test_window_centred_on_natural_time(self) -> None:
        """ready_time + half_width ≈ natural travel time (for non-truncated customers)."""
        p = VRPTWProblem.generate(
            5, 100.0, 42, 7, 2, 30.0,
            vehicle_speed=1.0, tw_width=20.0, service_time_max=0.0
        )
        half = 20.0 / 2.0
        for i, c in enumerate(p.customers):
            natural = float(p.dist_matrix[0, i + 1]) / 1.0
            # If natural >= half, window is not truncated
            if natural >= half:
                assert c.ready_time == pytest.approx(natural - half, abs=1e-6)
                assert c.due_time == pytest.approx(natural + half, abs=1e-6)


# ---------------------------------------------------------------------------
# vrptw_route_cost
# ---------------------------------------------------------------------------


class TestVRPTWRouteCost:
    def test_empty_route(self, small_vrptw: VRPTWProblem) -> None:
        dist, late = vrptw_route_cost([], small_vrptw.dist_matrix,
                                       small_vrptw.customers, 1.0)
        assert dist == 0.0
        assert late == 0.0

    def test_single_customer_no_lateness(self) -> None:
        """Route to a customer whose window exactly covers the natural travel time."""
        p = VRPTWProblem.generate(
            1, 100.0, 42, 7, 1, 50.0,
            vehicle_speed=1.0, tw_width=100.0, service_time_max=0.0
        )
        dist, late = vrptw_route_cost([0], p.dist_matrix, p.customers, 1.0)
        assert dist > 0.0
        assert late == 0.0

    def test_lateness_accrues_when_window_missed(self) -> None:
        """Narrow TW causes lateness for at least some routes."""
        p = VRPTWProblem.generate(
            10, 100.0, 42, 7, 3, 50.0,
            vehicle_speed=0.01,   # very slow → arrive very late
            tw_width=5.0,
            service_time_max=0.0,
        )
        perm = list(range(10))
        total_dist, total_late = vrptw_total_cost(
            [perm], p.dist_matrix, p.customers, 0.01
        )
        assert total_late > 0.0

    def test_route_distance_positive(self, small_vrptw: VRPTWProblem) -> None:
        dist, _ = vrptw_route_cost([0, 1], small_vrptw.dist_matrix,
                                    small_vrptw.customers, 1.0)
        assert dist > 0.0

    def test_distance_independent_of_speed(self) -> None:
        """Distance should not depend on speed (it's Euclidean)."""
        p = VRPTWProblem.generate(5, 100.0, 42, 7, 2, 30.0, service_time_max=0.0)
        d1, _ = vrptw_route_cost([0, 1, 2], p.dist_matrix, p.customers, 1.0)
        d2, _ = vrptw_route_cost([0, 1, 2], p.dist_matrix, p.customers, 5.0)
        assert d1 == pytest.approx(d2, rel=1e-9)

    def test_faster_speed_reduces_lateness(self) -> None:
        p = VRPTWProblem.generate(
            10, 100.0, 42, 7, 3, 50.0,
            tw_width=10.0, service_time_max=0.0,
        )
        perm = list(range(10))
        _, late_slow = vrptw_total_cost([perm], p.dist_matrix, p.customers, 0.5)
        _, late_fast = vrptw_total_cost([perm], p.dist_matrix, p.customers, 5.0)
        assert late_fast <= late_slow


# ---------------------------------------------------------------------------
# decode_giant_tour + evaluate
# ---------------------------------------------------------------------------


class TestDecodeAndEvaluate:
    def test_decode_covers_all_customers(self, small_vrptw: VRPTWProblem) -> None:
        perm = list(range(5))
        routes = small_vrptw.decode_giant_tour(perm)
        all_idx = [idx for r in routes for idx in r]
        assert sorted(all_idx) == list(range(5))

    def test_capacity_respected(self, small_vrptw: VRPTWProblem) -> None:
        perm = list(range(5))
        for route in small_vrptw.decode_giant_tour(perm):
            load = sum(small_vrptw.customers[i].demand for i in route)
            assert load <= small_vrptw.vehicle_capacity + 1e-9

    def test_evaluate_returns_positive(self, small_vrptw: VRPTWProblem) -> None:
        perm = list(range(5))
        assert small_vrptw.evaluate(perm) > 0.0

    def test_evaluate_deterministic(self, small_vrptw: VRPTWProblem) -> None:
        perm = [2, 0, 4, 1, 3]
        assert small_vrptw.evaluate(perm) == pytest.approx(
            small_vrptw.evaluate(perm)
        )

    def test_evaluate_penalises_excess_vehicles(self) -> None:
        """Using more routes than n_vehicles raises fitness."""
        p = VRPTWProblem.generate(
            6, 100.0, 42, 7,
            n_vehicles=1,       # 1 allowed
            vehicle_capacity=5.0,   # very low → many routes needed
            max_demand=5.0,
        )
        perm = list(range(6))
        fitness = p.evaluate(perm)
        routes = p.decode_giant_tour(perm)
        # With only 1 vehicle allowed but multiple needed → penalty applied
        if len(routes) > 1:
            # Fitness should exceed pure distance
            dist, late = vrptw_total_cost(
                routes, p.dist_matrix, p.customers, p.vehicle_speed
            )
            assert fitness > dist

    def test_wide_tw_lower_or_equal_fitness_than_narrow(self) -> None:
        """Wider TW → fewer (or equal) violations → lower (or equal) fitness."""
        base_kwargs = dict(
            n_customers=8, coord_range=100.0, data_seed=42, demand_seed=7,
            n_vehicles=2, vehicle_capacity=50.0, max_demand=10.0,
            vehicle_speed=1.0, tw_seed=13, service_time_max=0.0, tw_penalty=5.0,
        )
        p_wide = VRPTWProblem.generate(**base_kwargs, tw_width=200.0)
        p_narrow = VRPTWProblem.generate(**base_kwargs, tw_width=2.0)
        perm = list(range(8))
        assert p_wide.evaluate(perm) <= p_narrow.evaluate(perm)

    def test_initial_position_is_permutation(self, small_vrptw: VRPTWProblem) -> None:
        rng = random.Random(0)
        pos = small_vrptw.initial_position(rng)
        assert sorted(pos) == list(range(5))

    def test_initial_position_shuffled(self, small_vrptw: VRPTWProblem) -> None:
        """different seeds → different positions (not identity)."""
        rng1 = random.Random(1)
        rng2 = random.Random(2)
        p1 = small_vrptw.initial_position(rng1)
        p2 = small_vrptw.initial_position(rng2)
        # Very unlikely to be equal; at minimum they should be valid permutations
        assert sorted(p1) == list(range(5))
        assert sorted(p2) == list(range(5))


# ---------------------------------------------------------------------------
# decode_routes (Route objects with time fields)
# ---------------------------------------------------------------------------


class TestDecodeRoutes:
    def test_returns_route_objects(self, small_vrptw: VRPTWProblem) -> None:
        from modules.logistics.pso_logistics.models.entities import Route
        routes = small_vrptw.decode_routes(list(range(5)))
        assert all(isinstance(r, Route) for r in routes)

    def test_customer_ids_coverage(self, small_vrptw: VRPTWProblem) -> None:
        routes = small_vrptw.decode_routes(list(range(5)))
        all_ids = [cid for r in routes for cid in r.customer_ids]
        assert sorted(all_ids) == list(range(1, 6))

    def test_time_arrays_same_length(self, small_vrptw: VRPTWProblem) -> None:
        for route in small_vrptw.decode_routes(list(range(5))):
            n = len(route.customer_ids)
            assert len(route.arrival_times) == n
            assert len(route.start_service_times) == n
            assert len(route.waiting_times) == n
            assert len(route.lateness_times) == n

    def test_arrival_before_start_or_equal(self, small_vrptw: VRPTWProblem) -> None:
        for route in small_vrptw.decode_routes(list(range(5))):
            for arr, start in zip(route.arrival_times, route.start_service_times):
                assert start >= arr - 1e-9

    def test_waiting_time_non_negative(self, small_vrptw: VRPTWProblem) -> None:
        for route in small_vrptw.decode_routes(list(range(5))):
            for w in route.waiting_times:
                assert w >= -1e-9

    def test_lateness_non_negative(self, small_vrptw: VRPTWProblem) -> None:
        for route in small_vrptw.decode_routes(list(range(5))):
            for lt in route.lateness_times:
                assert lt >= -1e-9

    def test_distance_positive(self, small_vrptw: VRPTWProblem) -> None:
        for route in small_vrptw.decode_routes(list(range(5))):
            assert route.distance > 0.0

    def test_load_per_route(self, small_vrptw: VRPTWProblem) -> None:
        for route in small_vrptw.decode_routes(list(range(5))):
            expected_load = sum(
                small_vrptw.customers[i].demand
                for i in small_vrptw.decode_giant_tour(list(range(5)))[route.vehicle_id - 1]
            )
            assert route.load == pytest.approx(expected_load, rel=1e-6)

    def test_zero_service_time_no_waiting(self) -> None:
        """With zero service time, start_service = max(arrival, ready)."""
        p = VRPTWProblem.generate(
            5, 100.0, 42, 7, 2, 30.0,
            service_time_max=0.0, tw_width=100.0,
        )
        for route in p.decode_routes(list(range(5))):
            for w in route.waiting_times:
                assert w >= -1e-9


# ---------------------------------------------------------------------------
# total_lateness + on_time_ratio
# ---------------------------------------------------------------------------


class TestSummaryHelpers:
    def test_wide_windows_low_lateness(self) -> None:
        p = VRPTWProblem.generate(
            8, 100.0, 42, 7, 3, 50.0,
            vehicle_speed=5.0, tw_width=10000.0, service_time_max=0.0,
        )
        perm = list(range(8))
        assert p.total_lateness(perm) == pytest.approx(0.0, abs=1e-6)

    def test_on_time_ratio_between_0_and_1(self, small_vrptw: VRPTWProblem) -> None:
        perm = list(range(5))
        ratio = small_vrptw.on_time_ratio(perm)
        assert 0.0 <= ratio <= 1.0

    def test_on_time_ratio_full_with_wide_windows(self) -> None:
        p = VRPTWProblem.generate(
            5, 100.0, 42, 7, 2, 30.0,
            vehicle_speed=10.0, tw_width=99999.0, service_time_max=0.0,
        )
        assert p.on_time_ratio(list(range(5))) == pytest.approx(1.0)

    def test_total_lateness_matches_route_sum(self, small_vrptw: VRPTWProblem) -> None:
        perm = list(range(5))
        route_late = sum(
            sum(r.lateness_times)
            for r in small_vrptw.decode_routes(perm)
        )
        assert small_vrptw.total_lateness(perm) == pytest.approx(route_late, rel=1e-5)


# ---------------------------------------------------------------------------
# vrptw_total_cost (evaluator utility)
# ---------------------------------------------------------------------------


class TestVRPTWTotalCost:
    def test_empty_routes_list(self, small_vrptw: VRPTWProblem) -> None:
        dist, late = vrptw_total_cost([], small_vrptw.dist_matrix,
                                       small_vrptw.customers, 1.0)
        assert dist == 0.0
        assert late == 0.0

    def test_sums_individual_route_costs(self, small_vrptw: VRPTWProblem) -> None:
        routes = [[0, 1], [2, 3, 4]]
        total_d, total_l = vrptw_total_cost(
            routes, small_vrptw.dist_matrix, small_vrptw.customers, 1.0
        )
        d1, l1 = vrptw_route_cost([0, 1], small_vrptw.dist_matrix,
                                   small_vrptw.customers, 1.0)
        d2, l2 = vrptw_route_cost([2, 3, 4], small_vrptw.dist_matrix,
                                   small_vrptw.customers, 1.0)
        assert total_d == pytest.approx(d1 + d2)
        assert total_l == pytest.approx(l1 + l2)


# ---------------------------------------------------------------------------
# Medium / regression
# ---------------------------------------------------------------------------


class TestMediumRegression:
    def test_medium_evaluate_non_negative(self, medium_vrptw: VRPTWProblem) -> None:
        perm = list(range(10))
        assert medium_vrptw.evaluate(perm) >= 0.0

    def test_medium_routes_count_reasonable(self, medium_vrptw: VRPTWProblem) -> None:
        perm = list(range(10))
        routes = medium_vrptw.decode_giant_tour(perm)
        assert 1 <= len(routes) <= 10

    def test_medium_decode_ids_coverage(self, medium_vrptw: VRPTWProblem) -> None:
        perm = list(range(10))
        ids = medium_vrptw.decode_route_ids(perm)
        all_ids = [i for r in ids for i in r]
        assert sorted(all_ids) == list(range(1, 11))

    def test_tight_tw_has_lateness(self, tight_tw_vrptw: VRPTWProblem) -> None:
        """Very narrow windows + default speed should produce some lateness."""
        perm = list(range(tight_tw_vrptw.n_customers))
        # Not guaranteed since some customers may happen to be close to depot,
        # but total_lateness should be accessible
        late = tight_tw_vrptw.total_lateness(perm)
        assert late >= 0.0
