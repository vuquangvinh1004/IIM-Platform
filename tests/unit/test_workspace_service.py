"""Unit tests for WorkspaceService — workspace_items CRUD."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config.database import Base


# ── In-memory DB fixture ──────────────────────────────────────────────────────

@pytest.fixture(autouse=False)
def in_memory_db(monkeypatch):
    """Patch SessionFactory with an in-memory SQLite engine for isolation.

    WorkspaceItem has a FK to module_registry.  We insert a dummy registry
    row in setup; FK enforcement is intentionally left ON to catch schema
    issues early.
    """
    import core.storage.models  # noqa: F401 — register models with Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    # Enable FK enforcement on each connection
    from sqlalchemy import event as sa_event

    @sa_event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=engine)
    Factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    import core.storage.session as _sess_mod

    monkeypatch.setattr(_sess_mod, "SessionFactory", Factory)

    # Insert a dummy module_registry row so FK constraint is satisfied
    from core.storage.models import ModuleRegistry

    with Factory() as s:
        s.add(
            ModuleRegistry(
                module_id="mod_a",
                name="Module A",
                version="1.0.0",
                entry_point="modules.a.entry:A",
                install_path="/modules/a",
            )
        )
        s.add(
            ModuleRegistry(
                module_id="mod_b",
                name="Module B",
                version="1.0.0",
                entry_point="modules.b.entry:B",
                install_path="/modules/b",
            )
        )
        s.add(
            ModuleRegistry(
                module_id="mod_c",
                name="Module C",
                version="1.0.0",
                entry_point="modules.c.entry:C",
                install_path="/modules/c",
            )
        )
        s.commit()

    yield Factory

    Base.metadata.drop_all(bind=engine)
    engine.dispose()


# ── Tests: active module tracking (no DB) ────────────────────────────────────

class TestActiveModuleTracking:

    def test_initial_state_is_none(self):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        assert ws.active_module_id is None

    def test_set_active(self):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.set_active("mod_a")
        assert ws.active_module_id == "mod_a"

    def test_set_active_none(self):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.set_active("mod_a")
        ws.set_active(None)
        assert ws.active_module_id is None


# ── Tests: workspace_items CRUD ───────────────────────────────────────────────

class TestWorkspaceItemCRUD:

    def test_get_all_items_empty(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        assert ws.get_all_items() == []

    def test_add_item_returns_data(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        item = ws.add_item("mod_a", title="Module A")
        assert item.module_id == "mod_a"
        assert item.title == "Module A"
        assert item.pinned is False

    def test_add_item_idempotent(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        first = ws.add_item("mod_a")
        second = ws.add_item("mod_a")
        assert first.id == second.id
        assert len(ws.get_all_items()) == 1

    def test_get_all_items_sorted_by_sort_order(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.add_item("mod_a")
        ws.add_item("mod_b")
        ws.add_item("mod_c")
        items = ws.get_all_items()
        assert len(items) == 3
        assert [it.module_id for it in items] == ["mod_a", "mod_b", "mod_c"]

    def test_remove_item(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.add_item("mod_a")
        removed = ws.remove_item("mod_a")
        assert removed is True
        assert ws.get_all_items() == []

    def test_remove_nonexistent_returns_false(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        removed = ws.remove_item("does_not_exist")
        assert removed is False

    def test_set_pinned_true(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.add_item("mod_a")
        ws.set_pinned("mod_a", pinned=True)
        assert ws.is_pinned("mod_a") is True

    def test_set_pinned_creates_item_if_missing(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.set_pinned("mod_a", pinned=True)
        assert ws.is_pinned("mod_a") is True
        # Should be visible in all_items now
        items = ws.get_all_items()
        assert any(it.module_id == "mod_a" for it in items)

    def test_set_pinned_false(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.set_pinned("mod_a", pinned=True)
        ws.set_pinned("mod_a", pinned=False)
        assert ws.is_pinned("mod_a") is False

    def test_get_pinned_items(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.add_item("mod_a")
        ws.add_item("mod_b")
        ws.set_pinned("mod_a", pinned=True)
        pinned = ws.get_pinned_items()
        assert len(pinned) == 1
        assert pinned[0].module_id == "mod_a"

    def test_is_pinned_false_when_not_in_workspace(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        assert ws.is_pinned("mod_a") is False

    def test_reorder(self, in_memory_db):
        from core.services.workspace_service import WorkspaceService
        ws = WorkspaceService()
        ws.add_item("mod_a")
        ws.add_item("mod_b")
        ws.add_item("mod_c")
        ws.reorder(["mod_c", "mod_b", "mod_a"])
        items = ws.get_all_items()
        assert [it.module_id for it in items] == ["mod_c", "mod_b", "mod_a"]
