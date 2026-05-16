"""Integration tests for module discovery pipeline."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.module_runtime.discovery import discover_modules
from core.module_runtime.registry import ModuleRegistry
from core.utils.constants import ModuleState


@pytest.fixture
def module_dir_tree(tmp_path) -> Path:
    """Create a temporary modules directory with one valid and one broken module."""
    # Valid module
    valid = tmp_path / "valid_mod"
    valid.mkdir()
    (valid / "module.json").write_text(
        json.dumps({
            "id": "valid_mod",
            "name": "Valid Module",
            "version": "1.0.0",
            "sdk_version": "1.0.0",
            "min_platform_version": "1.0.0",
            "entry_point": "modules.valid_mod.entry:ValidModule",
            "description": "A valid test module.",
            "category": "test",
            "author": "Tests",
            "permissions": [],
            "tags": [],
            "supports_state_restore": False,
            "supports_export": False,
        }),
        encoding="utf-8",
    )
    (valid / "__init__.py").write_text("", encoding="utf-8")

    # Broken module (missing required field)
    broken = tmp_path / "broken_mod"
    broken.mkdir()
    (broken / "module.json").write_text('{"id": "broken_mod"}', encoding="utf-8")

    return tmp_path


def test_discover_finds_valid_module(module_dir_tree):
    reg = ModuleRegistry()
    found, failed = discover_modules(reg, module_dir_tree)
    assert found == 1
    assert failed == 1
    assert reg.is_registered("valid_mod")
    assert reg.get_record("valid_mod").state == ModuleState.VALIDATED


def test_discover_empty_dir(tmp_path):
    reg = ModuleRegistry()
    found, failed = discover_modules(reg, tmp_path)
    assert found == 0
    assert failed == 0


def test_discover_nonexistent_dir(tmp_path):
    reg = ModuleRegistry()
    found, failed = discover_modules(reg, tmp_path / "does_not_exist")
    assert found == 0
    assert failed == 0
