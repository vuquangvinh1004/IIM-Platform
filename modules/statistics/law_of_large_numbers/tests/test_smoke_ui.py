"""Smoke tests for LawOfLargeNumbersModule Qt view construction.

Requires a running QApplication (provided by pytest-qt's ``qtbot`` fixture).
These tests verify the view builds without crashing and core UI elements exist.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QGroupBox, QPushButton, QRadioButton, QSpinBox, QTableWidget, QWidget
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _QT_AVAILABLE, reason="PySide6 not installed")

_STUB_MANIFEST = {
    "id": "law_of_large_numbers",
    "name": "Luật Số Lớn — Tung Đồng Xu",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.statistics.law_of_large_numbers.entry:LawOfLargeNumbersModule",
    "category": "statistics",
    "author": "IIMP Team",
    "permissions": ["storage.read", "storage.write", "export.file",
                    "settings.read", "settings.write"],
}


def _make_module():
    from modules.statistics.law_of_large_numbers.module import LawOfLargeNumbersModule

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.export_service = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    return LawOfLargeNumbersModule(manifest=_STUB_MANIFEST, context=ctx)


def test_build_view_returns_qwidget(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    assert isinstance(widget, QWidget)
    qtbot.addWidget(widget)


def test_module_id_and_name():
    mod = _make_module()
    assert mod.module_id == "law_of_large_numbers"
    assert mod.module_name == "Luật Số Lớn — Tung Đồng Xu"
    assert mod.module_version == "1.0.0"


def test_on_load_on_activate_on_deactivate_on_unload(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    mod.on_activate()
    mod.on_deactivate()
    mod.on_unload()


def test_toss_button_exists(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    buttons = widget.findChildren(QPushButton)
    labels = [b.text() for b in buttons]
    assert any("tung" in lbl.lower() or "🪙" in lbl for lbl in labels)


def test_spin_box_exists(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    spins = widget.findChildren(QSpinBox)
    assert len(spins) >= 1


def test_table_has_correct_columns(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    tables = widget.findChildren(QTableWidget)
    assert len(tables) >= 1
    assert tables[0].columnCount() == 6


def test_toss_updates_table(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    table = widget.findChildren(QTableWidget)[0]
    assert table.rowCount() == 0

    mod._on_toss()
    mod._flush_animation()
    assert table.rowCount() == 1

    mod._on_toss()
    mod._flush_animation()
    assert table.rowCount() == 2


def test_reset_clears_table(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    mod._on_toss()
    mod._flush_animation()
    mod._on_toss()
    mod._flush_animation()
    mod._on_reset()

    table = widget.findChildren(QTableWidget)[0]
    assert table.rowCount() == 0


def test_state_round_trip(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    for _ in range(5):
        mod._on_toss()
        mod._flush_animation()

    state = mod.get_state()
    assert state["cum_tosses"] == 5

    mod2 = _make_module()
    mod2.on_load()
    w2 = mod2.build_view()
    qtbot.addWidget(w2)
    mod2.restore_state(state)
    assert mod2.get_state()["cum_tosses"] == 5


def test_face_selector_has_two_radio_buttons(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    radio_buttons = widget.findChildren(QRadioButton)
    assert len(radio_buttons) == 2
    labels = {rb.text() for rb in radio_buttons}
    assert any("N" in lbl for lbl in labels)
    assert any("S" in lbl for lbl in labels)


def test_face_change_resets_engine(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    # Toss some coins
    mod._spin_tosses.setValue(5)
    mod._on_toss()
    mod._flush_animation()
    assert mod._engine.cum_tosses == 5

    # Switch to "Sấp" — engine should reset
    mod._rb_tails.setChecked(True)
    assert mod._engine.cum_tosses == 0
    assert mod._engine.observed_face == 'tails'
