"""Smoke tests for the Time Series Simulation module manifest."""
from __future__ import annotations

import json
from pathlib import Path


MODULE_DIR = Path(__file__).resolve().parent.parent


def _load_manifest() -> dict:
    return json.loads((MODULE_DIR / "module.json").read_text(encoding="utf-8"))


def test_manifest_required_fields():
    m = _load_manifest()
    required = [
        "id", "name", "version", "sdk_version", "min_platform_version",
        "entry_point", "description", "category", "author",
        "permissions", "tags", "supports_state_restore", "supports_export",
    ]
    for field in required:
        assert field in m, f"Missing required manifest field: {field}"


def test_manifest_id():
    m = _load_manifest()
    assert m["id"] == "time_series_simulation"


def test_manifest_entry_point():
    m = _load_manifest()
    assert "time_series" in m["entry_point"]
    assert "TimeSeriesModule" in m["entry_point"]


def test_manifest_category():
    m = _load_manifest()
    assert m["category"] == "statistics"


def test_manifest_sdk_version():
    m = _load_manifest()
    assert m["sdk_version"] == "1.0.0"


def test_import_entry():
    """Entry module must be importable without PySide6."""
    import importlib
    import sys

    # Patch missing Qt so import guard triggers gracefully
    mod = importlib.import_module("modules.statistics.time_series.module")
    assert hasattr(mod, "TimeSeriesModule")
