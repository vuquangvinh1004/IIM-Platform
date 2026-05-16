"""Permission service — checks declared permissions against supported set.

v1.0: declarative only (no OS-level sandbox).
"""
from __future__ import annotations

from core.module_runtime.manifest_schema import ModuleManifest
from core.utils.constants import PermissionType
from core.utils.logger import get_logger

_log = get_logger("iimp.services.permission")

SUPPORTED: set[str] = {p.value for p in PermissionType}


class PermissionService:
    """Checks module permission declarations."""

    def has_permission(self, manifest: ModuleManifest, permission: str) -> bool:
        return permission in manifest.permissions

    def unsupported_permissions(self, manifest: ModuleManifest) -> list[str]:
        return [p for p in manifest.permissions if p not in SUPPORTED]
