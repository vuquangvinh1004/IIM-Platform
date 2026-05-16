"""Tests for module.json manifest of normal_approximation."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

MANIFEST_PATH = Path(__file__).parent.parent / "module.json"
REQUIRED_FIELDS = [
    "id", "name", "version", "sdk_version", "min_platform_version",
    "entry_point", "description", "category", "author", "permissions",
    "tags", "supports_state_restore", "supports_export",
    "data_contract_version",
]


def test_manifest_exists():
    assert MANIFEST_PATH.exists(), "module.json not found"


def test_manifest_is_valid_json():
    raw = MANIFEST_PATH.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert isinstance(parsed, dict)


def test_manifest_required_fields():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for field in REQUIRED_FIELDS:
        assert field in data, f"Missing required field: '{field}'"


def test_manifest_id():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["id"] == "normal_approximation"


def test_manifest_entry_point_format():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    ep = data["entry_point"]
    assert ":" in ep, "entry_point must be 'module.path:ClassName'"
    module_path, _, class_name = ep.partition(":")
    assert module_path, "entry_point module path must not be empty"
    assert class_name, "entry_point class name must not be empty"


def test_manifest_supports_state_restore_is_bool():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data["supports_state_restore"], bool)


def test_manifest_permissions_is_list():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data["permissions"], list)
