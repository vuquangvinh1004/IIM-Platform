"""Tests for central_limit_theorem manifest file."""
from __future__ import annotations

import json
from pathlib import Path

MANIFEST_PATH = Path(__file__).parent.parent / "module.json"


def test_manifest_file_exists():
    assert MANIFEST_PATH.exists(), "module.json not found"


def test_manifest_parses_successfully():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_manifest_id():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["id"] == "central_limit_theorem"


def test_manifest_entry_point():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "CentralLimitTheoremModule" in data["entry_point"]


def test_manifest_has_required_fields():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    required = {
        "id", "name", "version", "sdk_version",
        "min_platform_version", "entry_point",
        "description", "category", "author",
        "permissions", "tags",
        "supports_state_restore", "supports_export",
    }
    for field in required:
        assert field in data, f"Missing required field: {field}"


def test_manifest_has_required_permissions():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    perms = set(data.get("permissions", []))
    required = {"storage.read", "storage.write", "settings.read", "settings.write"}
    assert required <= perms, f"Missing permissions: {required - perms}"


def test_manifest_state_restore_true():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data.get("supports_state_restore") is True


def test_manifest_export_false():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data.get("supports_export") is False


def test_manifest_sdk_version():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["sdk_version"] == "1.0.0"


def test_manifest_version():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["version"] == "1.0.0"


def test_manifest_category():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["category"] == "statistics"


def test_manifest_has_ui_hints():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert "ui" in data
    ui = data["ui"]
    assert "min_width" in ui
    assert "min_height" in ui
    assert ui["min_width"] >= 800
    assert ui["min_height"] >= 600


def test_manifest_tags_include_clt():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    tags = data.get("tags", [])
    assert "clt" in tags or "central-limit-theorem" in tags
