"""Application entry point for IIMP.

Run with:
    python main.py

This file must stay minimal — it only wires together the bootstrapped
services and launches the Qt event loop.
"""
import sys

if sys.platform == "win32":
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("IIMP.App.1")

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from config.paths import EXPORTS_DIR, ROOT_DIR
from config.settings import APP_NAME, DEFAULT_THEME
from core.app_kernel.bootstrap import bootstrap
from core.app_kernel.shutdown_manager import ShutdownManager
from core.module_runtime.event_bus import EventBus
from core.module_runtime.registry import ModuleRegistry
from core.services.activity_service import ActivityService
from core.services.app_services import AppServices
from core.services.export_service import ExportService
from core.services.folder_service import FolderService
from core.services.module_service import ModuleService
from core.services.path_service import PathService
from core.services.permission_service import PermissionService
from core.services.settings_service import SettingsService
from core.services.ui_services import DialogService, ThemeService
from core.services.workspace_service import WorkspaceService
from core.utils.constants import ActivityType
from ui.main_window import MainWindow
from ui.styles.themes import apply_theme
from ui.widgets.splash_screen import StartupSplash


def main() -> int:
    # ── 1. Bootstrap infrastructure ──────────────────────────────────────────
    bootstrap()

    # ── 2. Qt application ────────────────────────────────────────────────────
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    _ico = ROOT_DIR / "simulation.ico"
    if _ico.exists():
        app.setWindowIcon(QIcon(str(_ico)))
    apply_theme(app, DEFAULT_THEME)

    # ── 2a. Splash screen ────────────────────────────────────────────────────
    splash = StartupSplash()
    splash.show()
    splash.set_status("Starting up…")
    app.processEvents()

    # ── 3. Shutdown manager ──────────────────────────────────────────────────
    shutdown = ShutdownManager()
    shutdown.connect_to_app(app)

    # ── 4. Services ──────────────────────────────────────────────────────────
    event_bus = EventBus()
    settings_svc = SettingsService()
    activity_svc = ActivityService()
    path_svc = PathService()
    export_svc = ExportService(default_export_dir=EXPORTS_DIR)
    dialog_svc = DialogService()
    theme_svc = ThemeService()
    workspace_svc = WorkspaceService()
    folder_svc = FolderService()

    services = AppServices(
        event_bus=event_bus,
        settings=settings_svc,
        activity=activity_svc,
        paths=path_svc,
        export=export_svc,
        dialogs=dialog_svc,
        theme=theme_svc,
    )

    # ── 5. Module runtime ────────────────────────────────────────────────────
    registry = ModuleRegistry()
    module_svc = ModuleService(
        registry=registry,
        services=services,
    )

    found, failed = module_svc.discover(on_progress=splash.set_progress)
    splash.set_status("Finalizing…")
    app.processEvents()
    activity_svc.log(
        ActivityType.APP_START,
        f"IIMP started. Modules discovered: {found}, failed: {failed}",
    )

    # ── 6. Main window ───────────────────────────────────────────────────────
    window = MainWindow(
        registry=registry,
        module_service=module_svc,
        settings_service=settings_svc,
        folder_service=folder_svc,
    )
    splash.finish_splash(window)
    window.show()

    # ── 7. Register shutdown handlers ────────────────────────────────────────
    shutdown.register("activity_log", lambda: activity_svc.log(ActivityType.APP_SHUTDOWN, "IIMP shutdown."))
    shutdown.register("event_bus_clear", event_bus.clear)

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
