"""Unit tests for ModuleRegistry."""
from __future__ import annotations

from pathlib import Path

from core.module_runtime.registry import ModuleRegistry
from core.utils.constants import ModuleState


def test_register_and_retrieve(tmp_parsed_manifest, tmp_path):
    reg = ModuleRegistry()
    reg.register(tmp_parsed_manifest, tmp_path)
    assert reg.is_registered("test_module")
    record = reg.get_record("test_module")
    assert record.manifest.id == "test_module"
    assert record.state == ModuleState.DISCOVERED


def test_duplicate_register_ignored(tmp_parsed_manifest, tmp_path):
    reg = ModuleRegistry()
    reg.register(tmp_parsed_manifest, tmp_path)
    reg.register(tmp_parsed_manifest, tmp_path)  # second call silently ignored
    assert len(reg) == 1


def test_set_state(tmp_parsed_manifest, tmp_path):
    reg = ModuleRegistry()
    reg.register(tmp_parsed_manifest, tmp_path)
    reg.set_state("test_module", ModuleState.VALIDATED)
    assert reg.get_record("test_module").state == ModuleState.VALIDATED


def test_all_records(tmp_parsed_manifest, tmp_path):
    reg = ModuleRegistry()
    reg.register(tmp_parsed_manifest, tmp_path)
    assert len(reg.all_records()) == 1


def test_loaded_modules_empty_when_no_instance(tmp_parsed_manifest, tmp_path):
    reg = ModuleRegistry()
    reg.register(tmp_parsed_manifest, tmp_path)
    assert reg.loaded_modules() == []
