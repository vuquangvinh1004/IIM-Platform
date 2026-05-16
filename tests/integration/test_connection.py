"""Integration tests for storage connection helpers."""
from __future__ import annotations

from sqlalchemy.engine import Engine


class TestInitDb:

    def test_init_db_is_idempotent(self):
        """Calling init_db() twice should not raise."""
        from core.storage.connection import init_db
        init_db()
        init_db()  # second call is a no-op (create_all is idempotent)

    def test_get_engine_returns_engine(self):
        from core.storage.connection import get_engine
        engine = get_engine()
        assert isinstance(engine, Engine)
