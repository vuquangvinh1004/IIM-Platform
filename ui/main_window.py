"""Main application window for IIMP.

Layout:
    ┌──────────────────────────────────────────────────────────┐
    │  Sidebar (nav)  │  Content stack (views)                 │
    ├──────────────────┴────────────────────────────────────────┤
    │  Status strip                                            │
    └──────────────────────────────────────────────────────────┘

Navigation is handled by a vertical button group on the left sidebar.
Each button switches the central QStackedWidget to the corresponding view.
"""
from __future__ import annotations

from enum import IntEnum
from typing import cast

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from config.settings import (
    APP_SHORT_NAME,
    WINDOW_DEFAULT_HEIGHT,
    WINDOW_DEFAULT_WIDTH,
    WINDOW_MIN_HEIGHT,
    WINDOW_MIN_WIDTH,
)
from core.module_runtime.registry import ModuleRegistry
from core.services.folder_service import FolderService
from core.services.module_service import ModuleService
from core.services.settings_service import SettingsService
from core.utils.logger import get_logger
from ui.views.activity_history_view import ActivityHistoryView
from ui.views.dashboard_view import DashboardView
from ui.views.module_library_view import ModuleLibraryView
from ui.views.module_manager_view import ModuleManagerView
from ui.views.settings_view import SettingsView
from ui.views.workspace_view import WorkspaceView
from ui.widgets.status_strip import StatusStrip

_log = get_logger("iimp.main_window")


class _NavIndex(IntEnum):
    """Typed indices for the navigation stack — eliminates magic string lookups."""
    DASHBOARD = 0
    LIBRARY = 1
    WORKSPACE = 2
    MANAGER = 3
    ACTIVITY = 4
    SETTINGS = 5


# Navigation entry: (button label, view class) — order must match _NavIndex
_NAV_ENTRIES: list[tuple[str, type[QWidget]]] = [
    ("Dashboard", DashboardView),
    ("Library", ModuleLibraryView),
    ("Workspace", WorkspaceView),
    ("Manager", ModuleManagerView),
    ("Activity", ActivityHistoryView),
    ("Settings", SettingsView),
]


class MainWindow(QMainWindow):
    """Primary shell window — hosts navigation and module host frame."""

    def __init__(
        self,
        registry: ModuleRegistry,
        module_service: ModuleService,
        settings_service: SettingsService,
        folder_service: FolderService,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._registry = registry
        self._module_service = module_service
        self._settings_service = settings_service
        self._folder_service = folder_service
        self._nav_buttons: list[QPushButton] = []
        self._library_signal_connected = False

        self._setup_window()
        self._build_ui()
        self._post_init()

    # ── Setup ─────────────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        self.setWindowTitle(APP_SHORT_NAME)
        self.setMinimumSize(WINDOW_MIN_WIDTH, WINDOW_MIN_HEIGHT)
        self.resize(WINDOW_DEFAULT_WIDTH, WINDOW_DEFAULT_HEIGHT)

    def _build_ui(self) -> None:
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Sidebar
        self._sidebar = self._build_sidebar()
        root_layout.addWidget(self._sidebar)

        # Content stack
        self._stack = QStackedWidget()
        root_layout.addWidget(self._stack, stretch=1)

        # Add views to stack (order must match _NavIndex)
        for _label, view_cls in _NAV_ENTRIES:
            self._stack.addWidget(view_cls())

        # Status strip
        self._status_strip = StatusStrip()
        self.setStatusBar(self._status_strip)

    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(180)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(0, 16, 0, 16)
        layout.setSpacing(2)

        for index, (label, _) in enumerate(_NAV_ENTRIES):
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setObjectName(f"nav_{label.lower()}")
            btn.clicked.connect(lambda checked, idx=index: self._navigate(idx))
            layout.addWidget(btn)
            self._nav_buttons.append(btn)

        layout.addStretch()
        return sidebar

    def _post_init(self) -> None:
        """Run after UI is built — inject services, populate library, navigate to dashboard."""
        manager_view = cast(ModuleManagerView, self._stack.widget(_NavIndex.MANAGER))
        manager_view.set_services(self._registry, self._module_service)

        settings_view = cast(SettingsView, self._stack.widget(_NavIndex.SETTINGS))
        settings_view.set_settings_service(self._settings_service)

        library = cast(ModuleLibraryView, self._stack.widget(_NavIndex.LIBRARY))
        library.set_folder_service(self._folder_service)
        if not self._library_signal_connected:
            library.open_module.connect(self._open_module)
            self._library_signal_connected = True

        workspace = cast(WorkspaceView, self._stack.widget(_NavIndex.WORKSPACE))
        workspace.host_frame.browse_requested.connect(lambda: self._navigate(_NavIndex.LIBRARY))

        self._navigate(_NavIndex.DASHBOARD)
        self._refresh_library()

    # ── Navigation ────────────────────────────────────────────────────────────

    def _navigate(self, index: _NavIndex | int) -> None:
        self._stack.setCurrentIndex(int(index))
        for i, btn in enumerate(self._nav_buttons):
            btn.setChecked(i == int(index))
        # Refresh data-driven views on navigation
        view = self._stack.widget(int(index))
        if view is not None and hasattr(view, "refresh"):
            view.refresh()  # type: ignore[union-attr]

    # ── Module open ───────────────────────────────────────────────────────────

    def _open_module(self, module_id: str) -> None:
        """Load module, build view and display in workspace."""
        workspace = cast(WorkspaceView, self._stack.widget(_NavIndex.WORKSPACE))

        instance = self._module_service.load_module(module_id)
        if instance is None:
            record = self._registry.get_record(module_id)
            error = record.error if record else "Unknown error"
            workspace.host_frame.show_error(module_id, error or "Load failed")
            self._navigate(_NavIndex.WORKSPACE)
            _log.error(f"Module '{module_id}' failed to load.")
            return

        try:
            widget = instance.build_view()
            workspace.host_frame.show_module(module_id, widget)
        except Exception as exc:
            workspace.host_frame.show_error(module_id, f"Build view failed: {exc}")
            self._navigate(_NavIndex.WORKSPACE)
            _log.exception(f"Module '{module_id}' failed while building/hosting view: {exc}")
            return

        if not self._module_service.activate(module_id):
            record = self._registry.get_record(module_id)
            error = record.error if record else "Activation failed"
            workspace.host_frame.show_error(module_id, error or "Activation failed")
            self._navigate(_NavIndex.WORKSPACE)
            _log.error(f"Module '{module_id}' failed to activate.")
            return

        self._navigate(_NavIndex.WORKSPACE)
        self._status_strip.set_status(f"Active: {instance.module_name}")
        _log.info(f"Module '{module_id}' displayed in workspace.")

    # ── Library helpers ───────────────────────────────────────────────────────

    def _refresh_library(self) -> None:
        records = self._registry.all_records()
        library = cast(ModuleLibraryView, self._stack.widget(_NavIndex.LIBRARY))
        library.populate(records)
        self._status_strip.set_module_count(len(records))
