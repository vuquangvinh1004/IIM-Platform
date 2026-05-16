"""Settings service — unified read/write for app and module settings.

Module settings are keyed by (module_id, setting_key) and stored in the
``module_settings`` DB table. App settings use the ``app_settings`` table.
All values are persisted as text; callers are responsible for (de-)serialisation.
"""
from __future__ import annotations

from core.storage.models import AppSettings, ModuleSettings
from core.storage.session import get_session
from core.utils.helpers import safe_json_dumps, safe_json_loads
from core.utils.logger import get_logger

_log = get_logger("iimp.services.settings")


class SettingsService:
    """Read and write settings for the app and for individual modules."""

    # ── App settings ──────────────────────────────────────────────────────────

    def get_app_setting(self, key: str, default: object = None) -> object:
        with get_session() as session:
            row = session.query(AppSettings).filter_by(setting_key=key).first()
            if row is None or row.setting_value is None:
                return default
            return safe_json_loads(row.setting_value, fallback=row.setting_value)

    def set_app_setting(self, key: str, value: object) -> None:
        serialized = safe_json_dumps(value) if not isinstance(value, str) else value
        with get_session() as session:
            row = session.query(AppSettings).filter_by(setting_key=key).first()
            if row:
                row.setting_value = serialized
            else:
                session.add(AppSettings(setting_key=key, setting_value=serialized))
        _log.debug(f"App setting '{key}' updated.")

    # ── Module settings ───────────────────────────────────────────────────────

    def get_module_setting(
        self, module_id: str, key: str, default: object = None
    ) -> object:
        with get_session() as session:
            row = (
                session.query(ModuleSettings)
                .filter_by(module_id=module_id, setting_key=key)
                .first()
            )
            if row is None or row.setting_value is None:
                return default
            return safe_json_loads(row.setting_value, fallback=row.setting_value)

    def set_module_setting(self, module_id: str, key: str, value: object) -> None:
        serialized = safe_json_dumps(value) if not isinstance(value, str) else value
        with get_session() as session:
            row = (
                session.query(ModuleSettings)
                .filter_by(module_id=module_id, setting_key=key)
                .first()
            )
            if row:
                row.setting_value = serialized
            else:
                session.add(
                    ModuleSettings(
                        module_id=module_id,
                        setting_key=key,
                        setting_value=serialized,
                    )
                )
        _log.debug(f"Module '{module_id}' setting '{key}' updated.")

    def get_all_module_settings(self, module_id: str) -> dict[str, object]:
        with get_session() as session:
            rows = session.query(ModuleSettings).filter_by(module_id=module_id).all()
            return {
                r.setting_key: safe_json_loads(r.setting_value, fallback=r.setting_value)
                for r in rows
            }
