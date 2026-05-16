"""Integration tests for StateManager."""
from __future__ import annotations

import pytest

from core.module_runtime.state_manager import StateManager, clear_all_sessions
from core.storage.models import ModuleRegistry, ModuleSession
from core.utils.exceptions import StateSaveError, StateRestoreError


# ── Mock module helpers ───────────────────────────────────────────────────────

def _make_mock_module(module_id: str, state: dict, *, supports: bool = True, raise_on_restore: bool = False):
    """Return a simple object implementing the BaseModule contract we need.

    Note: class body scope cannot access enclosing function locals in Python 3,
    so manifest attributes are assigned after class creation.
    """

    class MockModule:
        context = None

        def get_state(self):
            return state

        def restore_state(self, s: dict):
            if raise_on_restore:
                raise ValueError("restore failed by design")
            state.update(s)

        @property
        def module_id(self):
            return module_id

    # Assign class-level attributes outside the class body to avoid NameError
    # (Python 3 class bodies cannot form closures over enclosing function locals)
    MockModule.manifest = {
        "id": module_id,
        "supports_state_restore": supports,
    }

    return MockModule()


def _seed_registry(db_factory, module_id: str) -> None:
    """Insert a minimal module_registry row so FK constraint is satisfied."""
    with db_factory() as session:
        session.add(ModuleRegistry(
            module_id=module_id,
            name="Test Mod",
            version="1.0.0",
            entry_point="modules.test.entry:T",
            install_path="/modules/test",
        ))
        session.commit()


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSaveState:

    def test_save_creates_session_record(self, db_factory):
        _seed_registry(db_factory, "mod_a")
        mod = _make_mock_module("mod_a", {"x": 1})
        sm = StateManager()
        sm.save_state(mod)
        with db_factory() as session:
            rows = session.query(ModuleSession).filter_by(module_id="mod_a").all()
        assert len(rows) == 1
        assert '"x": 1' in rows[0].session_state

    def test_save_updates_existing_record(self, db_factory):
        _seed_registry(db_factory, "mod_a")
        state = {"x": 1}
        mod = _make_mock_module("mod_a", state)
        sm = StateManager()
        sm.save_state(mod)

        state["x"] = 99
        sm.save_state(mod)

        with db_factory() as session:
            rows = session.query(ModuleSession).filter_by(module_id="mod_a").all()
        # Still only one is_last_active record, value updated
        active_rows = [r for r in rows if r.is_last_active]
        assert len(active_rows) == 1
        assert "99" in active_rows[0].session_state

    def test_save_raises_state_save_error_on_bad_get_state(self, db_factory):

        class BadModule:
            manifest = {"id": "bad", "supports_state_restore": True}
            module_id = "bad"

            def get_state(self):
                raise RuntimeError("get_state explodes")

        sm = StateManager()
        with pytest.raises(StateSaveError):
            sm.save_state(BadModule())


class TestRestoreState:

    def test_restore_returns_false_when_no_record(self, db_factory):
        mod = _make_mock_module("mod_nothing", {}, supports=True)
        sm = StateManager()
        assert sm.restore_state(mod) is False

    def test_restore_returns_false_when_not_supported(self, db_factory):
        _seed_registry(db_factory, "mod_nosupport")
        mod = _make_mock_module("mod_nosupport", {}, supports=False)
        sm = StateManager()
        assert sm.restore_state(mod) is False

    def test_restore_applies_saved_state(self, db_factory):
        _seed_registry(db_factory, "mod_r")
        state = {}
        mod = _make_mock_module("mod_r", {"score": 42}, supports=True)
        sm = StateManager()
        sm.save_state(mod)

        restore_target = {}
        mod2 = _make_mock_module("mod_r", restore_target, supports=True)
        result = sm.restore_state(mod2)
        assert result is True
        assert restore_target.get("score") == 42

    def test_restore_raises_when_restore_state_fails(self, db_factory):
        _seed_registry(db_factory, "mod_fail")
        mod = _make_mock_module("mod_fail", {"a": 1}, supports=True)
        sm = StateManager()
        sm.save_state(mod)

        bad_mod = _make_mock_module("mod_fail", {}, supports=True, raise_on_restore=True)
        with pytest.raises(StateRestoreError):
            sm.restore_state(bad_mod)


class TestClearAllSessions:

    def test_clear_removes_all_session_records(self, db_factory):
        _seed_registry(db_factory, "mod_c1")
        _seed_registry(db_factory, "mod_c2")
        mod1 = _make_mock_module("mod_c1", {"val": 1})
        mod2 = _make_mock_module("mod_c2", {"val": 2})
        sm = StateManager()
        sm.save_state(mod1)
        sm.save_state(mod2)

        # Verify rows exist before clearing
        with db_factory() as session:
            count_before = session.query(ModuleSession).count()
        assert count_before >= 2

        clear_all_sessions()

        with db_factory() as session:
            count_after = session.query(ModuleSession).count()
        assert count_after == 0

    def test_clear_is_idempotent_on_empty_table(self, db_factory):
        """Calling clear_all_sessions on an empty table must not raise."""
        clear_all_sessions()  # should complete without error
