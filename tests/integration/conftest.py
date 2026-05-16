"""Shared in-memory DB fixture for integration tests that need DB isolation."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine, event as sa_event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from config.database import Base


@pytest.fixture
def db_factory(monkeypatch):
    """Patch SessionFactory with an isolated in-memory SQLite DB.

    Yields the in-memory sessionmaker.  Tables are created fresh for each
    test and torn down at the end.
    """
    import core.storage.models  # noqa: F401 — register all models with Base

    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @sa_event.listens_for(engine, "connect")
    def _fk_on(dbapi_conn, _record):
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    Base.metadata.create_all(bind=engine)
    Factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    import core.storage.session as _sess_mod
    monkeypatch.setattr(_sess_mod, "SessionFactory", Factory)

    yield Factory

    Base.metadata.drop_all(bind=engine)
    engine.dispose()
