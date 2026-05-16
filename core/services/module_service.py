"""Module service — manages the full module lifecycle from the service layer.

The shell calls methods here rather than touching the registry or loader
directly. This service coordinates discovery, loading, activation/deactivation,
state management, and DB synchronisation.
"""
from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Callable

from config.settings import PLATFORM_VERSION
from core.module_runtime.base_module import BaseModule
from core.module_runtime.discovery import discover_modules
from core.module_runtime.loader import instantiate_module
from core.module_runtime.module_context import ModuleContext, PlatformInfo
from core.module_runtime.registry import ModuleRecord, ModuleRegistry
from core.module_runtime.sandbox_policy import check_compatibility
from core.module_runtime.state_manager import StateManager
from core.services.app_services import AppServices
from core.storage.models import ModuleRegistry as DBModuleRegistry
from core.storage.session import get_session
from core.utils.constants import ActivityType, ModuleState
from core.utils.exceptions import ModuleCompatibilityError, ModuleLoadError
from core.utils.helpers import safe_json_dumps
from core.utils.logger import get_logger

_log = get_logger("iimp.services.module")


class ModuleService:
    """Orchestrates module lifecycle: discovery → load → activate → unload."""

    def __init__(
        self,
        registry: ModuleRegistry,
        services: AppServices,
        platform_version: str = PLATFORM_VERSION,
    ) -> None:
        self._registry = registry
        self._services = services
        self._state_manager = StateManager()
        self._platform_version = platform_version

    # ── Discovery ─────────────────────────────────────────────────────────────

    def discover(
        self,
        modules_dir: Path | None = None,
        *,
        on_progress: "Callable[[int, int, str], None] | None" = None,
    ) -> tuple[int, int]:
        """Scan for modules and register valid ones. Returns (found, failed).

        Args:
            modules_dir: Override for the default modules directory.
            on_progress: Optional callback ``(current, total, module_name)``
                forwarded to discovery for splash-screen progress reporting.
        """
        found, failed = discover_modules(self._registry, modules_dir, on_progress=on_progress)
        self._sync_registry_to_db()
        return found, failed

    # ── Loading ───────────────────────────────────────────────────────────────

    def load_module(self, module_id: str) -> BaseModule | None:
        """Load and instantiate the module identified by *module_id*.

        Returns the instance on success, or None if load fails (sets ERROR state).
        """
        record = self._registry.get_record(module_id)
        if record is None:
            _log.error(f"Cannot load unknown module: {module_id}")
            return None
        if record.instance is not None:
            return record.instance  # already loaded

        # Compatibility check
        issues = check_compatibility(record.manifest, self._platform_version)
        if issues:
            msg = "; ".join(issues)
            _log.warning(f"Module '{module_id}' compatibility issues: {msg}")
            self._registry.set_state(module_id, ModuleState.INCOMPATIBLE, error=msg)
            raise ModuleCompatibilityError(module_id, record.manifest.min_platform_version, self._platform_version)

        context = self._build_context(module_id)
        try:
            instance = instantiate_module(record.module_dir, context)
            self._registry.set_instance(module_id, instance)
            self._registry.set_state(module_id, ModuleState.LOADED)
            self._services.activity.log(ActivityType.MODULE_LOADED, f"Loaded {module_id}", module_id=module_id)
            return instance
        except ModuleLoadError as exc:
            _log.error(f"Load failed for '{module_id}': {exc}")
            self._registry.set_state(module_id, ModuleState.ERROR, error=str(exc))
            self._services.activity.log(ActivityType.MODULE_LOAD_ERROR, str(exc), module_id=module_id)
            return None

    # ── Activation ────────────────────────────────────────────────────────────

    def activate(self, module_id: str) -> bool:
        """Deactivate any currently active module, then activate *module_id*.

        Returns True on success, False if on_activate() raises. On failure the
        module state is set to ERROR so callers can inspect the registry.
        """
        # Deactivate any other active module first — single-active policy
        for rec in self._registry.active_modules():
            if rec.manifest.id != module_id:
                self.deactivate(rec.manifest.id)

        record = self._get_loaded(module_id)
        if record is None:
            return False
        assert record.instance is not None
        try:
            record.instance.on_activate()
            self._registry.set_state(module_id, ModuleState.ACTIVATED)
            self._state_manager.restore_state(record.instance)
            self._services.activity.log(ActivityType.MODULE_ACTIVATED, module_id=module_id)
            return True
        except Exception as exc:
            _log.exception(f"on_activate() failed for '{module_id}': {exc}")
            self._registry.set_state(module_id, ModuleState.ERROR, error=str(exc))
            return False

    def deactivate(self, module_id: str) -> bool:
        """Save state and deactivate *module_id*.

        Returns True on success, False if an error occurs during deactivation.
        State is always saved before calling on_deactivate() to avoid data loss.
        """
        record = self._get_loaded(module_id)
        if record is None:
            return False
        assert record.instance is not None
        try:
            self._state_manager.save_state(record.instance)
            record.instance.on_deactivate()
            self._registry.set_state(module_id, ModuleState.DEACTIVATED)
            self._services.activity.log(ActivityType.MODULE_DEACTIVATED, module_id=module_id)
            return True
        except Exception as exc:
            _log.exception(f"on_deactivate() failed for '{module_id}': {exc}")
            self._registry.set_state(module_id, ModuleState.ERROR, error=str(exc))
            return False

    def unload_module(self, module_id: str) -> None:
        record = self._get_loaded(module_id)
        if record is None:
            return
        assert record.instance is not None
        try:
            record.instance.on_unload()
        except Exception as exc:
            _log.exception(f"on_unload() raised for '{module_id}': {exc}")
        self._registry.set_state(module_id, ModuleState.UNLOADED)
        record.instance = None  # type: ignore[assignment]
        _log.info(f"Module unloaded: {module_id}")

    # ── Enable / Disable / Uninstall ──────────────────────────────────────────

    def enable_module(self, module_id: str) -> bool:
        """Mark module as enabled in DB and reflect in registry. Returns True on success."""
        return self._persist_enabled_flag(module_id, enabled=True)

    def disable_module(self, module_id: str) -> bool:
        """Unload if active, mark disabled in DB and reflect in registry. Returns True on success."""
        record = self._registry.get_record(module_id)
        if record and record.instance is not None:
            self.unload_module(module_id)
        return self._persist_enabled_flag(module_id, enabled=False)

    def uninstall_module(self, module_id: str) -> bool:
        """Unload, remove from DB registry (cascades settings/sessions). Returns True on success."""
        record = self._registry.get_record(module_id)
        if record and record.instance is not None:
            self.unload_module(module_id)
        with get_session() as session:
            row = session.query(DBModuleRegistry).filter_by(module_id=module_id).first()
            if row:
                session.delete(row)
        # Remove from in-memory registry
        self._registry.unregister(module_id)
        self._services.activity.log(
            ActivityType.MODULE_UNINSTALLED,
            f"Module '{module_id}' uninstalled.",
            module_id=module_id,
        )
        _log.info(f"Module '{module_id}' uninstalled.")
        return True

    def install_local_module(self, source_dir: "Path") -> str | None:
        """Register a module from a local directory.

        Validates the manifest, registers in DB, and adds to runtime registry.
        Returns the module id on success, or None on failure.
        """
        from shutil import copytree
        from config.paths import MODULES_DIR

        # Try to load and validate manifest first
        manifest = None
        try:
            from core.module_runtime.loader import load_manifest
            manifest = load_manifest(source_dir)
        except Exception as exc:
            _log.error(f"install_local_module: manifest load failed: {exc}")
            return None

        if self._registry.is_registered(manifest.id):
            _log.warning(f"install_local_module: '{manifest.id}' already registered.")
            return None

        # Copy to modules dir if source is outside
        dest_dir = MODULES_DIR / source_dir.name
        if source_dir.resolve() != dest_dir.resolve() and not dest_dir.exists():
            try:
                copytree(str(source_dir), str(dest_dir))
                _log.info(f"Copied module to {dest_dir}")
            except Exception as exc:
                _log.warning(f"Could not copy module directory: {exc}. Using source in-place.")
                dest_dir = source_dir

        # Register in runtime registry
        self._registry.register(manifest, dest_dir)
        self._sync_registry_to_db()
        self._services.activity.log(
            ActivityType.MODULE_INSTALLED,
            f"Installed '{manifest.name}' v{manifest.version}",
            module_id=manifest.id,
        )
        _log.info(f"Module '{manifest.id}' installed from {source_dir}.")
        return manifest.id

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _persist_enabled_flag(self, module_id: str, *, enabled: bool) -> bool:
        """Update DB *and* in-memory registry in one operation.

        This is the single place where the enabled/disabled state is written,
        preventing the two representations from drifting apart. Returns True
        on success, False if the module is not found in the DB.
        """
        activity_type = ActivityType.MODULE_ENABLED if enabled else ActivityType.MODULE_DISABLED
        new_state = ModuleState.DISCOVERED if enabled else ModuleState.DISABLED
        label = "enabled" if enabled else "disabled"

        with get_session() as session:
            row = session.query(DBModuleRegistry).filter_by(module_id=module_id).first()
            if row is None:
                _log.warning(f"_persist_enabled_flag: '{module_id}' not found in DB.")
                return False
            row.is_enabled = enabled
        # In-memory update only after DB commit succeeds
        self._registry.set_state(module_id, new_state)
        self._services.activity.log(activity_type, module_id=module_id)
        _log.info(f"Module '{module_id}' {label}.")
        return True

    def _build_context(self, module_id: str) -> ModuleContext:
        from core.utils.logger import get_logger as _gl
        return ModuleContext(
            module_id=module_id,
            logger=_gl(f"module.{module_id}"),
            event_bus=self._services.event_bus,
            storage_service=None,   # placeholder — Phase 5
            settings_service=self._services.settings,
            export_service=self._services.export,
            activity_service=self._services.activity,
            dialog_service=self._services.dialogs,
            theme_service=self._services.theme,
            path_service=self._services.paths,
            platform_info=PlatformInfo(
                platform_version=self._platform_version,
                sdk_version=PLATFORM_VERSION,
                os_name="Windows",
                debug=False,
            ),
        )

    def _get_loaded(self, module_id: str) -> ModuleRecord | None:
        record = self._registry.get_record(module_id)
        if record is None or record.instance is None:
            _log.warning(f"Module '{module_id}' is not loaded.")
            return None
        return record

    def _sync_registry_to_db(self) -> None:
        """Upsert all registered modules into the DB module_registry table.

        Optimised: loads all existing DB rows in a single query, then
        performs updates/inserts in one transaction instead of N individual
        lookups.
        """
        with get_session() as session:
            # Batch-load all existing DB rows keyed by module_id
            existing_rows: dict[str, DBModuleRegistry] = {
                row.module_id: row
                for row in session.query(DBModuleRegistry).all()
            }

            for record in self._registry.all_records():
                m = record.manifest
                existing = existing_rows.get(m.id)
                if existing:
                    existing.version = m.version
                    existing.entry_point = m.entry_point
                    existing.description = m.description
                    existing.permissions = safe_json_dumps(m.permissions)
                    existing.tags = safe_json_dumps(m.tags)
                    existing.min_platform_version = m.min_platform_version
                else:
                    session.add(
                        DBModuleRegistry(
                            module_id=m.id,
                            name=m.name,
                            category=m.category,
                            version=m.version,
                            description=m.description,
                            entry_point=m.entry_point,
                            install_path=str(record.module_dir),
                            icon_path=m.icon,
                            permissions=safe_json_dumps(m.permissions),
                            tags=safe_json_dumps(m.tags),
                            min_platform_version=m.min_platform_version,
                            is_builtin=True,
                        )
                    )
