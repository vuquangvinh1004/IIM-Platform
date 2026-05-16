"""Tests for normal_distribution module manifest validation."""
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.module_runtime.manifest_schema import ModuleManifest

MANIFEST_PATH = Path(__file__).parent.parent / "module.json"


def test_manifest_file_exists():
    assert MANIFEST_PATH.exists(), f"module.json not found at {MANIFEST_PATH}"


def test_manifest_parses_successfully():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    assert manifest.id == "normal_distribution"
    assert manifest.entry_point.endswith(":NormalDistributionModule")


def test_manifest_has_required_permissions():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    required = {"storage.read", "storage.write", "export.file"}
    assert required.issubset(set(manifest.permissions))


def test_manifest_supports_state_and_export():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    assert manifest.supports_state_restore is True
    assert manifest.supports_export is True


def test_manifest_sdk_version_field():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    assert manifest.sdk_version == "1.0.0"
