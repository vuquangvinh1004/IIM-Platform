"""In-memory module registry for IIMP.

The registry tracks all discovered modules, their current lifecycle
state, and their loaded instances. It also synchronises state changes
to the persistent DB via the module_service.

Design constraints:
- Single source of truth for runtime module state.
- Never instantiates modules directly — delegates to loader.
- Thread-considerate but not thread-safe (all mutations on Qt main thread).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from core.module_runtime.base_module import BaseModule
from core.utils.constants import ModuleState
from core.utils.logger import get_logger

if TYPE_CHECKING:
    from core.module_runtime.manifest_schema import ModuleManifest

_log = get_logger("iimp.registry")


@dataclass
class ModuleRecord:
    """Represents one module entry in the runtime registry."""

    manifest: "ModuleManifest"
    module_dir: Path
    state: ModuleState = ModuleState.DISCOVERED
    instance: BaseModule | None = None
    error: str | None = None


class ModuleRegistry:
    """In-memory registry for all discovered and loaded modules."""

    def __init__(self) -> None:
        self._records: dict[str, ModuleRecord] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register(self, manifest: "ModuleManifest", module_dir: Path) -> None:
        """Add a discovered module to the registry."""
        if manifest.id in self._records:
            _log.warning(f"Module '{manifest.id}' already registered. Skipping.")
            return
        self._records[manifest.id] = ModuleRecord(manifest=manifest, module_dir=module_dir)
        _log.debug(f"Registered module: {manifest.id}")

    def set_instance(self, module_id: str, instance: BaseModule) -> None:
        record = self._get(module_id)
        record.instance = instance
        record.state = ModuleState.LOADED

    def set_state(self, module_id: str, state: ModuleState, error: str | None = None) -> None:
        record = self._get(module_id)
        record.state = state
        record.error = error
        _log.debug(f"Module '{module_id}' state → {state.value}")

    # ── Queries ───────────────────────────────────────────────────────────────

    def get_record(self, module_id: str) -> ModuleRecord | None:
        return self._records.get(module_id)

    def all_records(self) -> list[ModuleRecord]:
        return list(self._records.values())

    def loaded_modules(self) -> list[ModuleRecord]:
        return [r for r in self._records.values() if r.instance is not None]

    def active_modules(self) -> list[ModuleRecord]:
        """Return all modules currently in ACTIVATED state."""
        return [r for r in self._records.values() if r.state == ModuleState.ACTIVATED]

    def is_registered(self, module_id: str) -> bool:
        return module_id in self._records

    def unregister(self, module_id: str) -> None:
        """Remove a module from the in-memory registry (used during uninstall)."""
        if module_id in self._records:
            del self._records[module_id]
            _log.debug(f"Unregistered module: {module_id}")
        else:
            _log.warning(f"unregister: '{module_id}' not found in registry.")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _get(self, module_id: str) -> ModuleRecord:
        record = self._records.get(module_id)
        if record is None:
            raise KeyError(f"Module '{module_id}' not found in registry")
        return record

    def __len__(self) -> int:
        return len(self._records)
