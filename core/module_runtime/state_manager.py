"""Module state manager — handles save and restore of module session state.

The state manager coordinates between the module's ``get_state()`` /
``restore_state()`` contract and the persistent ``module_sessions`` DB table.

State versioning
----------------
When saving, the manager injects ``_state_version`` from the module's
``data_contract_version`` manifest field.  When restoring, it compares
the saved version against the current manifest.  On mismatch it calls
``module.migrate_state()`` to let the module transform old data, or
falls back to default state if migration is not overridden.
"""
from __future__ import annotations

import json

from core.module_runtime.base_module import BaseModule
from core.storage.models import ModuleSession
from core.storage.session import get_session
from core.utils.exceptions import StateRestoreError, StateSaveError
from core.utils.logger import get_logger

_log = get_logger("iimp.state_manager")


def _data_contract(module: BaseModule) -> str | None:
    """Read ``data_contract_version`` from the module manifest, if present."""
    return module.manifest.get("data_contract_version")


class StateManager:
    """Persists and restores module session state via the DB."""

    def save_state(self, module: BaseModule) -> None:
        """Serialize module state and upsert into module_sessions."""
        try:
            state_dict = module.get_state()
            # Inject state version so future restores can detect mismatches
            dcv = _data_contract(module)
            if dcv is not None:
                state_dict.setdefault("_state_version", dcv)
            state_json = json.dumps(state_dict, ensure_ascii=False)
        except Exception as exc:
            raise StateSaveError(f"get_state() failed for '{module.module_id}': {exc}") from exc

        try:
            with get_session() as session:
                record = (
                    session.query(ModuleSession)
                    .filter_by(module_id=module.module_id, is_last_active=True)
                    .first()
                )
                if record:
                    record.session_state = state_json
                else:
                    session.add(
                        ModuleSession(
                            module_id=module.module_id,
                            session_name="last",
                            session_state=state_json,
                            is_last_active=True,
                        )
                    )
            _log.debug(f"State saved for '{module.module_id}'.")
        except Exception as exc:
            raise StateSaveError(f"DB write failed for '{module.module_id}': {exc}") from exc

    def restore_state(self, module: BaseModule) -> bool:
        """Load persisted state from DB and call restore_state() on module.

        Returns True if state was found and applied, False if no state exists.
        Raises StateRestoreError only on hard failures.
        """
        if not module.manifest.get("supports_state_restore", False):
            return False

        try:
            with get_session() as session:
                record = (
                    session.query(ModuleSession)
                    .filter_by(module_id=module.module_id, is_last_active=True)
                    .first()
                )
                if not record or not record.session_state:
                    return False
                state_dict = json.loads(record.session_state)
        except Exception as exc:
            _log.error(f"DB read failed when restoring state for '{module.module_id}': {exc}")
            return False

        # ── Version check & migration ─────────────────────────────────────
        saved_version = state_dict.pop("_state_version", None)
        current_version = _data_contract(module)

        if saved_version and current_version and saved_version != current_version:
            _log.info(
                "State version mismatch for '%s': saved=%s, current=%s. "
                "Attempting migration.",
                module.module_id,
                saved_version,
                current_version,
            )
            try:
                state_dict = module.migrate_state(state_dict, saved_version)
            except Exception as exc:
                _log.warning(
                    "migrate_state() failed for '%s': %s. "
                    "Discarding old state, using defaults.",
                    module.module_id,
                    exc,
                )
                return False

        try:
            module.restore_state(state_dict)
            _log.debug(f"State restored for '{module.module_id}'.")
            return True
        except Exception as exc:
            _log.warning(
                f"restore_state() raised for '{module.module_id}': {exc}. "
                "Falling back to default state."
            )
            raise StateRestoreError(
                f"restore_state() failed for '{module.module_id}': {exc}"
            ) from exc


def clear_all_sessions() -> None:
    """Delete all rows from module_sessions.

    Called once at application startup so every session begins with a
    clean slate.  State is still saved / restored *within* a running
    session (on module deactivate / activate), but it is never carried
    over to the next application launch.
    """
    try:
        with get_session() as session:
            deleted = session.query(ModuleSession).delete()
        _log.debug(f"Cleared {deleted} module session record(s) from previous run.")
    except Exception as exc:
        # Non-fatal: a stale session record is worse than a startup warning.
        _log.warning(f"Could not clear module sessions on startup: {exc}")
