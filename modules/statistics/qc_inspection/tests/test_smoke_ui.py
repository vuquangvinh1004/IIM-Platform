"""Smoke tests for QCInspectionModule Qt view construction."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import (
        QGroupBox, QPushButton, QSpinBox, QStackedWidget,
        QTableWidget, QWidget,
    )
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _QT_AVAILABLE, reason="PySide6 not installed"
)

_STUB_MANIFEST = {
    "id": "qc_inspection",
    "name": "QC Kiểm tra Chất lượng",
    "version": "1.0.0",
    "sdk_version": "1.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.statistics.qc_inspection.entry.QCInspectionModule",
    "category": "statistics",
    "author": "IIMP Team",
    "permissions": [
        "storage.read", "storage.write",
        "settings.read", "settings.write",
        "dialogs.basic", "activity.write",
    ],
}


def _make_module():
    from modules.statistics.qc_inspection.module import QCInspectionModule

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    ctx.export_service = MagicMock()
    mod = QCInspectionModule(manifest=_STUB_MANIFEST, context=ctx)
    mod.on_load()
    return mod


# ---------------------------------------------------------------------------
# View construction
# ---------------------------------------------------------------------------


class TestBuildView:
    def test_build_view_returns_qwidget(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        assert isinstance(view, QWidget)

    def test_view_has_stacked_widget(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        stacks = view.findChildren(QStackedWidget)
        assert len(stacks) >= 1

    def test_initial_page_is_inspection(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        stack = view.findChildren(QStackedWidget)[0]
        assert stack.currentIndex() == 0

    def test_config_button_exists(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        buttons = {b.text() for b in view.findChildren(QPushButton)}
        assert any("Cấu hình" in t for t in buttons)

    def test_qc_buttons_exist(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        buttons = {b.text() for b in view.findChildren(QPushButton)}
        assert any("Thủ công" in t for t in buttons)
        assert any("Tự động" in t for t in buttons)

    def test_simulate_button_initially_disabled(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        sim_btns = [b for b in view.findChildren(QPushButton)
                    if "Mô phỏng" in b.text()]
        assert sim_btns, "Simulate button not found"
        assert not sim_btns[0].isEnabled()

    def test_record_button_initially_disabled(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        rec_btns = [b for b in view.findChildren(QPushButton)
                    if "Ghi nhận" in b.text()]
        assert rec_btns, "Record button not found"
        assert not rec_btns[0].isEnabled()

    def test_results_table_has_four_columns(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        tables = view.findChildren(QTableWidget)
        assert tables, "No QTableWidget found"
        # The records table should have 4 columns
        col_counts = {t.columnCount() for t in tables}
        assert 4 in col_counts


# ---------------------------------------------------------------------------
# Module id / name / version
# ---------------------------------------------------------------------------


class TestModuleMetadata:
    def test_module_id(self):
        mod = _make_module()
        assert mod.module_id == "qc_inspection"

    def test_module_name(self):
        mod = _make_module()
        assert mod.module_name == "QC Kiểm tra Chất lượng"

    def test_module_version(self):
        mod = _make_module()
        assert mod.module_version == "1.0.0"


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


class TestLifecycle:
    def test_on_load_activate_deactivate_unload(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)
        mod.on_activate()
        mod.on_deactivate()
        mod.on_unload()
        # Should not raise; settings_service.set_module_setting called
        mod.context.settings_service.set_module_setting.assert_called()

    def test_get_state_returns_dict(self, qtbot):
        mod = _make_module()
        state = mod.get_state()
        assert isinstance(state, dict)
        assert "engine" in state

    def test_restore_state_tolerates_empty(self, qtbot):
        mod = _make_module()
        mod.restore_state({})  # should not raise


# ---------------------------------------------------------------------------
# Manual QC flow
# ---------------------------------------------------------------------------


class TestManualQCFlow:
    def test_manual_qc_loads_products(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        insp = mod._insp_page
        insp._cfg_n_products = 10
        insp._cfg_n_rounds = 3

        mod._on_manual_qc()
        assert mod._engine.is_pending_record

    def test_record_commits_round(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        insp = mod._insp_page
        insp._cfg_n_products = 5
        insp._cfg_n_rounds = 2

        mod._on_manual_qc()
        mod._on_record()
        assert mod._engine.rounds_done == 1

    def test_simulate_enabled_after_completion(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        insp = mod._insp_page
        insp._cfg_n_products = 5
        insp._cfg_n_rounds = 2

        for _ in range(2):
            mod._on_manual_qc()
            mod._on_record()

        assert mod._engine.is_complete
        sim_btns = [b for b in view.findChildren(QPushButton)
                    if "Mô phỏng" in b.text()]
        assert sim_btns[0].isEnabled()


# ---------------------------------------------------------------------------
# Auto QC flow
# ---------------------------------------------------------------------------


class TestAutoQCFlow:
    def test_auto_qc_completes_all_rounds(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        insp = mod._insp_page
        insp._cfg_n_products = 10
        insp._cfg_n_rounds = 5

        mod._on_auto_qc()
        assert mod._engine.is_complete
        assert mod._engine.rounds_done == 5


# ---------------------------------------------------------------------------
# Simulation view navigation
# ---------------------------------------------------------------------------


class TestSimulationNavigation:
    def test_show_simulation_switches_page(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        insp = mod._insp_page
        insp._cfg_n_products = 8
        insp._cfg_n_rounds = 3
        mod._on_auto_qc()

        mod._on_show_simulation()
        assert mod._stack.currentIndex() == 1

    def test_back_returns_to_inspection(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        insp = mod._insp_page
        insp._cfg_n_products = 8
        insp._cfg_n_rounds = 2
        mod._on_auto_qc()
        mod._on_show_simulation()
        mod._on_back()
        assert mod._stack.currentIndex() == 0

    def test_simulation_not_shown_if_incomplete(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        # No data → simulation switch must NOT happen
        mod._on_show_simulation()
        assert mod._stack.currentIndex() == 0


# ---------------------------------------------------------------------------
# Reset
# ---------------------------------------------------------------------------


class TestReset:
    def test_reset_clears_engine_records(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        insp = mod._insp_page
        insp._cfg_n_products = 5
        insp._cfg_n_rounds = 2
        mod._on_auto_qc()
        mod._on_reset()
        assert mod._engine.rounds_done == 0

    def test_reset_unlocks_spinners(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        insp = mod._insp_page
        insp._cfg_n_products = 5
        insp._cfg_n_rounds = 2
        mod._on_auto_qc()
        mod._on_reset()
        assert mod._insp_page._btn_config.isEnabled()
