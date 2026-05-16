"""Tests for LLNDiceModule manifest file."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

MANIFEST_PATH = (
    Path(__file__).parent.parent / "module.json"
)


def test_manifest_file_exists():
    assert MANIFEST_PATH.exists(), "module.json not found"


def test_manifest_parses_successfully():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_manifest_id():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["id"] == "law_of_large_numbers_dice"


def test_manifest_entry_point():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "LLNDiceModule" in data["entry_point"]


def test_manifest_has_required_permissions():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    perms = set(data.get("permissions", []))
    assert {"storage.read", "storage.write", "export.file",
            "settings.read", "settings.write"} <= perms


def test_manifest_supports_state_and_export():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data.get("supports_state_restore") is True
    assert data.get("supports_export") is True


def test_manifest_sdk_version():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["sdk_version"] == "1.0.0"


def test_manifest_version():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["version"] == "1.0.0"


def test_manifest_category():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["category"] == "statistics"
