"""Manifest tests for multiple_linear_regression_3d module."""
from __future__ import annotations

import json
from pathlib import Path


MANIFEST_PATH = Path(__file__).parent.parent / "module.json"


def _load() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def test_manifest_exists() -> None:
    assert MANIFEST_PATH.exists(), "module.json not found"


def test_manifest_required_fields() -> None:
    data = _load()
    required = [
        "id",
        "name",
        "version",
        "sdk_version",
        "min_platform_version",
        "entry_point",
        "description",
        "category",
        "author",
        "permissions",
        "tags",
        "supports_state_restore",
        "supports_export",
    ]
    for field in required:
        assert field in data, f"Missing required field: {field}"


def test_manifest_identity() -> None:
    data = _load()
    assert data["id"] == "multiple_linear_regression_3d"
    assert data["category"] == "statistics"


def test_entry_point_shape() -> None:
    data = _load()
    assert ":" in data["entry_point"]
    assert "MultipleLinearRegression3DModule" in data["entry_point"]
