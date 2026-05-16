"""Smoke-test for NormalDistributionModule v2.0.0 Qt view construction.

Requires a running QApplication (provided by pytest-qt's ``qtbot`` fixture).
These tests only verify that the view builds without crashing and returns
a QWidget — they do not assert rendering correctness.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QWidget, QTabWidget
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False


pytestmark = pytest.mark.skipif(not _QT_AVAILABLE, reason="PySide6 not installed")


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


def test_build_view_returns_qwidget(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    assert isinstance(widget, QWidget)
    qtbot.addWidget(widget)


def test_module_id_and_name():
    mod = _make_module()
    assert mod.module_id == "normal_distribution"
    assert mod.module_name == "Normal Distribution Explorer"
    assert mod.module_version == "3.0.0"


def test_tab_widget_has_three_tabs(qtbot):
    """The control panel must contain a QTabWidget with exactly 3 tabs."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    tabs = widget.findChildren(QTabWidget)
    assert len(tabs) >= 1
    assert tabs[0].count() == 3


def test_state_round_trip(qtbot):
    """get_state after restore_state should return the same values."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    desired = {
        "mu": 3.5, "sigma": 1.5, "tab": 2,
        "alpha_l": 0.01, "alpha_r": 0.05,
        "z_l": -2.0, "z_r": 2.0,
        "z_input_mode": "z", "precision": 5,
    }
    mod.restore_state(desired)
    recovered = mod.get_state()
    assert abs(recovered["mu"] - 3.5) < 1e-6
    assert abs(recovered["sigma"] - 1.5) < 1e-6
    assert recovered["tab"] == 2
    assert recovered["precision"] == 5


def test_lifecycle_no_crash(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    mod.on_activate()
    mod.on_deactivate()
    mod.on_unload()

    assert mod.module_version == "3.0.0"


def test_lifecycle_no_exception(qtbot):
    """Full lifecycle: load → build_view → activate → deactivate → unload."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    mod.on_activate()
    mod.on_deactivate()
    mod.on_unload()


# ------------------------------------------------------------------
# Mode 1 overlay smoke tests
# ------------------------------------------------------------------


def test_overlay_add_increases_dist_count(qtbot):
    """Adding an overlay distribution via _on_add_dist_clicked grows the list."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    assert len(mod._overlay_dists) == 0
    # Simulate setting spinbox values and clicking Add
    if mod._mu_add_spin is not None:
        mod._mu_add_spin.setValue(2.0)
    if mod._sigma_add_spin is not None:
        mod._sigma_add_spin.setValue(0.5)
    mod._on_add_dist_clicked()
    assert len(mod._overlay_dists) == 1
    assert abs(mod._overlay_dists[0][0] - 2.0) < 1e-6
    assert abs(mod._overlay_dists[0][1] - 0.5) < 1e-6


def test_overlay_remove_clears_entry(qtbot):
    """Removing an overlay entry decreases the list by one."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    mod._on_add_dist_clicked()
    mod._on_add_dist_clicked()
    assert len(mod._overlay_dists) == 2
    mod._on_remove_dist_clicked(0)
    assert len(mod._overlay_dists) == 1


def test_overlay_clear_empties_list(qtbot):
    """Clear-all removes all overlay distributions."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    for _ in range(3):
        mod._on_add_dist_clicked()
    assert len(mod._overlay_dists) == 3
    mod._on_clear_dists_clicked()
    assert mod._overlay_dists == []


def test_overlay_max_seven(qtbot):
    """Cannot add more than 7 overlays."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    for _ in range(10):
        mod._on_add_dist_clicked()
    assert len(mod._overlay_dists) == 7


def test_overlay_state_round_trip(qtbot):
    """Overlay distributions survive a get_state / restore_state cycle."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    if mod._mu_add_spin is not None:
        mod._mu_add_spin.setValue(3.0)
    if mod._sigma_add_spin is not None:
        mod._sigma_add_spin.setValue(1.5)
    mod._on_add_dist_clicked()

    state = mod.get_state()
    assert len(state["overlay_dists"]) == 1

    mod2 = _make_module()
    mod2.restore_state(state)
    assert len(mod2._overlay_dists) == 1
    assert abs(mod2._overlay_dists[0][0] - 3.0) < 1e-6
    assert abs(mod2._overlay_dists[0][1] - 1.5) < 1e-6
