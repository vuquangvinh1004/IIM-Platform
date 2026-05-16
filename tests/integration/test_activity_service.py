"""Integration tests for ActivityService."""
from __future__ import annotations

from core.services.activity_service import ActivityService
from core.storage.models import ActivityLog
from core.utils.constants import ActivityType


class TestActivityService:

    def test_log_basic_event(self, db_factory):
        svc = ActivityService()
        svc.log(ActivityType.APP_START, "Application started")
        with db_factory() as session:
            rows = session.query(ActivityLog).all()
        assert len(rows) == 1
        assert rows[0].activity_type == "app_start"
        assert rows[0].message == "Application started"

    def test_log_with_module_id(self, db_factory):
        svc = ActivityService()
        svc.log(ActivityType.MODULE_ACTIVATED, "Loaded", module_id="stats_mod")
        with db_factory() as session:
            row = session.query(ActivityLog).first()
        assert row.module_id == "stats_mod"

    def test_log_with_metadata(self, db_factory):
        svc = ActivityService()
        svc.log(ActivityType.EXPORT_COMPLETED, metadata={"format": "png", "size": 1024})
        with db_factory() as session:
            row = session.query(ActivityLog).first()
        assert row.metadata_json is not None
        assert "png" in row.metadata_json

    def test_log_multiple_events(self, db_factory):
        svc = ActivityService()
        svc.log(ActivityType.APP_START)
        svc.log(ActivityType.MODULE_ACTIVATED, module_id="mod_a")
        svc.log(ActivityType.APP_SHUTDOWN)
        with db_factory() as session:
            count = session.query(ActivityLog).count()
        assert count == 3

    def test_log_string_type(self, db_factory):
        """ActivityType can also be passed as a raw string."""
        svc = ActivityService()
        svc.log("custom_event", "Custom message")
        with db_factory() as session:
            row = session.query(ActivityLog).first()
        assert row.activity_type == "custom_event"
