"""Smoke tests for InteractiveGeometryModule Qt view construction.

Requires a running QApplication (provided by pytest-qt's ``qtbot`` fixture).
These tests verify build_view() returns a QWidget without crashing.
Skipped automatically when PySide6 is not installed.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QWidget
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False


pytestmark = pytest.mark.skipif(not _QT_AVAILABLE, reason="PySide6 not installed")

_STUB_MANIFEST = {
    "id": "interactive_geometry",
    "name": "Interactive Geometry Explorer",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.visualization.interactive_geometry.entry:InteractiveGeometryModule",
    "category": "visualization",
    "author": "IIMP Team",
    "permissions": ["storage.read", "storage.write", "export.file", "settings.read", "settings.write"],
    "default_settings": {
        "default_shape": "paraboloid",
        "default_colormap": "plasma",
        "default_elevation": 25,
        "default_azimuth": -45,
    },
}


def _make_module():
    from modules.visualization.interactive_geometry.module import InteractiveGeometryModule

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.export_service = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    return InteractiveGeometryModule(manifest=_STUB_MANIFEST, context=ctx)


def test_build_view_returns_qwidget(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    assert isinstance(widget, QWidget)
    qtbot.addWidget(widget)


def test_module_id_and_name():
    mod = _make_module()
    assert mod.module_id == "interactive_geometry"
    assert mod.module_name == "Interactive Geometry Explorer"
    assert mod.module_version == "1.0.0"


def test_on_load_on_activate_on_deactivate_on_unload(qtbot):
    mod = _make_module()
    mod.on_load()
    mod.on_activate()
    mod.on_deactivate()
    mod.on_unload()  # should not raise
