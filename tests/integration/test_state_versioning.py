"""Integration tests for state versioning and migration (BUG-03).

Tests cover:
- _state_version auto-injection on save
- Version match → normal restore
- Version mismatch → migrate_state() called
- migrate_state() failure → fallback to defaults
- No data_contract_version → no version injected (backward compat)
"""
from __future__ import annotations

import json

import pytest

from core.module_runtime.state_manager import StateManager
from core.storage.models import ModuleRegistry, ModuleSession
from core.utils.exceptions import StateRestoreError


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_module(
    module_id: str,
    state: dict,
    *,
    supports: bool = True,
    data_contract_version: str | None = "1.0.0",
    migrate_fn=None,
    raise_on_restore: bool = False,
):
    class MockModule:
        context = None

        def get_state(self):
            return dict(state)  # copy

        def restore_state(self, s: dict):
            if raise_on_restore:
                raise ValueError("restore failed by design")
            state.clear()
            state.update(s)

        def migrate_state(self, old_state: dict, old_version: str) -> dict:
            if migrate_fn is not None:
                return migrate_fn(old_state, old_version)
            return old_state

        @property
        def module_id(self):
            return module_id

    manifest = {
        "id": module_id,
        "supports_state_restore": supports,
    }
    if data_contract_version is not None:
        manifest["data_contract_version"] = data_contract_version

    MockModule.manifest = manifest
    return MockModule()


def _seed(db_factory, module_id: str):
    with db_factory() as session:
        session.add(ModuleRegistry(
            module_id=module_id,
            name="Test",
            version="1.0.0",
            entry_point="m.e:M",
            install_path="/m",
        ))
        session.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestStateVersionInjection:

    def test_save_injects_state_version(self, db_factory):
        _seed(db_factory, "sv_inject")
        mod = _make_module("sv_inject", {"x": 1}, data_contract_version="2.0.0")
        sm = StateManager()
        sm.save_state(mod)

        with db_factory() as session:
            rec = session.query(ModuleSession).filter_by(
                module_id="sv_inject", is_last_active=True
            ).first()
        saved = json.loads(rec.session_state)
        assert saved["_state_version"] == "2.0.0"
        assert saved["x"] == 1

    def test_save_without_data_contract_no_version(self, db_factory):
        _seed(db_factory, "sv_none")
        mod = _make_module("sv_none", {"y": 2}, data_contract_version=None)
        sm = StateManager()
        sm.save_state(mod)

        with db_factory() as session:
            rec = session.query(ModuleSession).filter_by(
                module_id="sv_none", is_last_active=True
            ).first()
        saved = json.loads(rec.session_state)
        assert "_state_version" not in saved

    def test_save_preserves_existing_state_version(self, db_factory):
        """If module explicitly sets _state_version, save_state keeps it."""
        _seed(db_factory, "sv_keep")
        mod = _make_module(
            "sv_keep",
            {"_state_version": "custom", "z": 3},
            data_contract_version="1.0.0",
        )
        sm = StateManager()
        sm.save_state(mod)

        with db_factory() as session:
            rec = session.query(ModuleSession).filter_by(
                module_id="sv_keep", is_last_active=True
            ).first()
        saved = json.loads(rec.session_state)
        # setdefault should keep existing "custom" value
        assert saved["_state_version"] == "custom"


class TestVersionMatchRestore:

    def test_same_version_restores_normally(self, db_factory):
        _seed(db_factory, "vm_ok")
        sm = StateManager()

        # Save with version 1.0.0
        mod_save = _make_module("vm_ok", {"a": 10}, data_contract_version="1.0.0")
        sm.save_state(mod_save)

        # Restore with same version 1.0.0
        target = {}
        mod_restore = _make_module("vm_ok", target, data_contract_version="1.0.0")
        assert sm.restore_state(mod_restore) is True
        assert target.get("a") == 10

    def test_no_version_in_saved_state_restores(self, db_factory):
        """Legacy state without _state_version should still restore."""
        _seed(db_factory, "vm_legacy")
        sm = StateManager()

        # Manually insert a state record without _state_version
        with db_factory() as session:
            session.add(ModuleSession(
                module_id="vm_legacy",
                session_name="last",
                session_state=json.dumps({"b": 20}),
                is_last_active=True,
            ))
            session.commit()

        target = {}
        mod = _make_module("vm_legacy", target, data_contract_version="1.0.0")
        assert sm.restore_state(mod) is True
        assert target.get("b") == 20


class TestVersionMismatchMigration:

    def test_mismatch_calls_migrate_state(self, db_factory):
        _seed(db_factory, "vm_mig")
        sm = StateManager()

        # Save with version 1.0.0
        mod_save = _make_module("vm_mig", {"old_key": 5}, data_contract_version="1.0.0")
        sm.save_state(mod_save)

        # Restore with version 2.0.0 — migration renames key
        def migrate(old_state, old_ver):
            assert old_ver == "1.0.0"
            return {"new_key": old_state["old_key"] * 10}

        target = {}
        mod_restore = _make_module(
            "vm_mig", target,
            data_contract_version="2.0.0",
            migrate_fn=migrate,
        )
        assert sm.restore_state(mod_restore) is True
        assert target.get("new_key") == 50

    def test_mismatch_migration_failure_returns_false(self, db_factory):
        _seed(db_factory, "vm_mig_fail")
        sm = StateManager()

        mod_save = _make_module("vm_mig_fail", {"c": 3}, data_contract_version="1.0.0")
        sm.save_state(mod_save)

        def bad_migrate(old_state, old_ver):
            raise RuntimeError("cannot migrate")

        target = {}
        mod_restore = _make_module(
            "vm_mig_fail", target,
            data_contract_version="2.0.0",
            migrate_fn=bad_migrate,
        )
        # Should return False (discard old state, use defaults)
        assert sm.restore_state(mod_restore) is False
        # target should not be modified
        assert target == {}

    def test_mismatch_without_custom_migrate_uses_default(self, db_factory):
        """Default migrate_state returns old_state unchanged — best-effort."""
        _seed(db_factory, "vm_default")
        sm = StateManager()

        mod_save = _make_module("vm_default", {"d": 99}, data_contract_version="1.0.0")
        sm.save_state(mod_save)

        target = {}
        mod_restore = _make_module(
            "vm_default", target,
            data_contract_version="2.0.0",
            # No custom migrate_fn → uses BaseModule default
        )
        assert sm.restore_state(mod_restore) is True
        assert target.get("d") == 99


class TestBaseModuleMigrateState:

    def test_default_migrate_state_returns_old_state(self):
        from core.module_runtime.base_module import BaseModule

        class Concrete(BaseModule):
            def on_load(self): pass
            def build_view(self): pass
            def on_activate(self): pass
            def on_deactivate(self): pass
            def on_unload(self): pass

        mod = Concrete(manifest={"id": "t", "data_contract_version": "1.0.0"}, context=None)
        old = {"key": "value"}
        result = mod.migrate_state(old, "0.5.0")
        assert result is old  # same reference — pass-through
