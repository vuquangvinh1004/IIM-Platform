"""Smoke tests for CentralLimitTheoremModule Qt view construction."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import (
        QPushButton, QStackedWidget, QTableWidget, QWidget,
    )
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not _QT_AVAILABLE, reason="PySide6 not installed"
)

_STUB_MANIFEST = {
    "id": "central_limit_theorem",
    "name": "Định lý Giới hạn Trung tâm",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": (
        "modules.statistics.central_limit_theorem.entry"
        ":CentralLimitTheoremModule"
    ),
    "category": "statistics",
    "author": "IIMP Team",
    "permissions": [
        "storage.read", "storage.write",
        "settings.read", "settings.write",
        "dialogs.basic", "activity.write",
    ],
}


def _make_module():
    from modules.statistics.central_limit_theorem.module import (
        CentralLimitTheoremModule,
    )

    ctx = MagicMock()
    ctx.logger = MagicMock()
    ctx.settings_service = MagicMock()
    ctx.settings_service.get_module_setting.return_value = None
    ctx.activity_service = MagicMock()
    ctx.export_service = MagicMock()
    mod = CentralLimitTheoremModule(manifest=_STUB_MANIFEST, context=ctx)
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

    def test_initial_page_is_weighing(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        stack = view.findChildren(QStackedWidget)[0]
        assert stack.currentIndex() == 0

    def test_config_button_exists(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        buttons = {b.text() for b in view.findChildren(QPushButton)}
        assert any("Cấu hình" in t for t in buttons)

    def test_manual_button_exists(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        buttons = {b.text() for b in view.findChildren(QPushButton)}
        assert any("thủ công" in t.lower() for t in buttons)

    def test_auto_button_exists(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        buttons = {b.text() for b in view.findChildren(QPushButton)}
        assert any("tự động" in t.lower() for t in buttons)

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

    def test_finish_button_initially_disabled(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        fin_btns = [b for b in view.findChildren(QPushButton)
                    if "Hoàn thành" in b.text()]
        assert fin_btns, "Finish button not found"
        assert not fin_btns[0].isEnabled()

    def test_results_table_has_four_columns(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        tables = view.findChildren(QTableWidget)
        assert tables, "No QTableWidget found"
        col_counts = {t.columnCount() for t in tables}
        assert 4 in col_counts

    def test_back_button_exists_in_sim_view(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        buttons = {b.text() for b in view.findChildren(QPushButton)}
        assert any("Quay lại" in t for t in buttons)


# ---------------------------------------------------------------------------
# Module metadata
# ---------------------------------------------------------------------------


class TestModuleMetadata:
    def test_module_id(self):
        mod = _make_module()
        assert mod.module_id == "central_limit_theorem"

    def test_module_name(self):
        mod = _make_module()
        assert mod.module_name == "Định lý Giới hạn Trung tâm"

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
# Auto-complete flow
# ---------------------------------------------------------------------------


class TestAutoCompleteFlow:
    def test_auto_fills_all_samples(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        page = mod._weigh_page
        page._cfg_sample_size = 5
        page._cfg_num_samples = 3
        page._cfg_pop_mean = 500.0
        page._cfg_pop_std = 20.0
        page._cfg_norm_mean = 500.0
        page._cfg_norm_std = 20.0

        mod._on_auto()
        assert mod._engine.is_complete
        assert mod._engine.samples_done == 3

    def test_simulate_enabled_after_auto(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        page = mod._weigh_page
        page._cfg_sample_size = 5
        page._cfg_num_samples = 2
        page._cfg_pop_mean = 500.0
        page._cfg_pop_std = 20.0
        page._cfg_norm_mean = 500.0
        page._cfg_norm_std = 20.0

        mod._on_auto()
        sim_btns = [b for b in view.findChildren(QPushButton)
                    if "Mô phỏng" in b.text()]
        assert sim_btns and sim_btns[0].isEnabled()

    def test_reset_resets_state(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        page = mod._weigh_page
        page._cfg_sample_size = 5
        page._cfg_num_samples = 2
        page._cfg_pop_mean = 500.0
        page._cfg_pop_std = 20.0
        page._cfg_norm_mean = 500.0
        page._cfg_norm_std = 20.0

        mod._on_auto()
        mod._on_reset()
        assert mod._engine.samples_done == 0
        assert not mod._engine.is_complete

    def test_show_simulation_switches_page(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        page = mod._weigh_page
        page._cfg_sample_size = 5
        page._cfg_num_samples = 2
        page._cfg_pop_mean = 500.0
        page._cfg_pop_std = 20.0
        page._cfg_norm_mean = 500.0
        page._cfg_norm_std = 20.0

        mod._on_auto()
        mod._on_show_simulation()
        assert mod._stack.currentIndex() == 1

    def test_back_switches_to_weighing(self, qtbot):
        mod = _make_module()
        view = mod.build_view()
        qtbot.addWidget(view)

        page = mod._weigh_page
        page._cfg_sample_size = 5
        page._cfg_num_samples = 2
        page._cfg_pop_mean = 500.0
        page._cfg_pop_std = 20.0
        page._cfg_norm_mean = 500.0
        page._cfg_norm_std = 20.0

        mod._on_auto()
        mod._on_show_simulation()
        mod._on_back()
        assert mod._stack.currentIndex() == 0
