"""Input and manifest field validators for IIMP.

These are pure validation functions — no Qt, no DB access.
"""
from __future__ import annotations

import re
from typing import Any

from core.utils.helpers import parse_version


# ── Module ID ─────────────────────────────────────────────────────────────────
_MODULE_ID_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")


def validate_module_id(module_id: Any) -> str:
    """Validate and return a well-formed module id.

    Raises ValueError if invalid.
    """
    if not isinstance(module_id, str) or not module_id:
        raise ValueError("module id must be a non-empty string")
    if not _MODULE_ID_RE.match(module_id):
        raise ValueError(
            f"module id '{module_id}' contains invalid characters; "
            "use only letters, digits, '_' or '-'"
        )
    return module_id


def validate_semver(version: Any, field: str = "version") -> str:
    """Validate that *version* is parseable as semantic version.

    Raises ValueError with the field name if invalid.
    """
    if not isinstance(version, str) or not version:
        raise ValueError(f"'{field}' must be a non-empty string")
    try:
        parse_version(version)
    except ValueError as exc:
        raise ValueError(f"'{field}' is not a valid version: {version}") from exc
    return version


def validate_entry_point(entry_point: Any) -> str:
    """Validate that *entry_point* follows 'module.path:ClassName' pattern."""
    if not isinstance(entry_point, str) or not entry_point:
        raise ValueError("entry_point must be a non-empty string")
    if ":" not in entry_point:
        raise ValueError(
            f"entry_point '{entry_point}' must be in format 'module.path:ClassName'"
        )
    return entry_point


def validate_permissions(permissions: Any) -> list[str]:
    """Validate permissions list; returns list of stripped strings."""
    if not isinstance(permissions, list):
        raise ValueError("permissions must be a list")
    result = []
    for item in permissions:
        if not isinstance(item, str):
            raise ValueError(f"permission entry must be a string, got: {type(item)}")
        result.append(item.strip())
    return result
