"""Tests: objective functions (Sphere, Ackley, registry)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from modules.logistics.particle_swarm_optimization.core.objective_functions import (
    Ackley,
    ObjectiveFunction,
    Sphere,
    get_function,
    list_functions,
)


class TestSphere:
    def test_zero_vector(self):
        f = Sphere()
        assert f.evaluate(np.zeros(2)) == pytest.approx(0.0)

    def test_unit_vector_2d(self):
        f = Sphere()
        assert f.evaluate(np.array([1.0, 0.0])) == pytest.approx(1.0)

    def test_specific_2d(self):
        f = Sphere()
        assert f.evaluate(np.array([3.0, 4.0])) == pytest.approx(25.0)

    def test_nd(self):
        f = Sphere()
        x = np.ones(10)
        assert f.evaluate(x) == pytest.approx(10.0)

    def test_global_optimum(self):
        val, _ = Sphere().global_optimum
        assert val == pytest.approx(0.0)

    def test_suggested_bounds(self):
        lb, ub = Sphere().suggested_bounds
        assert lb < 0 and ub > 0


class TestAckley:
    def test_global_minimum_at_origin_2d(self):
        f = Ackley()
        result = f.evaluate(np.zeros(2))
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_global_minimum_at_origin_5d(self):
        f = Ackley()
        result = f.evaluate(np.zeros(5))
        assert result == pytest.approx(0.0, abs=1e-10)

    def test_positive_at_non_origin(self):
        f = Ackley()
        # Outside origin the function value is positive
        assert f.evaluate(np.array([1.0, 1.0])) > 0.0

    def test_returns_float(self):
        f = Ackley()
        result = f.evaluate(np.array([0.5, -0.5]))
        assert isinstance(result, float)

    def test_suggested_bounds_wide(self):
        lb, ub = Ackley().suggested_bounds
        assert ub - lb >= 60.0  # ±32.768 → range ≥ 60


class TestRegistry:
    def test_get_sphere(self):
        f = get_function("sphere")
        assert isinstance(f, Sphere)

    def test_get_ackley(self):
        f = get_function("ackley")
        assert isinstance(f, Ackley)

    def test_get_unknown_raises(self):
        with pytest.raises(KeyError, match="unknown_func"):
            get_function("unknown_func")

    def test_list_functions_returns_pairs(self):
        result = list_functions()
        assert len(result) >= 2
        keys = [k for k, _ in result]
        assert "sphere" in keys
        assert "ackley" in keys

    def test_get_function_returns_new_instance(self):
        f1 = get_function("sphere")
        f2 = get_function("sphere")
        assert f1 is not f2  # each call returns a fresh instance
