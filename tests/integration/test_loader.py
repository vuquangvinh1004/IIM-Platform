"""Integration tests for the module loader pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.module_runtime.loader import (
    load_manifest,
    load_module_class,
    instantiate_module,
)
from core.module_runtime.manifest_schema import ModuleManifest
from core.utils.exceptions import (
    ManifestNotFoundError,
    ManifestValidationError,
    ModuleLoadError,
    ModuleNotFoundError,
)

# ── Fixtures ──────────────────────────────────────────────────────────────────

_VALID_MANIFEST = {
    "id": "headless_test_module",
    "name": "Headless Test Module",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.templates.headless_test_module.entry:HeadlessTestModule",
    "description": "Minimal module for loader integration tests.",
    "category": "template",
    "author": "IIMP Team",
    "permissions": [],
    "tags": ["test"],
    "supports_state_restore": False,
    "supports_export": False,
    "data_contract_version": "1.0.0",
    "default_settings": {},
}


def _write_manifest(directory: Path, data: dict) -> Path:
    path = directory / "module.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _mock_context():
    class MockLogger:
        def info(self, *a, **kw): pass
        def debug(self, *a, **kw): pass
        def warning(self, *a, **kw): pass
        def error(self, *a, **kw): pass

    from core.module_runtime.module_context import ModuleContext, PlatformInfo
    info = PlatformInfo(platform_version="1.0.0", sdk_version="1.0.0", os_name="Windows")
    return ModuleContext(
        module_id="headless_test_module",
        logger=MockLogger(),
        event_bus=None,
        storage_service=None,
        settings_service=None,
        export_service=None,
        activity_service=None,
        dialog_service=None,
        theme_service=None,
        path_service=None,
        platform_info=info,
    )


# ── load_manifest tests ───────────────────────────────────────────────────────

class TestLoadManifest:

    def test_valid_manifest_returns_model(self, tmp_path):
        _write_manifest(tmp_path, _VALID_MANIFEST)
        manifest = load_manifest(tmp_path)
        assert isinstance(manifest, ModuleManifest)
        assert manifest.id == "headless_test_module"

    def test_missing_manifest_raises(self, tmp_path):
        with pytest.raises(ManifestNotFoundError):
            load_manifest(tmp_path)

    def test_invalid_json_raises(self, tmp_path):
        (tmp_path / "module.json").write_text("{bad json", encoding="utf-8")
        with pytest.raises(ManifestValidationError):
            load_manifest(tmp_path)

    def test_missing_required_field_raises(self, tmp_path):
        incomplete = {k: v for k, v in _VALID_MANIFEST.items() if k != "name"}
        _write_manifest(tmp_path, incomplete)
        with pytest.raises(ManifestValidationError):
            load_manifest(tmp_path)


# ── load_module_class tests ───────────────────────────────────────────────────

class TestLoadModuleClass:

    def test_valid_entry_point_returns_class(self):
        manifest = ModuleManifest.model_validate(_VALID_MANIFEST)
        cls = load_module_class(manifest)
        from modules.templates.headless_test_module.module import HeadlessTestModule
        assert cls is HeadlessTestModule

    def test_bad_module_path_raises(self):
        bad = {**_VALID_MANIFEST, "entry_point": "modules.nonexistent.mod:NoClass"}
        manifest = ModuleManifest.model_validate(bad)
        with pytest.raises(ModuleNotFoundError):
            load_module_class(manifest)

    def test_missing_class_in_module_raises(self):
        bad = {**_VALID_MANIFEST, "entry_point": "modules.templates.headless_test_module.entry:GhostClass"}
        manifest = ModuleManifest.model_validate(bad)
        with pytest.raises(ModuleNotFoundError):
            load_module_class(manifest)

    def test_non_basemodule_class_raises(self):
        # json module is importable but json.JSONDecodeError is not a BaseModule subclass
        bad = {**_VALID_MANIFEST, "entry_point": "json:JSONDecodeError"}
        manifest = ModuleManifest.model_validate(bad)
        with pytest.raises(ModuleLoadError):
            load_module_class(manifest)


# ── instantiate_module tests ──────────────────────────────────────────────────

class TestInstantiateModule:

    def test_valid_module_instantiated(self):
        """Use the headless test module directory (no PySide6 dependency)."""
        from pathlib import Path
        starter_dir = Path("modules/templates/headless_test_module")
        ctx = _mock_context()
        instance = instantiate_module(starter_dir, ctx)
        assert instance is not None
        assert instance.module_id == "headless_test_module"

    def test_missing_manifest_raises_load_error(self, tmp_path):
        ctx = _mock_context()
        with pytest.raises((ManifestNotFoundError, ModuleLoadError)):
            instantiate_module(tmp_path, ctx)
