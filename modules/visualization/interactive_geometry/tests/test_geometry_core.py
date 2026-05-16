"""Unit tests for Interactive Geometry Explorer — pure-numpy geometry core.

All tests are headless-safe: no Qt, no matplotlib rendering required.
Tests cover compute_surface() for all five shapes and surface_stats().
"""
from __future__ import annotations

import numpy as np
import pytest

from modules.visualization.interactive_geometry.module import (
    COLORMAPS,
    RESOLUTION,
    SHAPES,
    compute_surface,
    surface_stats,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_shapes_tuple(self):
        assert set(SHAPES) == {"sine_2d", "paraboloid", "saddle", "sphere", "torus"}

    def test_resolution_keys(self):
        assert set(RESOLUTION.keys()) == {"low", "medium", "high"}

    def test_resolution_values_positive(self):
        for v in RESOLUTION.values():
            assert v > 0

    def test_colormaps_not_empty(self):
        assert len(COLORMAPS) >= 5


# ---------------------------------------------------------------------------
# compute_surface — shape tests with default n
# ---------------------------------------------------------------------------


class TestComputeSurface:
    @pytest.mark.parametrize("shape", SHAPES)
    def test_returns_three_arrays(self, shape):
        X, Y, Z = compute_surface(shape)
        assert isinstance(X, np.ndarray)
        assert isinstance(Y, np.ndarray)
        assert isinstance(Z, np.ndarray)

    @pytest.mark.parametrize("shape", SHAPES)
    def test_shapes_consistent(self, shape):
        """X, Y, Z must all have the same shape (n × n)."""
        X, Y, Z = compute_surface(shape, n=20)
        assert X.shape == Y.shape == Z.shape

    @pytest.mark.parametrize("shape", SHAPES)
    def test_no_nans(self, shape):
        X, Y, Z = compute_surface(shape, n=20)
        assert not np.any(np.isnan(Z)), f"NaN found in Z for shape={shape!r}"

    @pytest.mark.parametrize("shape", SHAPES)
    def test_no_infs(self, shape):
        X, Y, Z = compute_surface(shape, n=20)
        assert not np.any(np.isinf(Z)), f"Inf found in Z for shape={shape!r}"

    def test_unknown_shape_raises(self):
        with pytest.raises(ValueError, match="Unknown shape"):
            compute_surface("nonsense")


class TestSinc:
    def test_centre_equals_one(self):
        """Z at the origin (r=0) must be 1.0 (limit of sinc)."""
        X, Y, Z = compute_surface("sine_2d", n=61)
        # grid is symmetric: centre index = n//2
        centre = 61 // 2
        assert abs(Z[centre, centre] - 1.0) < 1e-9

    def test_z_bounded(self):
        _, _, Z = compute_surface("sine_2d", n=60)
        assert np.min(Z) >= -1.0
        assert np.max(Z) <= 1.0 + 1e-9


class TestParaboloid:
    def test_minimum_at_origin(self):
        """Z = X² + Y² has its minimum at (0,0)."""
        X, Y, Z = compute_surface("paraboloid", n=61)
        c = 61 // 2
        assert Z[c, c] == pytest.approx(0.0, abs=1e-9)

    def test_z_non_negative(self):
        _, _, Z = compute_surface("paraboloid", n=30)
        assert np.all(Z >= 0.0)


class TestSaddle:
    def test_zero_at_origin(self):
        """Z = X² - Y² is 0 at (0, 0)."""
        X, Y, Z = compute_surface("saddle", n=61)
        c = 61 // 2
        assert Z[c, c] == pytest.approx(0.0, abs=1e-9)

    def test_has_positive_and_negative_z(self):
        _, _, Z = compute_surface("saddle", n=30)
        assert np.any(Z > 0)
        assert np.any(Z < 0)


class TestSphere:
    def test_unit_sphere_radius(self):
        """All points on the unit sphere satisfy X²+Y²+Z²=1."""
        X, Y, Z = compute_surface("sphere", n=30)
        R2 = X**2 + Y**2 + Z**2
        assert np.allclose(R2, 1.0, atol=1e-10)

    def test_z_range(self):
        _, _, Z = compute_surface("sphere", n=30)
        assert np.min(Z) >= -1.0 - 1e-10
        assert np.max(Z) <= 1.0 + 1e-10


class TestTorus:
    def test_z_range(self):
        """Z values on torus (R=3, r=1) are in [-1, 1]."""
        _, _, Z = compute_surface("torus", n=30)
        assert np.min(Z) >= -1.0 - 1e-9
        assert np.max(Z) <= 1.0 + 1e-9

    def test_xy_ring_radius(self):
        """Points on torus: √(X²+Y²) ∈ [R-r, R+r] = [2, 4]."""
        X, Y, _ = compute_surface("torus", n=40)
        Rxy = np.sqrt(X**2 + Y**2)
        assert np.min(Rxy) >= 2.0 - 1e-9
        assert np.max(Rxy) <= 4.0 + 1e-9


# ---------------------------------------------------------------------------
# surface_stats
# ---------------------------------------------------------------------------


class TestSurfaceStats:
    @pytest.mark.parametrize("shape", SHAPES)
    def test_returns_expected_keys(self, shape):
        X, Y, Z = compute_surface(shape, n=20)
        stats = surface_stats(X, Y, Z)
        assert set(stats.keys()) == {"z_min", "z_max", "z_mean", "z_std", "x_range", "y_range"}

    @pytest.mark.parametrize("shape", SHAPES)
    def test_all_values_are_floats(self, shape):
        X, Y, Z = compute_surface(shape, n=20)
        stats = surface_stats(X, Y, Z)
        for k, v in stats.items():
            assert isinstance(v, float), f"{k} is not float"

    def test_z_min_leq_z_max(self):
        for shape in SHAPES:
            X, Y, Z = compute_surface(shape, n=20)
            s = surface_stats(X, Y, Z)
            assert s["z_min"] <= s["z_max"]

    def test_paraboloid_z_min_approx_zero(self):
        X, Y, Z = compute_surface("paraboloid", n=61)
        stats = surface_stats(X, Y, Z)
        assert stats["z_min"] == pytest.approx(0.0, abs=1e-9)


# ---------------------------------------------------------------------------
# Resolution mapping
# ---------------------------------------------------------------------------


class TestResolution:
    def test_low_resolution(self):
        n = RESOLUTION["low"]
        X, Y, Z = compute_surface("paraboloid", n=n)
        assert X.shape == (n, n)

    def test_high_resolution(self):
        n = RESOLUTION["high"]
        X, Y, Z = compute_surface("sine_2d", n=n)
        assert X.shape == (n, n)
