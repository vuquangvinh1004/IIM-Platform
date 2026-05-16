"""Unit tests for NormalDistributionModule v2.0.0 computation methods.

Tests are kept pure (no Qt, no matplotlib rendering) by exercising the two
static computation helpers on NormalDistributionModule directly.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from scipy.stats import norm

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

_STUB_MANIFEST = {
    "id": "normal_distribution",
    "name": "Normal Distribution Explorer",
    "version": "3.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.statistics.normal_distribution.entry:NormalDistributionModule",
    "category": "statistics",
    "author": "IIMP Team",
    "permissions": ["storage.read", "storage.write", "export.file", "settings.read", "settings.write"],
}


def _make_module():
    from modules.statistics.normal_distribution.module import NormalDistributionModule

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.export_service = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    return NormalDistributionModule(manifest=_STUB_MANIFEST, context=ctx)


# ------------------------------------------------------------------
# Tests — _compute_alpha_to_z  (Mode 2: α → Z)
# ------------------------------------------------------------------


class TestComputeAlphaToZ:
    """Given tail probabilities, find critical Z and X values."""

    def test_standard_normal_symmetric(self):
        """For N(0,1), z = norm.ppf(alpha) and x == z."""
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        z_l, z_r, x_l, x_r, area_m = NormalDistributionModule._compute_alpha_to_z(
            mu=0.0, sigma=1.0, alpha_l=0.025, alpha_r=0.025
        )
        assert abs(z_l - norm.ppf(0.025)) < 1e-9
        assert abs(z_r - norm.ppf(0.975)) < 1e-9
        assert abs(x_l - z_l) < 1e-9   # x == z when mu=0, sigma=1
        assert abs(x_r - z_r) < 1e-9
        assert abs(area_m - 0.95) < 1e-9

    def test_area_m_is_complement(self):
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        z_l, z_r, x_l, x_r, area_m = NormalDistributionModule._compute_alpha_to_z(
            mu=0.0, sigma=1.0, alpha_l=0.05, alpha_r=0.05
        )
        assert abs(area_m - 0.90) < 1e-9
        assert abs(0.05 + 0.05 + area_m - 1.0) < 1e-9

    def test_general_normal_x_values(self):
        """For N(mu, sigma), X = mu + sigma * z."""
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        mu, sigma = 5.0, 2.0
        z_l, z_r, x_l, x_r, area_m = NormalDistributionModule._compute_alpha_to_z(
            mu=mu, sigma=sigma, alpha_l=0.025, alpha_r=0.025
        )
        expected_z_l = norm.ppf(0.025)
        assert abs(z_l - expected_z_l) < 1e-9
        assert abs(x_l - (mu + sigma * expected_z_l)) < 1e-9
        assert abs(x_r - (mu + sigma * norm.ppf(0.975))) < 1e-9

    def test_asymmetric_tails(self):
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        z_l, z_r, x_l, x_r, area_m = NormalDistributionModule._compute_alpha_to_z(
            mu=0.0, sigma=1.0, alpha_l=0.01, alpha_r=0.05
        )
        assert abs(z_l - norm.ppf(0.01)) < 1e-9
        assert abs(z_r - norm.ppf(0.95)) < 1e-9
        assert abs(area_m - (1.0 - 0.01 - 0.05)) < 1e-9

    def test_small_alpha(self):
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        z_l, z_r, x_l, x_r, area_m = NormalDistributionModule._compute_alpha_to_z(
            mu=0.0, sigma=1.0, alpha_l=0.00001, alpha_r=0.05
        )
        assert z_l < -4.0  # very far left


# ------------------------------------------------------------------
# Tests — _compute_z_to_alpha  (Mode 3: Z/X → α)
# ------------------------------------------------------------------


class TestComputeZToAlpha:
    """Given critical values (Z or X), find probability areas."""

    def test_standard_normal_z_mode(self):
        """For N(0,1) with z=-1.96, 1.96 → area_m ≈ 0.95."""
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        z_l, z_r, x_l, x_r, area_l, area_r, area_m = NormalDistributionModule._compute_z_to_alpha(
            mu=0.0, sigma=1.0, val_l=-1.96, val_r=1.96, input_mode="z"
        )
        assert abs(z_l - (-1.96)) < 1e-9
        assert abs(z_r - 1.96) < 1e-9
        assert abs(area_l - norm.cdf(-1.96)) < 1e-9
        assert abs(area_r - (1 - norm.cdf(1.96))) < 1e-9
        assert abs(area_m - 0.95) < 0.001

    def test_areas_sum_to_one(self):
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        _, _, _, _, area_l, area_r, area_m = NormalDistributionModule._compute_z_to_alpha(
            mu=0.0, sigma=1.0, val_l=-2.0, val_r=2.0, input_mode="z"
        )
        assert abs(area_l + area_r + area_m - 1.0) < 1e-9

    def test_x_mode_standard_normal(self):
        """For N(0,1) X mode: x values equal z values."""
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        z_l, z_r, x_l, x_r, area_l, area_r, area_m = NormalDistributionModule._compute_z_to_alpha(
            mu=0.0, sigma=1.0, val_l=-1.96, val_r=1.96, input_mode="x"
        )
        assert abs(z_l - (-1.96)) < 1e-9
        assert abs(z_r - 1.96) < 1e-9
        assert abs(area_m - 0.95) < 0.001

    def test_x_mode_general_normal(self):
        """For N(mu, sigma) X mode: z = (x - mu) / sigma."""
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        mu, sigma = 5.0, 2.0
        # X criticals corresponding to z = +-1.96
        x_crit_l = float(mu + sigma * norm.ppf(0.025))
        x_crit_r = float(mu + sigma * norm.ppf(0.975))
        z_l, z_r, x_l, x_r, area_l, area_r, area_m = NormalDistributionModule._compute_z_to_alpha(
            mu=mu, sigma=sigma, val_l=x_crit_l, val_r=x_crit_r, input_mode="x"
        )
        assert abs(z_l - norm.ppf(0.025)) < 1e-6
        assert abs(z_r - norm.ppf(0.975)) < 1e-6
        assert abs(area_m - 0.95) < 0.001

    def test_swap_when_val_l_greater_than_val_r(self):
        """If val_l > val_r, values should be swapped internally."""
        from modules.statistics.normal_distribution.module import NormalDistributionModule

        z_l_a, z_r_a, _, _, area_l_a, area_r_a, area_m_a = NormalDistributionModule._compute_z_to_alpha(
            mu=0.0, sigma=1.0, val_l=-1.96, val_r=1.96, input_mode="z"
        )
        # Reversed inputs should produce the same result after swap
        z_l_b, z_r_b, _, _, area_l_b, area_r_b, area_m_b = NormalDistributionModule._compute_z_to_alpha(
            mu=0.0, sigma=1.0, val_l=1.96, val_r=-1.96, input_mode="z"
        )
        assert abs(z_l_a - z_l_b) < 1e-9
        assert abs(z_r_a - z_r_b) < 1e-9
        assert abs(area_m_a - area_m_b) < 1e-9


# ------------------------------------------------------------------
# Tests — state
# ------------------------------------------------------------------


class TestState:
    def test_get_state_returns_defaults(self):
        mod = _make_module()
        state = mod.get_state()
        assert state["mu"] == 0.0
        assert state["sigma"] == 1.0
        assert state["tab"] == 0
        assert state["alpha_l"] == 0.025
        assert state["alpha_r"] == 0.025
        assert state["z_l"] == -1.96
        assert state["z_r"] == 1.96
        assert state["z_input_mode"] == "z"
        assert state["precision"] == 4

    def test_restore_state_updates_fields(self):
        mod = _make_module()
        mod.restore_state({
            "mu": 5.0,
            "sigma": 2.0,
            "tab": 1,
            "alpha_l": 0.01,
            "alpha_r": 0.01,
            "z_l": -2.326,
            "z_r": 2.326,
            "z_input_mode": "x",
            "precision": 5,
        })
        assert mod._mu == 5.0
        assert mod._sigma == 2.0
        assert mod._tab == 1
        assert abs(mod._alpha_l - 0.01) < 1e-9
        assert mod._z_input_mode == "x"
        assert mod._precision == 5

    def test_restore_state_guards_sigma_zero(self):
        mod = _make_module()
        mod.restore_state({"mu": 0.0, "sigma": 0.0})
        assert mod._sigma >= 0.001  # Must be clamped


# ------------------------------------------------------------------
# Tests — overlay_dists state  (Mode 1 multi-distribution)
# ------------------------------------------------------------------


class TestOverlayState:
    """State round-trip tests for the Mode 1 overlay distribution list."""

    def test_get_state_includes_overlay_dists_key(self):
        mod = _make_module()
        state = mod.get_state()
        assert "overlay_dists" in state
        assert state["overlay_dists"] == []

    def test_restore_state_overlay_dists_round_trip(self):
        mod = _make_module()
        overlays = [(1.0, 0.5), (-2.0, 2.0)]
        mod.restore_state({"overlay_dists": overlays})
        assert mod._overlay_dists == [(1.0, 0.5), (-2.0, 2.0)]
        state = mod.get_state()
        assert state["overlay_dists"] == [(1.0, 0.5), (-2.0, 2.0)]

    def test_restore_state_overlay_dists_capped_at_seven(self):
        mod = _make_module()
        many = [(float(i), 1.0) for i in range(10)]
        mod.restore_state({"overlay_dists": many})
        assert len(mod._overlay_dists) == 7

    def test_restore_state_overlay_sigma_clamped(self):
        mod = _make_module()
        mod.restore_state({"overlay_dists": [(0.0, 0.0), (1.0, -5.0)]})
        for _mu, sigma in mod._overlay_dists:
            assert sigma >= 0.001

    def test_restore_state_missing_overlay_dists_defaults_to_empty(self):
        mod = _make_module()
        mod.restore_state({"mu": 1.0, "sigma": 1.5})
        assert mod._overlay_dists == []


# ------------------------------------------------------------------
# Tests — render_multi_distribution (headless — pure-logic paths)
# ------------------------------------------------------------------


class TestRenderMultiDistributionHeadless:
    """Test the delegate / early-exit paths that don't require Qt or matplotlib."""

    def _make_canvas_stub(self):
        """Return a _NormalCurveCanvas-like object without Qt/MPL."""
        from modules.statistics.normal_distribution.module import _NormalCurveCanvas

        # Force _QT=False path: _CanvasBase is 'object'
        import modules.statistics.normal_distribution.module as m

        original_qt = m._QT
        original_mpl = m._MPL

        try:
            m._QT = False
            m._MPL = False
            canvas = _NormalCurveCanvas.__new__(_NormalCurveCanvas)
        finally:
            m._QT = original_qt
            m._MPL = original_mpl

        return canvas

    def test_empty_list_returns_empty_string(self):
        canvas = self._make_canvas_stub()
        result = canvas.render_multi_distribution([])
        assert result == ""

    def test_no_mpl_returns_empty_string_for_multi(self):
        import modules.statistics.normal_distribution.module as m

        canvas = self._make_canvas_stub()
        original_mpl = m._MPL
        try:
            m._MPL = False
            result = canvas.render_multi_distribution([(0.0, 1.0), (1.0, 0.5)])
        finally:
            m._MPL = original_mpl
        assert result == ""
