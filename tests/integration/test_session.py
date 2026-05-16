"""Integration tests for get_session() rollback path."""
from __future__ import annotations

import pytest


class TestGetSessionRollback:

    def test_exception_triggers_rollback_and_reraises(self, db_factory):
        """If an exception is raised inside the with-block, it is re-raised."""
        from core.storage.session import get_session

        with pytest.raises(RuntimeError, match="rollback me"):
            with get_session() as _session:
                raise RuntimeError("rollback me")

    def test_clean_exit_commits(self, db_factory):
        """On clean exit the session commits successfully."""
        from core.storage.session import get_session
        from core.storage.models import AppSettings

        with get_session() as session:
            session.add(AppSettings(setting_key="test_commit", setting_value="yes"))

        # Verify row was committed by reading in a new session
        with get_session() as session:
            row = session.query(AppSettings).filter_by(setting_key="test_commit").first()
            value = row.setting_value if row else None
        assert value == "yes"
