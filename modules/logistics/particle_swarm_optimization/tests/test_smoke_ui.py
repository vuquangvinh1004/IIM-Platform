"""Smoke tests for the PSO module Qt view construction.

Requires PySide6 — skipped gracefully when not available.
Tests only verify that the view builds without crashing and returns
a valid QWidget; they do not assert rendering correctness.
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
    "id": "particle_swarm_optimization",
    "name": "PSO — Tối ưu hóa Bầy đàn",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": (
        "modules.logistics.particle_swarm_optimization"
        ".entry:ParticleSwarmOptimizationModule"
    ),
    "category": "quantitative_methods",
    "author": "IIMP Team",
    "permissions": ["storage.read", "storage.write", "export.file"],
}


def _make_module():
    from modules.logistics.particle_swarm_optimization.module import (
        ParticleSwarmOptimizationModule,
    )
    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.export_service = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    return ParticleSwarmOptimizationModule(manifest=_STUB_MANIFEST, context=ctx)


def test_build_view_returns_qwidget(qtbot):
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    assert isinstance(view, QWidget)
    qtbot.addWidget(view)


def test_build_view_idempotent(qtbot):
    """build_view() called twice must return the same widget instance."""
    mod = _make_module()
    mod.on_load()
    v1 = mod.build_view()
    v2 = mod.build_view()
    assert v1 is v2
    qtbot.addWidget(v1)


def test_view_has_two_tabs(qtbot):
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    qtbot.addWidget(view)
    tabs = view.findChildren(QTabWidget)
    assert len(tabs) >= 1
    assert tabs[0].count() == 2


def test_on_lifecycle_no_crash(qtbot):
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    qtbot.addWidget(view)
    mod.on_activate()
    mod.on_deactivate()
    mod.on_unload()


def test_get_state_returns_dict(qtbot):
    mod = _make_module()
    mod.on_load()
    mod.build_view()
    state = mod.get_state()
    assert isinstance(state, dict)
    assert "_state_version" in state
    # New trajectory/display fields must be present
    assert "step_delay_ms" in state
    assert "view_mode" in state
    assert "n_display_particles" in state
    assert "tail_length" in state


def test_restore_state_no_crash(qtbot):
    mod = _make_module()
    mod.on_load()
    mod.build_view()
    state = mod.get_state()
    state["last_convergence"] = [10.0, 8.0, 5.0, 2.0, 0.5]
    state["last_gbest_fitness"] = 0.5
    state["last_gbest_position"] = [0.01, -0.02]
    # Verify all three view modes restore without error
    for mode in ("animation", "full_trail", "short_tail"):
        state["view_mode"] = mode
        mod.restore_state(state)  # must not raise


def test_set_view_mode_updates_buttons(qtbot):
    """_set_view_mode() must update button states and tail_len enable correctly."""
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    qtbot.addWidget(view)
    pso_view = mod._view
    for mode, expect_tail_enabled in (
        ("animation", False),
        ("full_trail", False),
        ("short_tail", True),
    ):
        pso_view._set_view_mode(mode)
        assert pso_view._view_mode == mode
        assert pso_view._btn_mode_anim.isChecked() == (mode == "animation")
        assert pso_view._btn_mode_full.isChecked() == (mode == "full_trail")
        assert pso_view._btn_mode_tail.isChecked() == (mode == "short_tail")
        assert pso_view._spin_tail_len.isEnabled() == expect_tail_enabled


def test_trajectory_display_controls_exist(qtbot):
    """Display group controls must be present with correct defaults."""
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    qtbot.addWidget(view)
    pso_view = mod._view
    assert pso_view._spin_delay.value() == 50          # _DEFAULT_DELAY_MS
    assert pso_view._spin_n_display.value() == 0       # 0 = all particles
    assert pso_view._spin_tail_len.value() == 10       # default tail length
    assert pso_view._view_mode == "animation"
