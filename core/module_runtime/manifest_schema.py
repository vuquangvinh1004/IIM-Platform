"""Pydantic schema for IIMP module manifests (module.json).

Validation here is the single source of truth for what constitutes
a valid manifest. If a field is added here it must also be documented
in IIMP_MODULE_SDK.md.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator

from core.utils.validators import (
    validate_entry_point,
    validate_module_id,
    validate_permissions,
    validate_semver,
)


class UIHints(BaseModel):
    """Optional UI layout hints supplied in the manifest."""

    min_width: int = 640
    min_height: int = 480
    layout_mode: str = "default"


class ModuleManifest(BaseModel):
    """Validated representation of a module.json manifest.

    Required fields follow the SDK specification §5.2.
    Optional fields follow §5.3.
    """

    # ── Required ──────────────────────────────────────────────────────────────
    id: str
    name: str
    version: str
    sdk_version: str
    min_platform_version: str
    entry_point: str
    description: str
    category: str
    author: str
    permissions: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    supports_state_restore: bool
    supports_export: bool

    # ── Optional ──────────────────────────────────────────────────────────────
    icon: str | None = None
    homepage: str | None = None
    license: str | None = None
    ui: UIHints | None = None
    data_contract_version: str | None = None
    default_settings: dict[str, Any] = Field(default_factory=dict)
    capabilities: list[str] = Field(default_factory=list)
    compatibility_notes: str | None = None
    optional_dependencies: list[str] = Field(default_factory=list)

    # ── Field validators ──────────────────────────────────────────────────────

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        return validate_module_id(v)

    @field_validator("version", "sdk_version", "min_platform_version")
    @classmethod
    def _validate_version(cls, v: str, info) -> str:
        return validate_semver(v, field=info.field_name)

    @field_validator("entry_point")
    @classmethod
    def _validate_entry_point(cls, v: str) -> str:
        return validate_entry_point(v)

    @field_validator("permissions")
    @classmethod
    def _validate_permissions(cls, v: list) -> list[str]:
        return validate_permissions(v)
