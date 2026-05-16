"""UI smoke tests for the IIMP shell.

These tests verify that the main shell views can be constructed and rendered
without crashing.  They do NOT assert visual/content correctness — only that
no exception is raised during widget construction.

All tests are automatically skipped when PySide6 is not installed.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

try:
    from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

pytestmark = pytest.mark.skipif(not _QT_AVAILABLE, reason="PySide6 not installed")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_registry():
    from core.module_runtime.registry import ModuleRegistry
    reg = ModuleRegistry()
    return reg


def _make_module_service(registry):
    from unittest.mock import MagicMock
    svc = MagicMock()
    svc.registry = registry
    return svc


def _make_settings_service():
    svc = MagicMock()
    svc.get.return_value = None
    svc.get_setting.return_value = None
    return svc


def _make_folder_service():
    return MagicMock()


# ---------------------------------------------------------------------------
# Individual view smoke tests
# ---------------------------------------------------------------------------


class TestDashboardView:
    def test_constructs_without_crash(self, qtbot, patched_db):
        from ui.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        assert isinstance(view, QWidget)

    def test_is_visible_after_show(self, qtbot, patched_db):
        from ui.views.dashboard_view import DashboardView
        view = DashboardView()
        qtbot.addWidget(view)
        view.show()
        assert view.isVisible()


class TestModuleLibraryView:
    def test_constructs_without_crash(self, qtbot):
        from ui.views.module_library_view import ModuleLibraryView
        view = ModuleLibraryView()
        qtbot.addWidget(view)
        assert isinstance(view, QWidget)

    def test_populate_with_empty_list(self, qtbot):
        from ui.views.module_library_view import ModuleLibraryView
        view = ModuleLibraryView()
        qtbot.addWidget(view)
        view.populate([])  # should not raise

    def test_search_box_exists(self, qtbot):
        from PySide6.QtWidgets import QLineEdit
        from ui.views.module_library_view import ModuleLibraryView
        view = ModuleLibraryView()
        qtbot.addWidget(view)
        search_boxes = view.findChildren(QLineEdit)
        assert len(search_boxes) >= 1


class TestModuleManagerView:
    def test_constructs_without_crash(self, qtbot):
        from ui.views.module_manager_view import ModuleManagerView
        view = ModuleManagerView()
        qtbot.addWidget(view)
        assert isinstance(view, QWidget)

    def test_set_services_with_empty_registry(self, qtbot, patched_db):
        from ui.views.module_manager_view import ModuleManagerView
        view = ModuleManagerView()
        qtbot.addWidget(view)
        reg = _make_registry()
        svc = _make_module_service(reg)
        view.set_services(reg, svc)  # should not raise


class TestSettingsView:
    def test_constructs_without_crash(self, qtbot):
        from ui.views.settings_view import SettingsView
        view = SettingsView()
        qtbot.addWidget(view)
        assert isinstance(view, QWidget)

    def test_set_settings_service(self, qtbot, patched_db):
        from ui.views.settings_view import SettingsView
        from core.services.settings_service import SettingsService
        view = SettingsView()
        qtbot.addWidget(view)
        svc = SettingsService()
        view.set_settings_service(svc)  # should not raise


class TestActivityHistoryView:
    def test_constructs_without_crash(self, qtbot, patched_db):
        from ui.views.activity_history_view import ActivityHistoryView
        view = ActivityHistoryView()
        qtbot.addWidget(view)
        assert isinstance(view, QWidget)


# ---------------------------------------------------------------------------
# MainWindow smoke tests
# ---------------------------------------------------------------------------


class TestMainWindow:
    def test_constructs_without_crash(self, qtbot, patched_db):
        from ui.main_window import MainWindow
        reg = _make_registry()
        svc = _make_module_service(reg)
        win = MainWindow(registry=reg, module_service=svc,
                         settings_service=_make_settings_service(),
                         folder_service=_make_folder_service())
        qtbot.addWidget(win)
        assert isinstance(win, QMainWindow)

    def test_has_stacked_widget(self, qtbot, patched_db):
        from ui.main_window import MainWindow
        reg = _make_registry()
        svc = _make_module_service(reg)
        win = MainWindow(registry=reg, module_service=svc,
                         settings_service=_make_settings_service(),
                         folder_service=_make_folder_service())
        qtbot.addWidget(win)
        stacks = win.findChildren(QStackedWidget)
        assert len(stacks) >= 1

    def test_navigate_to_each_view(self, qtbot, patched_db):
        """Clicking each nav button must not raise."""
        from PySide6.QtWidgets import QPushButton
        from ui.main_window import MainWindow
        reg = _make_registry()
        svc = _make_module_service(reg)
        win = MainWindow(registry=reg, module_service=svc,
                         settings_service=_make_settings_service(),
                         folder_service=_make_folder_service())
        qtbot.addWidget(win)
        win.show()
        # Find all sidebar navigation push-buttons and click each
        for btn in win.findChildren(QPushButton):
            if btn.parent() and btn.parent().objectName() == "sidebar":
                qtbot.mouseClick(btn, pytest.importorskip("PySide6.QtCore").Qt.MouseButton.LeftButton)

    def test_window_title_set(self, qtbot, patched_db):
        from ui.main_window import MainWindow
        from config.settings import APP_SHORT_NAME
        reg = _make_registry()
        svc = _make_module_service(reg)
        win = MainWindow(registry=reg, module_service=svc,
                         settings_service=_make_settings_service(),
                         folder_service=_make_folder_service())
        qtbot.addWidget(win)
        assert win.windowTitle() == APP_SHORT_NAME
