"""Activity service — writes structured events to the activity_logs table.

Modules call ``context.activity_service.log(...)`` to record significant
actions. The shell also uses this directly for lifecycle events.
"""
from __future__ import annotations

from core.storage.models import ActivityLog
from core.storage.session import get_session
from core.utils.constants import ActivityType
from core.utils.helpers import safe_json_dumps
from core.utils.logger import get_logger

_log = get_logger("iimp.services.activity")


class ActivityService:
    """Write activity events to the database."""

    def log(
        self,
        activity_type: ActivityType | str,
        message: str | None = None,
        module_id: str | None = None,
        metadata: dict | None = None,
    ) -> None:
        """Persist an activity log entry."""
        type_value = activity_type.value if isinstance(activity_type, ActivityType) else activity_type
        with get_session() as session:
            session.add(
                ActivityLog(
                    module_id=module_id,
                    activity_type=type_value,
                    message=message,
                    metadata_json=safe_json_dumps(metadata) if metadata else None,
                )
            )
        _log.debug(f"Activity logged: {type_value} | {message}")

    def log_activity(
        self,
        module_id: str,
        action: str,
        *,
        metadata: dict | None = None,
    ) -> None:
        """Backward-compatible alias for older modules expecting ``log_activity``.

        Args:
            module_id: Stable module identifier producing the event.
            action: Short action verb or status label (for example: activated).
            metadata: Optional structured details stored with the event.
        """
        self.log(
            activity_type="MODULE_ACTIVITY",
            message=action,
            module_id=module_id,
            metadata=metadata,
        )
