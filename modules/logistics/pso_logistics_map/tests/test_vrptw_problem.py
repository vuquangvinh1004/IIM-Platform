"""Tests for VRPTWProblem on real-road distance matrix.

Test categories:
    1. Constructor validation (shape checks)
    2. decode_giant_tour — capacity split (same as VRP)
    3. evaluate — fitness structure (distance + TW lateness penalty)
    4. initial_position — valid permutation
    5. total_lateness — non-negative, increases with tight windows
    6. decode_routes — dict keys and value ranges
    7. Headless swarm — fitness non-increasing, deterministic
"""
from __future__ import annotations

import random

import numpy as np
import pytest

from modules.logistics.pso_logistics_map.problems.vrptw_problem import VRPTWProblem

# ── Shared fixtures ───────────────────────────────────────────────────────────

N = 5

# All distances = 100m
_DIST_FULL = np.full((N + 1, N + 1), 100.0, dtype=np.float64)
np.fill_diagonal(_DIST_FULL, 0.0)

_DEMANDS = np.full(N, 10.0, dtype=np.float64)

# Speed: 10 m/s → travel time depot→customer = 100/10 = 10 seconds
_SPEED_MPS = 10.0

# Generous time windows: [0, 9999] seconds — nobody is late
_TW_WIDE = np.column_stack([np.zeros(N), np.full(N, 9999.0)])

# Tight time windows: due_time = 5 seconds (travel time = 10s → always late)
_TW_TIGHT = np.column_stack([np.zeros(N), np.full(N, 5.0)])

_SERVICE_ZERO = np.zeros(N, dtype=np.float64)


def _make_vrptw(
    time_windows=None,
    service_times=None,
    vehicle_capacity: float = 50.0,
    n_vehicles: int = 3,
    tw_penalty: float = 1.0,
    speed_mps: float = _SPEED_MPS,
) -> VRPTWProblem:
    tw = _TW_WIDE if time_windows is None else time_windows
    st = _SERVICE_ZERO if service_times is None else service_times
    return VRPTWProblem(
        _DIST_FULL, N, n_vehicles, _DEMANDS, vehicle_capacity,
        speed_mps, tw, st, tw_penalty
    )


# ── 1. Constructor validation ─────────────────────────────────────────────────

class TestConstructorValidation:
    def test_demands_length_mismatch(self):
        with pytest.raises(ValueError, match="demands length"):
            VRPTWProblem(_DIST_FULL, N, 3, np.ones(2), 50.0,
                         _SPEED_MPS, _TW_WIDE, _SERVICE_ZERO)

    def test_time_windows_shape_wrong(self):
        bad_tw = np.zeros((N, 3))  # wrong last dim
        with pytest.raises(ValueError, match="time_windows shape"):
            VRPTWProblem(_DIST_FULL, N, 3, _DEMANDS, 50.0,
                         _SPEED_MPS, bad_tw, _SERVICE_ZERO)

    def test_service_times_length_mismatch(self):
        with pytest.raises(ValueError, match="service_times length"):
            VRPTWProblem(_DIST_FULL, N, 3, _DEMANDS, 50.0,
                         _SPEED_MPS, _TW_WIDE, np.zeros(2))

    def test_n_vehicles_zero(self):
        with pytest.raises(ValueError, match="n_vehicles"):
            VRPTWProblem(_DIST_FULL, N, 0, _DEMANDS, 50.0,
                         _SPEED_MPS, _TW_WIDE, _SERVICE_ZERO)

    def test_vehicle_capacity_zero(self):
        with pytest.raises(ValueError, match="vehicle_capacity"):
            VRPTWProblem(_DIST_FULL, N, 3, _DEMANDS, 0.0,
                         _SPEED_MPS, _TW_WIDE, _SERVICE_ZERO)

    def test_valid_construction(self):
        prob = _make_vrptw()
        assert prob.n_customers == N
        assert prob.vehicle_speed_mps == pytest.approx(_SPEED_MPS)
        assert prob.tw_penalty == pytest.approx(1.0)


# ── 2. decode_giant_tour ──────────────────────────────────────────────────────

class TestDecodeGiantTour:
    def test_all_fit_one_vehicle(self):
        prob = _make_vrptw(vehicle_capacity=50.0)
        routes = prob.decode_giant_tour([0, 1, 2, 3, 4])
        assert len(routes) == 1

    def test_split_by_capacity(self):
        """Same split logic as VRP."""
        prob = _make_vrptw(vehicle_capacity=15.0)  # demand=10, cap=15 → 1 per vehicle
        routes = prob.decode_giant_tour([0, 1, 2, 3, 4])
        assert len(routes) == 5

    def test_all_indices_preserved(self):
        prob = _make_vrptw(vehicle_capacity=25.0)
        perm = [3, 0, 4, 1, 2]
        routes = prob.decode_giant_tour(perm)
        flat = [idx for r in routes for idx in r]
        assert sorted(flat) == sorted(perm)


# ── 3. evaluate ───────────────────────────────────────────────────────────────

class TestEvaluate:
    def test_wide_windows_no_tw_penalty(self):
        """With generous windows, TW penalty = 0, fitness = pure distance."""
        prob = _make_vrptw(time_windows=_TW_WIDE, tw_penalty=100.0, vehicle_capacity=50.0)
        perm = [0, 1, 2, 3, 4]
        fit = prob.evaluate(perm)
        # 1 route: depot→0→1→2→3→4→depot = 6×100 = 600m; TW penalty = 0
        assert fit == pytest.approx(600.0)

    def test_tight_windows_add_penalty(self):
        """With tight windows, fitness > distance-only."""
        prob_wide = _make_vrptw(time_windows=_TW_WIDE, tw_penalty=10.0, vehicle_capacity=50.0)
        prob_tight = _make_vrptw(time_windows=_TW_TIGHT, tw_penalty=10.0, vehicle_capacity=50.0)
        perm = [0, 1, 2, 3, 4]
        fit_wide = prob_wide.evaluate(perm)
        fit_tight = prob_tight.evaluate(perm)
        assert fit_tight > fit_wide

    def test_excess_vehicles_penalty(self):
        """Routes > n_vehicles ⇒ penalty added."""
        prob = _make_vrptw(vehicle_capacity=15.0, n_vehicles=1)
        perm = [0, 1, 2, 3, 4]
        # 5 routes but only 1 vehicle allowed
        fit = prob.evaluate(perm)
        # base: 5×200=1000m; penalty = 4×penalty_per_extra
        assert fit > 1000.0

    def test_fitness_is_finite_for_full_matrix(self):
        prob = _make_vrptw()
        fit = prob.evaluate([0, 1, 2, 3, 4])
        assert np.isfinite(fit)


# ── 4. initial_position ───────────────────────────────────────────────────────

class TestInitialPosition:
    def test_is_permutation(self):
        prob = _make_vrptw()
        pos = prob.initial_position(random.Random(0))
        assert sorted(pos) == list(range(N))

    def test_deterministic(self):
        prob = _make_vrptw()
        p1 = prob.initial_position(random.Random(3))
        p2 = prob.initial_position(random.Random(3))
        assert p1 == p2


# ── 5. total_lateness ─────────────────────────────────────────────────────────

class TestTotalLateness:
    def test_wide_window_no_lateness(self):
        prob = _make_vrptw(time_windows=_TW_WIDE, vehicle_capacity=50.0)
        late = prob.total_lateness([0, 1, 2, 3, 4])
        assert late == pytest.approx(0.0)

    def test_tight_window_has_lateness(self):
        """Travel time = 10s but due_time = 5s → lateness = 5s per customer."""
        prob = _make_vrptw(time_windows=_TW_TIGHT, vehicle_capacity=50.0)
        perm = [0, 1, 2, 3, 4]
        late = prob.total_lateness(perm)
        # First customer: arrival = 100/10 = 10s, due = 5s → lateness = 5s
        assert late > 0.0

    def test_tight_penalty_proportional(self):
        """Higher tw_penalty → higher fitness for same route."""
        perm = [0, 1, 2, 3, 4]
        f1 = _make_vrptw(time_windows=_TW_TIGHT, tw_penalty=1.0, vehicle_capacity=50.0).evaluate(perm)
        f2 = _make_vrptw(time_windows=_TW_TIGHT, tw_penalty=5.0, vehicle_capacity=50.0).evaluate(perm)
        assert f2 > f1


# ── 6. decode_routes ─────────────────────────────────────────────────────────

class TestDecodeRoutes:
    def test_returns_list_of_dicts(self):
        prob = _make_vrptw()
        routes = prob.decode_routes([0, 1, 2, 3, 4])
        assert isinstance(routes, list)
        for r in routes:
            for key in ("vehicle_id", "customer_indices", "distance", "load", "total_lateness_s"):
                assert key in r

    def test_total_load_matches_demands(self):
        prob = _make_vrptw(vehicle_capacity=50.0)
        routes = prob.decode_routes([0, 1, 2, 3, 4])
        total_load = sum(r["load"] for r in routes)
        assert total_load == pytest.approx(_DEMANDS.sum())

    def test_wide_window_zero_lateness_in_routes(self):
        prob = _make_vrptw(time_windows=_TW_WIDE, vehicle_capacity=50.0)
        routes = prob.decode_routes([0, 1, 2, 3, 4])
        total_late = sum(r["total_lateness_s"] for r in routes)
        assert total_late == pytest.approx(0.0)


# ── 7. Headless swarm ─────────────────────────────────────────────────────────

class TestHeadlessSwarm:
    def _run_swarm(self, n_iter: int = 20, seed: int = 0) -> dict:
        from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm
        from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig

        prob = _make_vrptw(vehicle_capacity=25.0)
        cfg = MapLogisticsPSOConfig(
            n_customers=N,
            problem_type="vrptw",
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

    def test_gbest_is_permutation(self):
        r = self._run_swarm()
        assert sorted(r["pos"]) == list(range(N))

    def test_fitness_is_finite(self):
        r = self._run_swarm()
        assert np.isfinite(r["fitness"])

    def test_deterministic(self):
        r1 = self._run_swarm(seed=77)
        r2 = self._run_swarm(seed=77)
        assert r1["fitness"] == r2["fitness"]
        assert r1["pos"] == r2["pos"]

    def test_fitness_non_increasing(self):
        from modules.logistics.pso_logistics_map.pso.discrete_swarm import DiscreteSwarm
        from modules.logistics.pso_logistics_map.models.config import MapLogisticsPSOConfig

        prob = _make_vrptw(vehicle_capacity=25.0)
        cfg = MapLogisticsPSOConfig(n_customers=N, problem_type="vrptw",
                                    n_vehicles=3, vehicle_capacity=25.0,
                                    n_particles=10, n_iterations=30, pso_seed=3)
        rng = random.Random(3)
        swarm = DiscreteSwarm(cfg, prob, rng)
        prev = float("inf")
        for _ in range(30):
            r = swarm.step()
            assert r["gbest_fitness"] <= prev + 1e-9
            prev = r["gbest_fitness"]
