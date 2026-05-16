"""Smoke tests for ExponentialDistributionModule Qt view construction.

Requires a running QApplication (provided by pytest-qt's ``qtbot`` fixture).
These tests only verify that the view builds without crashing and returns
a QWidget — they do not assert rendering correctness.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QDoubleSpinBox, QTabWidget, QWidget

    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False


pytestmark = pytest.mark.skipif(
    not _QT_AVAILABLE, reason="PySide6 not installed"
)

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
# Basic view construction
# ------------------------------------------------------------------


def test_build_view_returns_qwidget(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    assert isinstance(widget, QWidget)
    qtbot.addWidget(widget)


def test_module_id_name_version():
    mod = _make_module()
    assert mod.module_id == "exponential_distribution"
    assert mod.module_name == "Exponential Distribution Explorer"
    assert mod.module_version == "1.0.0"


def test_tab_widget_has_two_tabs(qtbot):
    """The control panel must contain a QTabWidget with exactly 2 tabs."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    tabs = widget.findChildren(QTabWidget)
    assert len(tabs) >= 1
    assert tabs[0].count() == 2


def test_spinboxes_present(qtbot):
    """The view must contain at least one QDoubleSpinBox (μ input)."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    spins = widget.findChildren(QDoubleSpinBox)
    assert len(spins) >= 1


def test_prob_tab_spinboxes_present(qtbot):
    """Tab 2 must expose _xa_spin and _xb_spin for a and b inputs."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    assert mod._xa_spin is not None
    assert mod._xb_spin is not None


# ------------------------------------------------------------------
# State persistence
# ------------------------------------------------------------------


def test_state_round_trip(qtbot):
    """get_state after build_view should return default values."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    state = mod.get_state()
    assert "mu" in state
    assert "tab" in state
    assert "x_a" in state
    assert "x_b" in state


def test_restore_state_syncs_ui(qtbot):
    """restore_state called after build_view should update spinbox values."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    mod.restore_state({"mu": 4.0, "tab": 0, "x_a": 0.5, "x_b": 2.0})
    assert mod._mu_spin is not None
    assert abs(mod._mu_spin.value() - 4.0) < 1e-6
    assert mod._xa_spin is not None
    assert abs(mod._xa_spin.value() - 0.5) < 1e-6


# ------------------------------------------------------------------
# Lifecycle
# ------------------------------------------------------------------


def test_lifecycle_no_crash(qtbot):
    """Full on_load → build_view → on_activate → on_deactivate → on_unload cycle."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    mod.on_activate()
    mod.on_deactivate()
    mod.on_unload()


# ------------------------------------------------------------------
# Tab switching
# ------------------------------------------------------------------


def test_tab_switch_does_not_crash(qtbot):
    """Switching between Tab 0 and Tab 1 must not raise."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    tabs = widget.findChildren(QTabWidget)[0]
    tabs.setCurrentIndex(1)
    tabs.setCurrentIndex(0)
    tabs.setCurrentIndex(1)


# ------------------------------------------------------------------
# Mode panel visibility
# ------------------------------------------------------------------


def test_prob_tab_default_values(qtbot):
    """Tab 2 spinboxes must reflect defaults a=0.0, b=1.0 on construction."""
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    assert mod._xa_spin is not None
    assert mod._xb_spin is not None
    assert abs(mod._xa_spin.value() - 0.0) < 1e-6
    assert abs(mod._xb_spin.value() - 1.0) < 1e-6


def test_prob_tab_no_radio_buttons(qtbot):
    """Tab 2 must not contain radio buttons (always 3-region mode)."""
    from PySide6.QtWidgets import QRadioButton
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    radios = widget.findChildren(QRadioButton)
    assert len(radios) == 0
