"""test_manifest.py — Kiểm tra module.json của pso_logistics_map."""
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
    assert data["id"] == "pso_logistics_map"
    assert data["version"] == "1.1.0"
    assert data["sdk_version"] == "1.0.0"


def test_manifest_entry_point_format():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    entry = data["entry_point"]
    assert ":" in entry, "entry_point phải có dạng 'module.path:ClassName'"
    module_path, class_name = entry.rsplit(":", 1)
    assert module_path.startswith("modules.logistics.pso_logistics_map")
    assert class_name == "PSOLogisticsMapModule"


def test_manifest_permissions():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    perms = set(data["permissions"])
    assert "storage.read" in perms
    assert "storage.write" in perms
    assert "export.file" in perms


def test_manifest_dependencies_include_osmium():
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    packages = data["dependencies"]["packages"]
    assert "osmium" in packages, "osmium phải khai báo trong dependencies.packages"
    assert "networkx" in packages
    assert "scipy" in packages
