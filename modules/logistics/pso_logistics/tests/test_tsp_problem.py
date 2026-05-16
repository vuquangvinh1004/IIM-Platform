"""test_tsp_problem.py — Unit tests for TSPProblem."""
from __future__ import annotations

import math
import random

import numpy as np
import pytest

from modules.logistics.pso_logistics.core.route_evaluator import (
    build_distance_matrix,
    tsp_tour_distance,
)
from modules.logistics.pso_logistics.models.entities import Customer, Depot
from modules.logistics.pso_logistics.problems.tsp_problem import TSPProblem

# ── TSPProblem.generate ───────────────────────────────────────────────────────

def test_generate_n_customers():
    problem = TSPProblem.generate(n_customers=10, coord_range=100.0, data_seed=1)
    assert problem.n_customers == 10
    assert len(problem.customers) == 10


def test_generate_depot_at_center():
    for n in (5, 15, 20):
        problem = TSPProblem.generate(n_customers=n, coord_range=100.0, data_seed=7)
        assert problem.depot.x == pytest.approx(50.0)
        assert problem.depot.y == pytest.approx(50.0)


def test_generate_customers_within_range():
    coord_range = 80.0
    problem = TSPProblem.generate(n_customers=20, coord_range=coord_range, data_seed=42)
    for c in problem.customers:
        assert 0.0 <= c.x <= coord_range
        assert 0.0 <= c.y <= coord_range


def test_generate_same_seed_reproducible():
    p1 = TSPProblem.generate(10, 100.0, 42)
    p2 = TSPProblem.generate(10, 100.0, 42)
    for c1, c2 in zip(p1.customers, p2.customers):
        assert c1.x == pytest.approx(c2.x)
        assert c1.y == pytest.approx(c2.y)


def test_generate_different_seed_different():
    p1 = TSPProblem.generate(10, 100.0, 1)
    p2 = TSPProblem.generate(10, 100.0, 2)
    coords1 = [(c.x, c.y) for c in p1.customers]
    coords2 = [(c.x, c.y) for c in p2.customers]
    assert coords1 != coords2


def test_generate_dist_matrix_shape():
    n = 8
    problem = TSPProblem.generate(n, 100.0, 5)
    assert problem.dist_matrix.shape == (n + 1, n + 1)


def test_generate_dist_matrix_symmetric():
    problem = TSPProblem.generate(6, 100.0, 3)
    dm = problem.dist_matrix
    assert np.allclose(dm, dm.T)


# ── TSPProblem.evaluate ───────────────────────────────────────────────────────

def test_evaluate_returns_float():
    problem = TSPProblem.generate(5, 100.0, 0)
    rng = random.Random(0)
    perm = problem.initial_position(rng)
    result = problem.evaluate(perm)
    assert isinstance(result, float)
    assert result > 0.0


def test_evaluate_known_case():
    """Two customers in a straight line from depot: distance should be deterministic."""
    depot = Depot(id=0, x=0.0, y=0.0)
    c1 = Customer(id=1, x=10.0, y=0.0)
    c2 = Customer(id=2, x=20.0, y=0.0)
    dm = build_distance_matrix((depot.x, depot.y), [(c1.x, c1.y), (c2.x, c2.y)])
    problem = TSPProblem(depot=depot, customers=[c1, c2], dist_matrix=dm)

    # Route: depot→c1→c2→depot = 10 + 10 + 20 = 40
    dist_0 = problem.evaluate([0, 1])
    # Route: depot→c2→c1→depot = 20 + 10 + 10 = 40
    dist_1 = problem.evaluate([1, 0])
    assert dist_0 == pytest.approx(40.0)
    assert dist_1 == pytest.approx(40.0)


# ── TSPProblem.initial_position ───────────────────────────────────────────────

def test_initial_position_is_valid_permutation():
    problem = TSPProblem.generate(10, 100.0, 1)
    rng = random.Random(0)
    pos = problem.initial_position(rng)
    assert sorted(pos) == list(range(problem.n_customers))


# ── TSPProblem.decode_route_ids ───────────────────────────────────────────────

def test_decode_route_ids():
    problem = TSPProblem.generate(5, 100.0, 9)
    perm = [4, 2, 0, 1, 3]
    ids = problem.decode_route_ids(perm)
    assert len(ids) == 5
    expected = [problem.customers[i].id for i in perm]
    assert ids == expected


# ── build_distance_matrix (standalone) ───────────────────────────────────────

def test_build_distance_matrix_diagonal_zero():
    depot = Depot(id=0, x=0.0, y=0.0)
    customers = [Customer(id=i + 1, x=float(i), y=0.0) for i in range(3)]
    dm = build_distance_matrix((depot.x, depot.y), [(c.x, c.y) for c in customers])
    assert np.all(np.diag(dm) == 0.0)


def test_tsp_tour_distance_single_customer():
    depot = Depot(id=0, x=0.0, y=0.0)
    c = Customer(id=1, x=3.0, y=4.0)
    dm = build_distance_matrix((depot.x, depot.y), [(c.x, c.y)])
    dist = tsp_tour_distance([0], dm)
    # depot→c→depot = 5 + 5 = 10
    assert dist == pytest.approx(10.0)
