"""Integration tests for SettingsService."""
from __future__ import annotations

import pytest

from core.services.settings_service import SettingsService
from core.storage.models import ModuleRegistry


def _seed_registry(db_factory, module_id: str) -> None:
    """Insert a minimal module_registry row so FK constraint is satisfied."""
    with db_factory() as session:
        session.add(ModuleRegistry(
            module_id=module_id,
            name=f"Test {module_id}",
            version="1.0.0",
            entry_point=f"modules.{module_id}.entry:Cls",
            install_path=f"/modules/{module_id}",
        ))
        session.commit()


class TestAppSettings:

    def test_get_missing_returns_default(self, db_factory):
        svc = SettingsService()
        assert svc.get_app_setting("nonexistent", default="fallback") == "fallback"

    def test_set_and_get_string(self, db_factory):
        svc = SettingsService()
        svc.set_app_setting("theme", "dark")
        assert svc.get_app_setting("theme") == "dark"

    def test_set_and_get_number(self, db_factory):
        svc = SettingsService()
        svc.set_app_setting("precision", 4)
        result = svc.get_app_setting("precision")
        assert int(result) == 4

    def test_update_existing(self, db_factory):
        svc = SettingsService()
        svc.set_app_setting("key", "v1")
        svc.set_app_setting("key", "v2")
        assert svc.get_app_setting("key") == "v2"

    def test_set_dict_value(self, db_factory):
        svc = SettingsService()
        svc.set_app_setting("config", {"a": 1, "b": 2})
        result = svc.get_app_setting("config")
        assert result == {"a": 1, "b": 2}


class TestModuleSettings:

    def test_get_missing_returns_default(self, db_factory):
        svc = SettingsService()
        assert svc.get_module_setting("mod_x", "key", default=42) == 42

    def test_set_and_get(self, db_factory):
        _seed_registry(db_factory, "mod_a")
        svc = SettingsService()
        svc.set_module_setting("mod_a", "precision", 6)
        result = svc.get_module_setting("mod_a", "precision")
        assert int(result) == 6

    def test_different_modules_isolated(self, db_factory):
        _seed_registry(db_factory, "mod_a")
        _seed_registry(db_factory, "mod_b")
        svc = SettingsService()
        svc.set_module_setting("mod_a", "key", "val_a")
        svc.set_module_setting("mod_b", "key", "val_b")
        assert svc.get_module_setting("mod_a", "key") == "val_a"
        assert svc.get_module_setting("mod_b", "key") == "val_b"

    def test_get_all_module_settings(self, db_factory):
        _seed_registry(db_factory, "mod_a")
        svc = SettingsService()
        svc.set_module_setting("mod_a", "k1", "v1")
        svc.set_module_setting("mod_a", "k2", "v2")
        all_settings = svc.get_all_module_settings("mod_a")
        assert all_settings["k1"] == "v1"
        assert all_settings["k2"] == "v2"

    def test_get_all_empty_module(self, db_factory):
        svc = SettingsService()
        assert svc.get_all_module_settings("no_such_mod") == {}

    def test_update_existing_module_setting(self, db_factory):
        _seed_registry(db_factory, "mod_a")
        svc = SettingsService()
        svc.set_module_setting("mod_a", "k", "old")
        svc.set_module_setting("mod_a", "k", "new")
        assert svc.get_module_setting("mod_a", "k") == "new"
