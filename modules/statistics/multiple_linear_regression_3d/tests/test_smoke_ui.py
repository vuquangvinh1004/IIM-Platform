"""Smoke tests for MultipleLinearRegression3DModule Qt construction."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QPushButton, QTableWidget, QWidget

    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _QT_AVAILABLE, reason="PySide6 not installed")

_STUB_MANIFEST = {
    "id": "multiple_linear_regression_3d",
    "name": "Hồi quy Tuyến tính Bội (2 biến X) - 3D",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": (
        "modules.statistics.multiple_linear_regression_3d.entry:"
        "MultipleLinearRegression3DModule"
    ),
    "category": "statistics",
    "author": "IIMP Team",
    "permissions": ["storage.read", "storage.write", "export.file"],
}


def _make_module():
    from modules.statistics.multiple_linear_regression_3d.module import (
        MultipleLinearRegression3DModule,
    )

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.export_service = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()

    return MultipleLinearRegression3DModule(manifest=_STUB_MANIFEST, context=ctx)


def test_build_view_returns_widget(qtbot):
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    qtbot.addWidget(view)
    assert isinstance(view, QWidget)


def test_has_expected_toolbar_actions(qtbot):
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    qtbot.addWidget(view)

    labels = [btn.text().lower() for btn in view.findChildren(QPushButton)]
    assert any("nhập dữ liệu" in label for label in labels)
    assert any("giải ols" in label for label in labels)


def test_has_computation_table(qtbot):
    mod = _make_module()
    mod.on_load()
    view = mod.build_view()
    qtbot.addWidget(view)

    tables = view.findChildren(QTableWidget)
    assert len(tables) >= 1
    assert tables[0].columnCount() == 8
