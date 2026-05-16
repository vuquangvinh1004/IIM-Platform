"""Unit tests for manifest schema validation."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.module_runtime.manifest_schema import ModuleManifest


def test_valid_manifest_parses(tmp_manifest):
    m = ModuleManifest.model_validate(tmp_manifest)
    assert m.id == "test_module"
    assert m.version == "1.0.0"
    assert m.supports_export is False


def test_missing_required_field_raises(tmp_manifest):
    del tmp_manifest["entry_point"]
    with pytest.raises(ValidationError):
        ModuleManifest.model_validate(tmp_manifest)


def test_invalid_module_id_raises(tmp_manifest):
    tmp_manifest["id"] = "bad id!"
    with pytest.raises(ValidationError):
        ModuleManifest.model_validate(tmp_manifest)


def test_invalid_version_raises(tmp_manifest):
    tmp_manifest["version"] = "not-a-version!!!"
    with pytest.raises(ValidationError):
        ModuleManifest.model_validate(tmp_manifest)


def test_invalid_entry_point_raises(tmp_manifest):
    tmp_manifest["entry_point"] = "module_without_colon"
    with pytest.raises(ValidationError):
        ModuleManifest.model_validate(tmp_manifest)


def test_permissions_must_be_list(tmp_manifest):
    tmp_manifest["permissions"] = "storage.read"
    with pytest.raises(ValidationError):
        ModuleManifest.model_validate(tmp_manifest)
