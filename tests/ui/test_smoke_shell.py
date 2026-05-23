"""UI smoke tests for the IIMP shell.

These tests verify that the main shell views can be constructed and rendered
without crashing.  They do NOT assert visual/content correctness — only that
no exception is raised during widget construction.

All tests are automatically skipped when PySide6 is not installed.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
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


def _register_module_record(registry, module_id: str, name: str, category: str = "test"):
    """Register a minimal valid manifest record for library rendering tests."""
    from core.module_runtime.manifest_schema import ModuleManifest

    manifest = ModuleManifest.model_validate(
        {
            "id": module_id,
            "name": name,
            "version": "1.0.0",
            "sdk_version": "1.0.0",
            "min_platform_version": "1.0.0",
            "entry_point": "modules.templates.starter_module.entry:StarterModule",
            "description": f"Synthetic module for UI stress: {module_id}",
            "category": category,
            "author": "UI Test",
            "permissions": ["storage.read"],
            "tags": ["ui-test"],
            "supports_state_restore": True,
            "supports_export": False,
        }
    )
    registry.register(manifest, Path("."))


class _FakeModuleInstance:
    """Module double that caches and reuses one root widget across opens."""

    def __init__(self, module_name: str):
        from PySide6.QtWidgets import QLabel

        self.module_name = module_name
        self._widget = QLabel(f"Fake module view: {module_name}")
        self._widget.setObjectName(f"fake_view_{module_name.lower().replace(' ', '_')}")

    def build_view(self):
        return self._widget


class _FakeModuleServiceForOpenLoop:
    """Service double for repeated open-module UI workflow tests."""

    def __init__(self, modules: dict[str, _FakeModuleInstance]):
        self._modules = modules

    def load_module(self, module_id: str):
        return self._modules.get(module_id)

    def activate(self, module_id: str) -> bool:
        return module_id in self._modules


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

    def test_repeated_open_from_library_keeps_workspace_non_blank(self, qtbot, patched_db):
        """Regression: repeated opens must never leave Workspace in an empty/blank state."""
        from ui.main_window import MainWindow
        from ui.views.module_library_view import ModuleLibraryView
        from ui.views.workspace_view import WorkspaceView

        reg = _make_registry()
        _register_module_record(reg, "mod_alpha", "Alpha")
        _register_module_record(reg, "mod_beta", "Beta")
        _register_module_record(reg, "mod_gamma", "Gamma")

        fake_instances = {
            "mod_alpha": _FakeModuleInstance("Alpha"),
            "mod_beta": _FakeModuleInstance("Beta"),
            "mod_gamma": _FakeModuleInstance("Gamma"),
        }
        svc = _FakeModuleServiceForOpenLoop(fake_instances)

        win = MainWindow(
            registry=reg,
            module_service=svc,
            settings_service=_make_settings_service(),
            folder_service=_make_folder_service(),
        )
        qtbot.addWidget(win)
        win.show()

        library = win.findChild(ModuleLibraryView)
        workspace = win.findChild(WorkspaceView)
        assert library is not None
        assert workspace is not None

        open_sequence = [
            "mod_alpha", "mod_beta", "mod_gamma",
            "mod_beta", "mod_alpha", "mod_gamma",
            "mod_gamma", "mod_beta", "mod_alpha",
            "mod_alpha", "mod_beta", "mod_gamma",
            "mod_beta", "mod_alpha", "mod_gamma",
        ]

        for module_id in open_sequence:
            library.open_module.emit(module_id)
            qtbot.waitUntil(
                lambda: workspace.host_frame.active_module_id == module_id,
                timeout=1000,
            )

            hosted = workspace.host_frame._current_widget
            assert hosted is not None
            assert hosted.property("hostOwned") is not True
            assert hosted.parent() is workspace.host_frame
            assert hosted.isVisible()
