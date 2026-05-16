"""test_smoke_ui.py — Smoke tests for PSOLogisticsModule UI (requires PySide6)."""
from __future__ import annotations

import pytest

try:
    from PySide6.QtWidgets import QApplication, QTabWidget, QWidget
    _QT = True
except ImportError:
    _QT = False

pytestmark = pytest.mark.skipif(not _QT, reason="PySide6 not available")

# ── QApplication fixture ──────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def app():
    import sys
    existing = QApplication.instance()
    if existing:
        yield existing
    else:
        a = QApplication(sys.argv)
        yield a
        # do NOT call a.quit() — let pytest-qt or the process handle it


# ── Module context stub ───────────────────────────────────────────────────────


class _StubLogger:
    def info(self, *a): pass
    def debug(self, *a): pass
    def warning(self, *a): pass
    def error(self, *a): pass


class _StubExportSvc:
    def ask_save_path(self, parent, **kwargs): return None
    def write_bytes(self, path, data): pass


class _StubSettingsSvc:
    def get(self, key, default=None): return default
    def set(self, key, value): pass


class _StubActivitySvc:
    def log(self, *a, **kw): pass


class _StubContext:
    logger = _StubLogger()
    export_service = _StubExportSvc()
    settings_service = _StubSettingsSvc()
    activity_service = _StubActivitySvc()


def _make_manifest() -> dict:
    return {
        "id": "pso_logistics",
        "name": "PSO Logistics",
        "version": "1.0.0",
        "sdk_version": "1.0.0",
    }


def _make_module():
    from modules.logistics.pso_logistics.module import PSOLogisticsModule
    return PSOLogisticsModule(manifest=_make_manifest(), context=_StubContext())


# ── tests ─────────────────────────────────────────────────────────────────────


def test_build_view_returns_qwidget(app):
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    assert isinstance(view, QWidget)


def test_build_view_idempotent(app):
    """Second call returns same object."""
    mod = _make_module()
    mod.on_load()
    v1 = mod.build_view()
    v2 = mod.build_view()
    assert v1 is v2


def test_view_has_two_inner_tabs(app):
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    # _tabs is a QTabWidget with 3 tabs: map + convergence + swarm view
    tabs = view.findChild(QTabWidget)
    assert tabs is not None
    assert tabs.count() == 3


def test_lifecycle_no_crash(app):
    """Full lifecycle: on_load → build_view → on_activate → on_deactivate → on_unload."""
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    assert view is not None
    mod.on_activate()
    mod.on_deactivate()
    mod.on_unload()  # should stop any running worker gracefully


def test_get_state_contains_required_keys(app):
    mod = _make_module()
    mod.on_load()
    mod.build_view()
    state = mod.get_state()
    assert "_state_version" in state
    assert state["_state_version"] == "1.0.0"
    assert "n_customers" in state
    assert "n_particles" in state
    assert "n_iterations" in state


def test_restore_state_no_crash(app):
    mod = _make_module()
    mod.on_load()
    mod.build_view()
    state = mod.get_state()
    state["n_customers"] = 12
    state["n_iterations"] = 150
    mod.restore_state(state)
    restored_state = mod.get_state()
    assert restored_state["n_customers"] == 12
    assert restored_state["n_iterations"] == 150
