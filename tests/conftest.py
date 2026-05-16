"""Shared pytest fixtures for IIMP test suite.

How to use:
- ``tmp_registry``   — empty in-memory ModuleRegistry
- ``tmp_manifest``   — minimal valid ModuleManifest dict
- ``tmp_module_dir`` — temp directory with a valid module.json + entry.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.module_runtime.manifest_schema import ModuleManifest
from core.module_runtime.registry import ModuleRegistry


# ── Minimal valid manifest dict ───────────────────────────────────────────────

@pytest.fixture
def tmp_manifest() -> dict:
    return {
        "id": "test_module",
        "name": "Test Module",
        "version": "1.0.0",
        "sdk_version": "1.0.0",
        "min_platform_version": "1.0.0",
        "entry_point": "modules.templates.starter_module.entry:StarterModule",
        "description": "A test module.",
        "category": "test",
        "author": "Test Suite",
        "permissions": ["storage.read"],
        "tags": ["test"],
        "supports_state_restore": False,
        "supports_export": False,
    }


@pytest.fixture
def tmp_parsed_manifest(tmp_manifest) -> ModuleManifest:
    return ModuleManifest.model_validate(tmp_manifest)


# ── In-memory registry ────────────────────────────────────────────────────────

@pytest.fixture
def tmp_registry() -> ModuleRegistry:
    return ModuleRegistry()


# ── Temporary module directory with minimal valid files ───────────────────────

@pytest.fixture
def tmp_module_dir(tmp_path: Path, tmp_manifest: dict) -> Path:
    """Create a minimal module directory in a temp folder."""
    module_dir = tmp_path / "test_module"
    module_dir.mkdir()

    # Write manifest
    (module_dir / "module.json").write_text(
        json.dumps(tmp_manifest, indent=2), encoding="utf-8"
    )

    # Write minimal __init__.py
    (module_dir / "__init__.py").write_text("", encoding="utf-8")

    return module_dir
