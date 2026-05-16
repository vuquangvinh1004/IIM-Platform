"""Tests: manifest validation for particle_swarm_optimization."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.module_runtime.manifest_schema import ModuleManifest

MANIFEST_PATH = Path(__file__).parent.parent / "module.json"


def test_manifest_file_exists():
    assert MANIFEST_PATH.exists(), f"module.json not found at {MANIFEST_PATH}"


def test_manifest_parses_successfully():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    assert manifest.id == "particle_swarm_optimization"
    assert "ParticleSwarmOptimizationModule" in manifest.entry_point


def test_manifest_required_fields():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    assert manifest.version == "1.0.0"
    assert manifest.sdk_version == "1.0.0"
    assert manifest.min_platform_version == "1.0.0"
    assert manifest.category == "logistics"
    assert manifest.author


def test_manifest_permissions():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    required = {"storage.read", "storage.write", "export.file"}
    assert required.issubset(set(manifest.permissions))


def test_manifest_supports_state_and_export():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    assert manifest.supports_state_restore is True
    assert manifest.supports_export is True


def test_manifest_tags_not_empty():
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    manifest = ModuleManifest(**raw)
    assert len(manifest.tags) > 0
    assert "pso" in manifest.tags or "optimization" in manifest.tags
