"""Unit tests for PermissionService."""
from __future__ import annotations

from core.module_runtime.manifest_schema import ModuleManifest
from core.services.permission_service import PermissionService

_BASE = {
    "id": "mod",
    "name": "Mod",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.mod.entry:Mod",
    "description": "test",
    "category": "test",
    "author": "tests",
    "permissions": ["storage.read", "export.file"],
    "tags": [],
    "supports_state_restore": False,
    "supports_export": False,
}


def _manifest(**overrides) -> ModuleManifest:
    return ModuleManifest.model_validate({**_BASE, **overrides})


class TestPermissionService:

    def setup_method(self):
        self.svc = PermissionService()

    def test_has_permission_true(self):
        m = _manifest()
        assert self.svc.has_permission(m, "storage.read") is True

    def test_has_permission_false(self):
        m = _manifest()
        assert self.svc.has_permission(m, "storage.write") is False

    def test_unsupported_permissions_empty_when_all_valid(self):
        m = _manifest()
        assert self.svc.unsupported_permissions(m) == []

    def test_unsupported_permissions_returns_bad_ones(self):
        m = _manifest(permissions=["storage.read", "hax.root"])
        bad = self.svc.unsupported_permissions(m)
        assert "hax.root" in bad
        assert "storage.read" not in bad

    def test_empty_permissions(self):
        m = _manifest(permissions=[])
        assert self.svc.has_permission(m, "storage.read") is False
        assert self.svc.unsupported_permissions(m) == []
