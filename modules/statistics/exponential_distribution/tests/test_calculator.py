"""Unit tests for ExponentialDistributionModule computation methods.

Tests are pure (no Qt, no matplotlib rendering): they exercise the two
static computation helpers on ExponentialDistributionModule directly.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest
from scipy.stats import expon

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_STUB_MANIFEST = {
    "id": "exponential_distribution",
    "name": "Exponential Distribution Explorer",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": (
        "modules.statistics.exponential_distribution.entry"
        ":ExponentialDistributionModule"
    ),
    "category": "statistics",
    "author": "IIMP Team",
    "permissions": [
        "storage.read",
        "storage.write",
        "export.file",
        "settings.read",
        "settings.write",
    ],
}


def _make_module():
    from modules.statistics.exponential_distribution.module import (
        ExponentialDistributionModule,
    )

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.export_service = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    return ExponentialDistributionModule(manifest=_STUB_MANIFEST, context=ctx)


# ------------------------------------------------------------------
# Tests — _compute_single  (Tab 2: CDF / SF modes)
# ------------------------------------------------------------------


class TestComputeSingle:
    """P(X≤x) and P(X>x) for Exp(μ)."""

    def test_p_at_mean_mu1(self):
        """For Exp(1): P(X≤1) = 1 − 1/e ≈ 0.6321."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        p_cdf, p_sf = ExponentialDistributionModule._compute_single(mu=1.0, x=1.0)
        expected = float(1.0 - np.exp(-1.0))
        assert abs(p_cdf - expected) < 1e-9
        assert abs(p_cdf + p_sf - 1.0) < 1e-12

    def test_p_at_zero_is_zero_cdf(self):
        """P(X≤0) = 0 for any μ."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        p_cdf, p_sf = ExponentialDistributionModule._compute_single(mu=2.0, x=0.0)
        assert abs(p_cdf) < 1e-12
        assert abs(p_sf - 1.0) < 1e-12

    def test_negative_x_clamped_to_zero(self):
        """x < 0 is treated as x = 0."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        p_cdf, _ = ExponentialDistributionModule._compute_single(mu=1.0, x=-5.0)
        assert abs(p_cdf) < 1e-12

    def test_complement_property(self):
        """P(X≤x) + P(X>x) = 1 for all x, μ."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        for mu, x in [(1.0, 0.5), (3.0, 2.5), (0.1, 0.05), (100.0, 70.0)]:
            p_cdf, p_sf = ExponentialDistributionModule._compute_single(mu=mu, x=x)
            assert abs(p_cdf + p_sf - 1.0) < 1e-12, f"failed for mu={mu}, x={x}"

    def test_larger_mu_smaller_cdf(self):
        """For fixed x, larger μ → smaller CDF (slower decay)."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        p1, _ = ExponentialDistributionModule._compute_single(mu=1.0, x=1.0)
        p2, _ = ExponentialDistributionModule._compute_single(mu=5.0, x=1.0)
        assert p1 > p2

    def test_large_x_cdf_near_one(self):
        """P(X≤50μ) is essentially 1."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        p_cdf, _ = ExponentialDistributionModule._compute_single(mu=1.0, x=50.0)
        assert p_cdf > 0.9999

    def test_matches_scipy(self):
        """Results must agree with scipy.stats.expon."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        mu, x = 2.5, 1.8
        p_cdf, p_sf = ExponentialDistributionModule._compute_single(mu=mu, x=x)
        assert abs(p_cdf - float(expon.cdf(x, scale=mu))) < 1e-9
        assert abs(p_sf - float(expon.sf(x, scale=mu))) < 1e-9

    def test_memoryless_property(self):
        """P(X>s+t) / P(X>s) == P(X>t) — memoryless property."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        mu, s, t = 2.0, 1.0, 3.0
        _, p_sf_s = ExponentialDistributionModule._compute_single(mu=mu, x=s)
        _, p_sf_st = ExponentialDistributionModule._compute_single(mu=mu, x=s + t)
        _, p_sf_t = ExponentialDistributionModule._compute_single(mu=mu, x=t)
        # P(X>s+t | X>s) = P(X>s+t)/P(X>s)
        conditional = p_sf_st / p_sf_s
        assert abs(conditional - p_sf_t) < 1e-9


# ------------------------------------------------------------------
# Tests — _compute_interval  (Tab 2: interval mode)
# ------------------------------------------------------------------


class TestComputeInterval:
    """P(X<a), P(a≤X≤b), P(X>b) for Exp(μ)."""

    def test_partition_sums_to_one(self):
        """The three regions always sum to 1."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        for mu, a, b in [(1.0, 0.5, 2.0), (3.0, 1.0, 5.0), (0.5, 0.1, 0.8)]:
            p_l, p_m, p_r = ExponentialDistributionModule._compute_interval(
                mu=mu, a=a, b=b
            )
            assert abs(p_l + p_m + p_r - 1.0) < 1e-11, (
                f"partition failed for mu={mu}, a={a}, b={b}"
            )

    def test_a_at_zero_p_left_is_zero(self):
        """When a=0, P(X<a) = 0."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        p_l, _, _ = ExponentialDistributionModule._compute_interval(
            mu=1.0, a=0.0, b=2.0
        )
        assert abs(p_l) < 1e-12

    def test_a_equals_b_mid_is_zero(self):
        """When a == b, P(a≤X≤b) = 0 (point has zero measure)."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        _, p_m, _ = ExponentialDistributionModule._compute_interval(
            mu=1.0, a=1.0, b=1.0
        )
        assert abs(p_m) < 1e-12

    def test_negative_a_clamped_to_zero(self):
        """a < 0 must be clamped → P(X<0) = 0."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        p_l, p_m, p_r = ExponentialDistributionModule._compute_interval(
            mu=1.0, a=-3.0, b=2.0
        )
        assert abs(p_l) < 1e-12  # a clamped to 0

    def test_b_less_than_a_clamped(self):
        """b < a must be clamped to a → P(a≤X≤b) = 0."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        _, p_m, _ = ExponentialDistributionModule._compute_interval(
            mu=1.0, a=3.0, b=1.0  # b < a
        )
        assert abs(p_m) < 1e-12

    def test_very_large_b_p_right_near_zero(self):
        """When b is very large, P(X>b) ≈ 0."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        _, _, p_r = ExponentialDistributionModule._compute_interval(
            mu=1.0, a=0.5, b=100.0
        )
        assert p_r < 1e-40

    def test_matches_scipy(self):
        """Results must agree with scipy.stats.expon."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        mu, a, b = 2.0, 0.8, 3.5
        p_l, p_m, p_r = ExponentialDistributionModule._compute_interval(
            mu=mu, a=a, b=b
        )
        assert abs(p_l - float(expon.cdf(a, scale=mu))) < 1e-9
        assert abs(
            p_m - float(expon.cdf(b, scale=mu) - expon.cdf(a, scale=mu))
        ) < 1e-9
        assert abs(p_r - float(expon.sf(b, scale=mu))) < 1e-9


# ------------------------------------------------------------------
# Tests — state management
# ------------------------------------------------------------------


class TestState:
    def test_get_state_returns_defaults(self):
        mod = _make_module()
        state = mod.get_state()
        assert abs(state["mu"] - 1.0) < 1e-9
        assert state["tab"] == 0
        assert abs(state["x_a"] - 0.0) < 1e-9
        assert abs(state["x_b"] - 1.0) < 1e-9
        assert state["precision"] == 4

    def test_restore_state_updates_fields(self):
        mod = _make_module()
        mod.restore_state(
            {
                "mu": 3.0,
                "tab": 1,
                "x_a": 1.0,
                "x_b": 4.0,
                "precision": 6,
            }
        )
        assert abs(mod._mu - 3.0) < 1e-9
        assert mod._tab == 1
        assert abs(mod._x_a - 1.0) < 1e-9
        assert abs(mod._x_b - 4.0) < 1e-9
        assert mod._precision == 6

    def test_restore_state_clamps_mu(self):
        """mu is clamped to ≥ 0.001."""
        mod = _make_module()
        mod.restore_state({"mu": -10.0})
        assert mod._mu >= 0.001

    def test_restore_state_clamps_x_values(self):
        """Negative x values are clamped to 0."""
        mod = _make_module()
        mod.restore_state({"x_a": -2.0, "x_b": -1.0})
        assert mod._x_a >= 0.0
        assert mod._x_b >= mod._x_a

    def test_get_set_state_round_trip(self):
        """round-trip: restore_state → get_state preserves values."""
        mod = _make_module()
        original = {
            "mu": 5.0,
            "tab": 1,
            "x_a": 1.5,
            "x_b": 6.0,
            "precision": 5,
        }
        mod.restore_state(original)
        recovered = mod.get_state()
        for key in original:
            if isinstance(original[key], float):
                assert abs(recovered[key] - original[key]) < 1e-9, key
            else:
                assert recovered[key] == original[key], key

    def test_on_load_reads_precision_setting(self):
        """on_load picks up 'precision' from settings_service."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        ctx = MagicMock()
        ctx.logger = MagicMock()
        ctx.export_service = MagicMock()
        ctx.settings_service = MagicMock()
        ctx.settings_service.get_module_setting.return_value = "6"
        ctx.activity_service = MagicMock()
        mod = ExponentialDistributionModule(manifest=_STUB_MANIFEST, context=ctx)
        mod.on_load()
        assert mod._precision == 6

    def test_on_load_ignores_invalid_precision(self):
        """on_load gracefully ignores non-integer precision values."""
        from modules.statistics.exponential_distribution.module import (
            ExponentialDistributionModule,
        )

        ctx = MagicMock()
        ctx.logger = MagicMock()
        ctx.export_service = MagicMock()
        ctx.settings_service = MagicMock()
        ctx.settings_service.get_module_setting.return_value = "not_a_number"
        ctx.activity_service = MagicMock()
        mod = ExponentialDistributionModule(manifest=_STUB_MANIFEST, context=ctx)
        mod.on_load()
        assert mod._precision == 4  # default unchanged
