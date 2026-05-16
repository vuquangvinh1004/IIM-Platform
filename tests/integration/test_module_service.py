"""Integration tests for ModuleService — orchestration layer.

Uses the headless_test_module (no PySide6 dependency).
All DB operations go through the in-memory db_factory fixture.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from core.module_runtime.event_bus import EventBus
from core.module_runtime.registry import ModuleRegistry
from core.services.activity_service import ActivityService
from core.services.app_services import AppServices
from core.services.export_service import ExportService
from core.services.module_service import ModuleService
from core.services.path_service import PathService
from core.services.settings_service import SettingsService
from core.utils.constants import ModuleState
from core.utils.exceptions import ModuleCompatibilityError

# Headless module directory — no PySide6 dependency
_HEADLESS_DIR = Path(__file__).parent.parent.parent / "modules" / "templates" / "headless_test_module"


def _make_service(db_factory, *, platform_version: str = "1.0.0", tmp_path: Path | None = None) -> ModuleService:
    """Build a fully wired ModuleService backed by the in-memory test DB."""
    services = AppServices(
        event_bus=EventBus(),
        settings=SettingsService(),
        activity=ActivityService(),
        paths=PathService(),
        export=ExportService(tmp_path or Path("/tmp")),
        dialogs=None,  # type: ignore[arg-type]
        theme=None,    # type: ignore[arg-type]
    )
    return ModuleService(
        registry=ModuleRegistry(),
        services=services,
        platform_version=platform_version,
    )


# ── Constructor ─────────────────────────────────────────────────────────────

class TestModuleServiceInit:

    def test_init_stores_platform_version(self, db_factory):
        svc = _make_service(db_factory, platform_version="2.5.0")
        assert svc._platform_version == "2.5.0"

    def test_init_creates_state_manager(self, db_factory):
        from core.module_runtime.state_manager import StateManager
        svc = _make_service(db_factory)
        assert isinstance(svc._state_manager, StateManager)


# ── Discover ────────────────────────────────────────────────────────────────

class TestDiscover:

    def test_discover_headless_module(self, db_factory, tmp_path):
        """discover() picks up headless_test_module and syncs to DB."""
        import shutil
        # Copy headless module to tmp_path so we have an isolated scan dir
        dest = tmp_path / "headless_test_module"
        shutil.copytree(str(_HEADLESS_DIR), str(dest))

        svc = _make_service(db_factory)
        found, failed = svc.discover(tmp_path)
        assert found == 1
        assert failed == 0

    def test_discover_non_existent_dir_returns_zero(self, db_factory, tmp_path):
        missing = tmp_path / "no_such_dir"
        svc = _make_service(db_factory)
        found, failed = svc.discover(missing)
        assert found == 0
        assert failed == 0

    def test_discover_syncs_to_db(self, db_factory, tmp_path):
        """After discover(), the module_registry DB table has a row."""
        import shutil
        from core.storage.models import ModuleRegistry as DBReg
        from core.storage.session import get_session

        dest = tmp_path / "headless_test_module"
        shutil.copytree(str(_HEADLESS_DIR), str(dest))

        svc = _make_service(db_factory)
        svc.discover(tmp_path)

        with get_session() as session:
            row = session.query(DBReg).filter_by(module_id="headless_test_module").first()
            row_version = row.version if row else None
        assert row_version == "1.0.0"


# ── Load module ─────────────────────────────────────────────────────────────

class TestLoadModule:

    def _discovered_service(self, db_factory, tmp_path) -> ModuleService:
        import shutil
        dest = tmp_path / "headless_test_module"
        shutil.copytree(str(_HEADLESS_DIR), str(dest))
        svc = _make_service(db_factory)
        svc.discover(tmp_path)
        return svc

    def test_load_unknown_returns_none(self, db_factory):
        svc = _make_service(db_factory)
        result = svc.load_module("no_such_module")
        assert result is None

    def test_load_success(self, db_factory, tmp_path):
        svc = self._discovered_service(db_factory, tmp_path)
        instance = svc.load_module("headless_test_module")
        assert instance is not None
        assert instance.module_id == "headless_test_module"

    def test_load_sets_loaded_state(self, db_factory, tmp_path):
        svc = self._discovered_service(db_factory, tmp_path)
        svc.load_module("headless_test_module")
        record = svc._registry.get_record("headless_test_module")
        assert record.state == ModuleState.LOADED

    def test_load_already_loaded_returns_existing(self, db_factory, tmp_path):
        svc = self._discovered_service(db_factory, tmp_path)
        first = svc.load_module("headless_test_module")
        second = svc.load_module("headless_test_module")
        assert first is second

    def test_load_incompatible_raises(self, db_factory, tmp_path):
        """Module requiring platform version higher than provided raises ModuleCompatibilityError."""
        import shutil
        import json
        dest = tmp_path / "headless_test_module"
        shutil.copytree(str(_HEADLESS_DIR), str(dest))
        # Override manifest to require a much higher platform version
        manifest_path = dest / "module.json"
        data = json.loads(manifest_path.read_text())
        data["min_platform_version"] = "99.0.0"
        manifest_path.write_text(json.dumps(data))

        svc = _make_service(db_factory, platform_version="1.0.0")
        svc.discover(tmp_path)
        with pytest.raises(ModuleCompatibilityError):
            svc.load_module("headless_test_module")

    def test_load_incompatible_sets_incompatible_state(self, db_factory, tmp_path):
        import shutil, json
        dest = tmp_path / "headless_test_module"
        shutil.copytree(str(_HEADLESS_DIR), str(dest))
        data = json.loads((dest / "module.json").read_text())
        data["min_platform_version"] = "99.0.0"
        (dest / "module.json").write_text(json.dumps(data))

        svc = _make_service(db_factory, platform_version="1.0.0")
        svc.discover(tmp_path)
        with pytest.raises(ModuleCompatibilityError):
            svc.load_module("headless_test_module")
        record = svc._registry.get_record("headless_test_module")
        assert record.state == ModuleState.INCOMPATIBLE


# ── Activate / Deactivate / Unload ──────────────────────────────────────────

class TestModuleLifecycle:

    def _loaded_service(self, db_factory, tmp_path) -> ModuleService:
        import shutil
        dest = tmp_path / "headless_test_module"
        shutil.copytree(str(_HEADLESS_DIR), str(dest))
        svc = _make_service(db_factory)
        svc.discover(tmp_path)
        svc.load_module("headless_test_module")
        return svc

    def test_activate_sets_activated_state(self, db_factory, tmp_path):
        svc = self._loaded_service(db_factory, tmp_path)
        svc.activate("headless_test_module")
        record = svc._registry.get_record("headless_test_module")
        assert record.state == ModuleState.ACTIVATED

    def test_activate_unknown_module_is_noop(self, db_factory):
        svc = _make_service(db_factory)
        svc.activate("ghost")  # should not raise

    def test_deactivate_sets_deactivated_state(self, db_factory, tmp_path):
        svc = self._loaded_service(db_factory, tmp_path)
        svc.activate("headless_test_module")
        svc.deactivate("headless_test_module")
        record = svc._registry.get_record("headless_test_module")
        assert record.state == ModuleState.DEACTIVATED

    def test_unload_clears_instance(self, db_factory, tmp_path):
        svc = self._loaded_service(db_factory, tmp_path)
        svc.unload_module("headless_test_module")
        record = svc._registry.get_record("headless_test_module")
        assert record.instance is None
        assert record.state == ModuleState.UNLOADED

    def test_unload_unknown_is_noop(self, db_factory):
        svc = _make_service(db_factory)
        svc.unload_module("ghost")  # should not raise


# ── Enable / Disable / Uninstall ────────────────────────────────────────────

class TestEnableDisableUninstall:

    def _discovered_service(self, db_factory, tmp_path) -> ModuleService:
        import shutil
        dest = tmp_path / "headless_test_module"
        shutil.copytree(str(_HEADLESS_DIR), str(dest))
        svc = _make_service(db_factory)
        svc.discover(tmp_path)
        return svc

    def test_enable_unknown_module_returns_false(self, db_factory):
        svc = _make_service(db_factory)
        assert svc.enable_module("ghost") is False

    def test_enable_known_module_returns_true(self, db_factory, tmp_path):
        svc = self._discovered_service(db_factory, tmp_path)
        result = svc.enable_module("headless_test_module")
        assert result is True

    def test_disable_unknown_module_returns_false(self, db_factory):
        svc = _make_service(db_factory)
        assert svc.disable_module("ghost") is False

    def test_disable_known_module_returns_true(self, db_factory, tmp_path):
        svc = self._discovered_service(db_factory, tmp_path)
        result = svc.disable_module("headless_test_module")
        assert result is True

    def test_uninstall_removes_from_registry(self, db_factory, tmp_path):
        svc = self._discovered_service(db_factory, tmp_path)
        svc.uninstall_module("headless_test_module")
        assert svc._registry.get_record("headless_test_module") is None

    def test_uninstall_unloads_active_instance(self, db_factory, tmp_path):
        """Uninstall while loaded — should unload first then remove."""
        import shutil
        dest = tmp_path / "headless_test_module"
        shutil.copytree(str(_HEADLESS_DIR), str(dest))
        svc = _make_service(db_factory)
        svc.discover(tmp_path)
        svc.load_module("headless_test_module")
        svc.uninstall_module("headless_test_module")
        assert svc._registry.get_record("headless_test_module") is None


# ── Install local module ─────────────────────────────────────────────────────

class TestInstallLocalModule:

    def test_install_headless_module(self, db_factory, tmp_path, monkeypatch):
        """install_local_module registers and returns the module id."""
        from config import paths
        # Point MODULES_DIR to a temp dir so copytree goes somewhere writable
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        monkeypatch.setattr(paths, "MODULES_DIR", modules_dir)

        svc = _make_service(db_factory)
        result = svc.install_local_module(_HEADLESS_DIR)
        assert result == "headless_test_module"

    def test_install_already_registered_returns_none(self, db_factory, tmp_path, monkeypatch):
        from config import paths
        modules_dir = tmp_path / "modules"
        modules_dir.mkdir()
        monkeypatch.setattr(paths, "MODULES_DIR", modules_dir)

        svc = _make_service(db_factory)
        svc.install_local_module(_HEADLESS_DIR)          # first install
        result = svc.install_local_module(_HEADLESS_DIR)  # duplicate
        assert result is None

    def test_install_bad_manifest_returns_none(self, db_factory, tmp_path):
        """A directory without a valid manifest returns None."""
        svc = _make_service(db_factory)
        result = svc.install_local_module(tmp_path)  # tmp_path has no module.json
        assert result is None
