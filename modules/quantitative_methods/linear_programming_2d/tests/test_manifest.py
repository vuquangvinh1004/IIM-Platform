"""Manifest validation tests for linear_programming_2d module."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

_MODULE_DIR = Path(__file__).resolve().parent.parent
_MANIFEST_PATH = _MODULE_DIR / "module.json"

REQUIRED_FIELDS = [
    "id", "name", "version", "sdk_version", "min_platform_version",
    "entry_point", "description", "category", "author",
    "permissions", "tags", "supports_state_restore", "supports_export",
]


@pytest.fixture(scope="module")
def manifest() -> dict:
    assert _MANIFEST_PATH.exists(), f"module.json not found at {_MANIFEST_PATH}"
    return json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))


class TestManifest:
    """Validate module.json against SDK spec."""

    def test_file_exists(self) -> None:
        assert _MANIFEST_PATH.exists()

    def test_valid_json(self) -> None:
        json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    def test_required_field_present(self, manifest: dict, field: str) -> None:
        assert field in manifest, f"Missing required field: {field}"

    def test_id_value(self, manifest: dict) -> None:
        assert manifest["id"] == "linear_programming_2d"

    def test_category(self, manifest: dict) -> None:
        assert manifest["category"] == "quantitative_methods"

    def test_entry_point_format(self, manifest: dict) -> None:
        ep = manifest["entry_point"]
        assert ":" in ep
        assert ep.startswith("modules.quantitative_methods.linear_programming_2d.")

    def test_version_semver(self, manifest: dict) -> None:
        parts = manifest["version"].split(".")
        assert len(parts) == 3
        assert all(p.isdigit() for p in parts)

    def test_permissions_is_list(self, manifest: dict) -> None:
        assert isinstance(manifest["permissions"], list)

    def test_tags_is_list(self, manifest: dict) -> None:
        assert isinstance(manifest["tags"], list)
        assert len(manifest["tags"]) >= 1

    def test_supports_state_restore(self, manifest: dict) -> None:
        assert manifest["supports_state_restore"] is True

    def test_supports_export(self, manifest: dict) -> None:
        assert manifest["supports_export"] is True
