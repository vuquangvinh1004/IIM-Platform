"""ModuleContext — the host services container passed to every module.

Modules interact with the shell exclusively through this object.
No module may import shell internals directly.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PlatformInfo:
    """Read-only platform metadata exposed to modules."""

    platform_version: str
    sdk_version: str
    os_name: str
    debug: bool = False


@dataclass
class ModuleContext:
    """All host services available to a loaded module.

    The host populates this before passing it to ``instantiate_module()``.
    Only services listed here are officially supported in SDK v1.0.
    """

    module_id: str
    logger: Any                    # loguru bound logger
    event_bus: Any                 # EventBus instance
    storage_service: Any           # StorageService
    settings_service: Any          # SettingsService
    export_service: Any            # ExportService
    activity_service: Any          # ActivityService
    dialog_service: Any            # DialogService
    theme_service: Any             # ThemeService
    path_service: Any              # PathService
    platform_info: PlatformInfo
    workspace_service: Any = field(default=None)
