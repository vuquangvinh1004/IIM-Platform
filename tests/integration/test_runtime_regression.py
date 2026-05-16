"""Runtime regression tests — manifest errors, load errors, state errors.

These tests verify that the platform handles failure modes gracefully:
- bad manifests don't crash the registry or discovery pipeline
- load failures mark module as ERROR, don't propagate to crash shell
- state errors are contained and fall back cleanly
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.module_runtime.discovery import discover_modules
from core.module_runtime.loader import load_manifest, load_module_class, instantiate_module
from core.module_runtime.registry import ModuleRegistry
from core.module_runtime.state_manager import StateManager
from core.utils.constants import ModuleState
from core.utils.exceptions import (
    ManifestNotFoundError,
    ManifestValidationError,
    ModuleLoadError,
    ModuleNotFoundError,
    StateSaveError,
    StateRestoreError,
)


# ── Manifest regression ───────────────────────────────────────────────────────

class TestManifestRegression:

    def _valid_data(self, module_id: str = "test_mod") -> dict:
        return {
            "id": module_id,
            "name": "Test",
            "version": "1.0.0",
            "sdk_version": "1.0.0",
            "min_platform_version": "1.0.0",
            "entry_point": f"modules.{module_id}.entry:Cls",
            "description": "desc",
            "category": "test",
            "author": "tester",
            "permissions": [],
            "tags": [],
            "supports_state_restore": False,
            "supports_export": False,
        }

    def test_no_manifest_file(self, tmp_path):
        with pytest.raises(ManifestNotFoundError) as exc_info:
            load_manifest(tmp_path)
        assert "module.json not found" in str(exc_info.value)

    def test_empty_json_object_raises(self, tmp_path):
        (tmp_path / "module.json").write_text("{}", encoding="utf-8")
        with pytest.raises(ManifestValidationError):
            load_manifest(tmp_path)

    def test_invalid_version_string_raises(self, tmp_path):
        data = self._valid_data()
        data["version"] = "NOTAVERSION"
        (tmp_path / "module.json").write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ManifestValidationError):
            load_manifest(tmp_path)

    def test_invalid_entry_point_no_colon_raises(self, tmp_path):
        data = self._valid_data()
        data["entry_point"] = "no_colon_here"
        (tmp_path / "module.json").write_text(json.dumps(data), encoding="utf-8")
        with pytest.raises(ManifestValidationError):
            load_manifest(tmp_path)

    def test_discovery_bad_manifest_counted_as_failed(self, tmp_path):
        """A broken module.json increments failed count, doesn't raise."""
        (tmp_path / "bad_mod").mkdir()
        (tmp_path / "bad_mod" / "module.json").write_text('{"id": "bad"}', encoding="utf-8")
        reg = ModuleRegistry()
        found, failed = discover_modules(reg, tmp_path)
        assert found == 0
        assert failed == 1

    def test_discovery_valid_plus_broken_counts_correctly(self, tmp_path):
        """Mixed directory: valid module registered, broken one counted but ignored."""
        valid = tmp_path / "good_mod"
        valid.mkdir()
        (valid / "module.json").write_text(json.dumps({
            "id": "good_mod",
            "name": "Good",
            "version": "1.0.0",
            "sdk_version": "1.0.0",
            "min_platform_version": "1.0.0",
            "entry_point": "modules.good_mod.entry:Cls",
            "description": "d",
            "category": "test",
            "author": "t",
            "permissions": [],
            "tags": [],
            "supports_state_restore": False,
            "supports_export": False,
        }), encoding="utf-8")
        (valid / "__init__.py").write_text("", encoding="utf-8")

        broken = tmp_path / "bad_mod"
        broken.mkdir()
        (broken / "module.json").write_text('{}', encoding="utf-8")

        reg = ModuleRegistry()
        found, failed = discover_modules(reg, tmp_path)
        assert found == 1
        assert failed == 1


# ── Load error regression ─────────────────────────────────────────────────────

class TestLoadErrorRegression:

    def test_nonexistent_import_path_raises_not_found(self):
        from core.module_runtime.manifest_schema import ModuleManifest
        m = ModuleManifest.model_validate({
            "id": "x",
            "name": "X",
            "version": "1.0.0",
            "sdk_version": "1.0.0",
            "min_platform_version": "1.0.0",
            "entry_point": "modules.totally.fake.path:Xyz",
            "description": "d",
            "category": "c",
            "author": "a",
            "permissions": [],
            "tags": [],
            "supports_state_restore": False,
            "supports_export": False,
        })
        with pytest.raises(ModuleNotFoundError):
            load_module_class(m)

    def test_non_base_module_class_raises_load_error(self):
        from core.module_runtime.manifest_schema import ModuleManifest
        # json.JSONDecoderError is a real class but NOT a BaseModule subclass
        m = ModuleManifest.model_validate({
            "id": "x",
            "name": "X",
            "version": "1.0.0",
            "sdk_version": "1.0.0",
            "min_platform_version": "1.0.0",
            "entry_point": "json:JSONDecodeError",
            "description": "d",
            "category": "c",
            "author": "a",
            "permissions": [],
            "tags": [],
            "supports_state_restore": False,
            "supports_export": False,
        })
        with pytest.raises(ModuleLoadError):
            load_module_class(m)


# ── State error regression ────────────────────────────────────────────────────

class TestStateErrorRegression:

    def test_get_state_raises_wrapped_in_state_save_error(self, db_factory):
        class BrokenModule:
            manifest = {"id": "broken", "supports_state_restore": True}
            module_id = "broken"

            def get_state(self):
                raise RuntimeError("unexpected crash in get_state")

        with pytest.raises(StateSaveError) as exc_info:
            StateManager().save_state(BrokenModule())
        assert "get_state()" in str(exc_info.value)

    def test_restore_state_raises_wrapped_in_state_restore_error(self, db_factory):
        from core.storage.models import ModuleRegistry as DBReg, ModuleSession

        # Seed registry + session
        with db_factory() as session:
            session.add(DBReg(
                module_id="mod_crash",
                name="CrashMod",
                version="1.0.0",
                entry_point="modules.x:X",
                install_path="/m/x",
            ))
            session.commit()
            session.add(ModuleSession(
                module_id="mod_crash",
                session_state='{"a": 1}',
                is_last_active=True,
            ))
            session.commit()

        class CrashOnRestore:
            manifest = {"id": "mod_crash", "supports_state_restore": True}
            module_id = "mod_crash"

            def restore_state(self, state: dict):
                raise ValueError("restore crashed")

        with pytest.raises(StateRestoreError):
            StateManager().restore_state(CrashOnRestore())

    def test_restore_returns_false_if_no_saved_state(self, db_factory):
        class SimpleModule:
            manifest = {"id": "no_state", "supports_state_restore": True}
            module_id = "no_state"

        result = StateManager().restore_state(SimpleModule())
        assert result is False
