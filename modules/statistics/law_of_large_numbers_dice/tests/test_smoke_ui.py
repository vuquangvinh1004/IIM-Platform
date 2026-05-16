"""Smoke tests for LLNDiceModule Qt view construction."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QCheckBox, QPushButton, QSpinBox, QTableWidget, QWidget
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _QT_AVAILABLE, reason="PySide6 not installed")

_STUB_MANIFEST = {
    "id": "law_of_large_numbers_dice",
    "name": "Luật Số Lớn — Tung Xúc Xắc",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.statistics.law_of_large_numbers_dice.entry:LLNDiceModule",
    "category": "statistics",
    "author": "IIMP Team",
    "permissions": ["storage.read", "storage.write", "export.file",
                    "settings.read", "settings.write"],
}


def _make_module():
    from modules.statistics.law_of_large_numbers_dice.module import LLNDiceModule

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.export_service = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    return LLNDiceModule(manifest=_STUB_MANIFEST, context=ctx)


def test_build_view_returns_qwidget(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    assert isinstance(widget, QWidget)
    qtbot.addWidget(widget)


def test_module_id_and_name():
    mod = _make_module()
    assert mod.module_id == "law_of_large_numbers_dice"
    assert mod.module_name == "Luật Số Lớn — Tung Xúc Xắc"
    assert mod.module_version == "1.0.0"


def test_on_load_activate_deactivate_unload(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    mod.on_activate()
    mod.on_deactivate()
    mod.on_unload()


def test_roll_button_exists(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    buttons = [b.text() for b in widget.findChildren(QPushButton)]
    assert any("tung" in t.lower() or "🎲" in t for t in buttons)


def test_spin_box_exists(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    assert len(widget.findChildren(QSpinBox)) >= 1


def test_six_face_checkboxes_exist(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    cbs = widget.findChildren(QCheckBox)
    assert len(cbs) == 6


def test_table_has_correct_columns(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)
    tables = widget.findChildren(QTableWidget)
    assert len(tables) >= 1
    assert tables[0].columnCount() == 6


def test_roll_updates_table(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    table = widget.findChildren(QTableWidget)[0]
    assert table.rowCount() == 0

    mod._on_roll()
    mod._flush_animation()
    assert table.rowCount() == 1

    mod._on_roll()
    mod._flush_animation()
    assert table.rowCount() == 2


def test_reset_clears_table(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    mod._on_roll()
    mod._flush_animation()
    mod._on_roll()
    mod._flush_animation()
    mod._on_reset()

    assert widget.findChildren(QTableWidget)[0].rowCount() == 0


def test_changing_faces_resets_data(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    mod._on_roll()
    mod._flush_animation()
    assert mod._engine.cum_rolls == 1

    # Change observed faces triggers reset via _on_faces_changed
    mod._engine.set_observed_faces([1, 2, 3])
    mod._refresh_all()
    assert mod._engine.cum_rolls == 0


def test_theoretical_prob_updates_with_faces():
    mod = _make_module()
    mod._engine.set_observed_faces([1, 2, 3])
    assert abs(mod._engine.theoretical_prob - 0.5) < 1e-12


def test_state_round_trip(qtbot):
    mod = _make_module()
    mod.on_load()
    widget = mod.build_view()
    qtbot.addWidget(widget)

    for _ in range(5):
        mod._on_roll()
        mod._flush_animation()

    state = mod.get_state()
    assert state["cum_rolls"] == 5

    mod2 = _make_module()
    mod2.on_load()
    w2 = mod2.build_view()
    qtbot.addWidget(w2)
    mod2.restore_state(state)
    assert mod2.get_state()["cum_rolls"] == 5
    assert mod2.get_state()["observed_faces"] == state["observed_faces"]
