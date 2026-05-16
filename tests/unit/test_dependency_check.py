"""Unit tests for loader dependency pre-check (BUG-02)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.module_runtime.loader import (
    check_optional_dependencies,
    load_manifest,
    instantiate_module,
)
from core.module_runtime.manifest_schema import ModuleManifest
from core.utils.exceptions import DependencyMissingError


# ── Helpers ───────────────────────────────────────────────────────────────────

def _base_manifest(**overrides) -> dict:
    m = {
        "id": "dep_test",
        "name": "Dep Test",
        "version": "1.0.0",
        "sdk_version": "1.0.0",
        "min_platform_version": "1.0.0",
        "entry_point": "modules.templates.headless_test_module.entry:HeadlessTestModule",
        "description": "Test module",
        "category": "test",
        "author": "Test",
        "permissions": [],
        "tags": [],
        "supports_state_restore": False,
        "supports_export": False,
    }
    m.update(overrides)
    return m


def _write_manifest(directory: Path, data: dict) -> Path:
    path = directory / "module.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# ── Tests: check_optional_dependencies ────────────────────────────────────────


class TestCheckOptionalDependencies:

    def test_no_deps_returns_empty(self):
        m = ModuleManifest.model_validate(_base_manifest())
        assert check_optional_dependencies(m) == []

    def test_empty_deps_list_returns_empty(self):
        m = ModuleManifest.model_validate(
            _base_manifest(optional_dependencies=[])
        )
        assert check_optional_dependencies(m) == []

    def test_all_present_returns_empty(self):
        m = ModuleManifest.model_validate(
            _base_manifest(optional_dependencies=["json", "os"])
        )
        assert check_optional_dependencies(m) == []

    def test_missing_deps_returned(self):
        m = ModuleManifest.model_validate(
            _base_manifest(optional_dependencies=["json", "no_such_pkg_xyz"])
        )
        result = check_optional_dependencies(m)
        assert result == ["no_such_pkg_xyz"]

    def test_all_missing_returned(self):
        m = ModuleManifest.model_validate(
            _base_manifest(optional_dependencies=["pkg_aaa", "pkg_bbb"])
        )
        result = check_optional_dependencies(m)
        assert result == ["pkg_aaa", "pkg_bbb"]


# ── Tests: instantiate_module blocks on missing deps ──────────────────────────


class TestInstantiateDependencyCheck:

    def test_raises_dependency_missing_error(self, tmp_path):
        manifest_data = _base_manifest(
            optional_dependencies=["nonexistent_dep_xyz"]
        )
        module_dir = tmp_path / "dep_test"
        module_dir.mkdir()
        _write_manifest(module_dir, manifest_data)
        (module_dir / "__init__.py").write_text("")

        from core.module_runtime.module_context import ModuleContext, PlatformInfo

        class MockLogger:
            def info(self, *a, **kw): pass
            def debug(self, *a, **kw): pass
            def warning(self, *a, **kw): pass
            def error(self, *a, **kw): pass

        info = PlatformInfo(
            platform_version="1.0.0", sdk_version="1.0.0", os_name="Windows"
        )
        ctx = ModuleContext(
            module_id="dep_test",
            logger=MockLogger(),
            event_bus=None,
            storage_service=None,
            export_service=None,
            settings_service=None,
            activity_service=None,
            dialog_service=None,
            theme_service=None,
            path_service=None,
            workspace_service=None,
            platform_info=info,
        )

        with pytest.raises(DependencyMissingError) as exc_info:
            instantiate_module(module_dir, ctx)
        assert "nonexistent_dep_xyz" in str(exc_info.value)
        assert exc_info.value.missing == ["nonexistent_dep_xyz"]

    def test_no_error_when_deps_satisfied(self, tmp_path):
        """Module with satisfied optional_dependencies loads normally."""
        manifest_data = _base_manifest(
            optional_dependencies=["json", "os"],
            id="headless_test_module",
            entry_point="modules.templates.headless_test_module.entry:HeadlessTestModule",
        )
        module_dir = tmp_path / "headless_test_module"
        module_dir.mkdir()
        _write_manifest(module_dir, manifest_data)
        (module_dir / "__init__.py").write_text("")

        from core.module_runtime.module_context import ModuleContext, PlatformInfo

        class MockLogger:
            def info(self, *a, **kw): pass
            def debug(self, *a, **kw): pass
            def warning(self, *a, **kw): pass
            def error(self, *a, **kw): pass

        info = PlatformInfo(
            platform_version="1.0.0", sdk_version="1.0.0", os_name="Windows"
        )
        ctx = ModuleContext(
            module_id="headless_test_module",
            logger=MockLogger(),
            event_bus=None,
            storage_service=None,
            export_service=None,
            settings_service=None,
            activity_service=None,
            dialog_service=None,
            theme_service=None,
            path_service=None,
            workspace_service=None,
            platform_info=info,
        )

        # Should NOT raise
        instance = instantiate_module(module_dir, ctx)
        assert instance is not None


# ── Tests: manifest schema accepts optional_dependencies ──────────────────────


class TestManifestOptionalDependencies:

    def test_manifest_without_optional_dependencies(self):
        m = ModuleManifest.model_validate(_base_manifest())
        assert m.optional_dependencies == []

    def test_manifest_with_optional_dependencies(self):
        m = ModuleManifest.model_validate(
            _base_manifest(optional_dependencies=["numpy", "matplotlib"])
        )
        assert m.optional_dependencies == ["numpy", "matplotlib"]
