"""UI smoke test fixtures.

Provides:
- ``in_memory_db`` — patched SessionFactory pointing to a fresh in-memory SQLite DB
                    so views that call get_session() don't touch disk data.
"""
from __future__ import annotations

try:
    from PySide6.QtWidgets import QApplication
    _QT_AVAILABLE = True
except ImportError:
    _QT_AVAILABLE = False

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture(scope="module")
def in_memory_db(monkeypatch_module=None):
    """Return a sessionmaker bound to an isolated in-memory SQLite DB.

    This fixture is intentionally *not* autouse — views that call
    get_session() in their constructors need it to be applied first via
    the ``patched_db`` fixture.
    """
    import core.storage.models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sa_event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    from config.database import Base
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture()
def patched_db(monkeypatch, tmp_path):
    """Patch core.storage.session.SessionFactory with an isolated in-memory DB.

    Import and use this fixture wherever the view under test calls get_session()
    (e.g. DashboardView, SettingsView).
    """
    import core.storage.models  # noqa: F401

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sa_event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _rec):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    from config.database import Base
    Base.metadata.create_all(bind=engine)
    Factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    import core.storage.session as sess_mod
    monkeypatch.setattr(sess_mod, "SessionFactory", Factory)
    return Factory
