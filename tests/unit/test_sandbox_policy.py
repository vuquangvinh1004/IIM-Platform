"""Unit tests for sandbox_policy.check_compatibility."""
from __future__ import annotations

from core.module_runtime.manifest_schema import ModuleManifest
from core.module_runtime.sandbox_policy import check_compatibility

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
    "permissions": [],
    "tags": [],
    "supports_state_restore": False,
    "supports_export": False,
}


def _manifest(**overrides) -> ModuleManifest:
    return ModuleManifest.model_validate({**_BASE, **overrides})


class TestCheckCompatibility:

    def test_compatible_returns_empty_list(self):
        m = _manifest()
        issues = check_compatibility(m, "1.0.0")
        assert issues == []

    def test_platform_too_old_adds_issue(self):
        m = _manifest(min_platform_version="2.0.0")
        issues = check_compatibility(m, "1.0.0")
        assert any("platform >= 2.0.0" in i for i in issues)

    def test_higher_platform_ok(self):
        m = _manifest(min_platform_version="0.9.0")
        issues = check_compatibility(m, "1.5.0")
        assert issues == []

    def test_unsupported_permission_adds_issue(self):
        m = _manifest(permissions=["storage.read", "network.unlimited"])
        issues = check_compatibility(m, "1.0.0")
        assert any("network.unlimited" in i for i in issues)

    def test_supported_permissions_no_issue(self):
        m = _manifest(permissions=["storage.read", "storage.write", "export.file"])
        issues = check_compatibility(m, "1.0.0")
        assert issues == []

    def test_multiple_issues_all_reported(self):
        m = _manifest(
            min_platform_version="99.0.0",
            permissions=["fake.perm.one", "fake.perm.two"],
        )
        issues = check_compatibility(m, "1.0.0")
        assert len(issues) >= 3  # 1 version + 2 bad permissions
