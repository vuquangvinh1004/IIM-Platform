"""Path service — supplies standardised paths to modules.

Modules must only write to paths they receive from this service.
They must never construct absolute or relative paths arbitrarily.
"""
from __future__ import annotations

from pathlib import Path

from config.paths import EXPORTS_DIR, MODULE_DATA_DIR, TEMP_DIR


class PathService:
    """Provides module-scoped data and export paths."""

    def module_data_path(self, module_id: str) -> Path:
        """Return (and create) the persistent data dir for *module_id*."""
        p = MODULE_DATA_DIR / module_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def module_temp_path(self, module_id: str) -> Path:
        """Return (and create) the temp dir for *module_id*."""
        p = TEMP_DIR / module_id
        p.mkdir(parents=True, exist_ok=True)
        return p

    def exports_path(self) -> Path:
        """Return the global exports directory."""
        EXPORTS_DIR.mkdir(parents=True, exist_ok=True)
        return EXPORTS_DIR
