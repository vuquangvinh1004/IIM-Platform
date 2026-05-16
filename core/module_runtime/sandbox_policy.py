"""Sandbox policy placeholder for IIMP v1.0.

In v1.0 sandbox enforcement is declarative (manifest permissions)
rather than OS-level. This module documents the policy and provides
a compatibility check utility.
"""
from __future__ import annotations

from core.module_runtime.manifest_schema import ModuleManifest
from core.utils.constants import PermissionType
from core.utils.helpers import version_satisfies
from core.utils.logger import get_logger

_log = get_logger("iimp.sandbox")

# Permissions officially supported by the platform in v1.0
SUPPORTED_PERMISSIONS: set[str] = {p.value for p in PermissionType}


def check_compatibility(
    manifest: ModuleManifest,
    platform_version: str,
) -> list[str]:
    """Return a list of compatibility warnings for *manifest*.

    An empty list means the module is compatible and all declared
    permissions are supported.
    """
    issues: list[str] = []

    if not version_satisfies(platform_version, manifest.min_platform_version):
        issues.append(
            f"Module requires platform >= {manifest.min_platform_version}, "
            f"current is {platform_version}"
        )

    unsupported = [p for p in manifest.permissions if p not in SUPPORTED_PERMISSIONS]
    for perm in unsupported:
        issues.append(f"Unsupported permission declared: '{perm}'")

    return issues
