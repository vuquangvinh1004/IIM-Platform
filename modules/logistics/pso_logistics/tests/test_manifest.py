"""test_manifest.py — Kiểm tra module.json của pso_logistics."""
from __future__ import annotations

import json
from pathlib import Path

MODULE_DIR = Path(__file__).parent.parent
MANIFEST_PATH = MODULE_DIR / "module.json"
REQUIRED_FIELDS = {
    "id", "name", "version", "sdk_version", "entry_point",
    "category", "permissions", "supports_state_restore", "supports_export",
}


def test_manifest_file_exists():
    assert MANIFEST_PATH.exists(), "module.json không tồn tại"


def test_manifest_parses():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_manifest_required_fields():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    missing = REQUIRED_FIELDS - data.keys()
    assert not missing, f"Thiếu các trường: {missing}"


def test_manifest_id_and_version():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["id"] == "pso_logistics"
    assert data["version"] == "1.2.0"
    assert data["sdk_version"] == "1.0.0"


def test_manifest_permissions():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    perms = set(data["permissions"])
    assert "storage.read" in perms
    assert "storage.write" in perms
    assert "export.file" in perms


def test_manifest_flags_and_tags():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert data["supports_state_restore"] is True
    assert data["supports_export"] is True
    assert isinstance(data.get("tags"), list)
    assert len(data["tags"]) > 0
