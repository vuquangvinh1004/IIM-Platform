"""AppServices — container for all platform-level services.

Grouping services into a single dataclass eliminates pass-through variables:
instead of propagating individual services through long constructor chains,
components that need multiple services accept one ``AppServices`` instance.

Usage::

    services = AppServices(
        event_bus=event_bus,
        settings=settings_svc,
        activity=activity_svc,
        paths=path_svc,
        export=export_svc,
        dialogs=dialog_svc,
        theme=theme_svc,
    )
    module_service = ModuleService(registry, services)
"""
from __future__ import annotations

from dataclasses import dataclass

from core.module_runtime.event_bus import EventBus
from core.services.activity_service import ActivityService
from core.services.export_service import ExportService
from core.services.path_service import PathService
from core.services.settings_service import SettingsService
from core.services.ui_services import DialogService, ThemeService


@dataclass(frozen=True)
class AppServices:
    """Immutable container for all platform-level services.

    Attributes:
        event_bus: Platform-wide pub-sub event bus.
        settings:  Unified app and module settings store.
        activity:  Structured activity-log writer.
        paths:     Module-scoped path resolver.
        export:    Safe file-export capability.
        dialogs:   Unified message dialog presenter.
        theme:     UI palette token provider.
    """

    event_bus: EventBus
    settings: SettingsService
    activity: ActivityService
    paths: PathService
    export: ExportService
    dialogs: DialogService
    theme: ThemeService
