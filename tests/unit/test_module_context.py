"""Unit tests for ModuleContext and PlatformInfo dataclasses."""
from __future__ import annotations

from core.module_runtime.module_context import ModuleContext, PlatformInfo


class TestPlatformInfo:

    def test_fields(self):
        info = PlatformInfo(platform_version="1.0.0", sdk_version="1.0.0", os_name="Windows")
        assert info.platform_version == "1.0.0"
        assert info.sdk_version == "1.0.0"
        assert info.os_name == "Windows"
        assert info.debug is False

    def test_debug_flag(self):
        info = PlatformInfo(platform_version="1.0.0", sdk_version="1.0.0", os_name="Linux", debug=True)
        assert info.debug is True


class TestModuleContext:

    def _make_context(self, module_id: str = "mod") -> ModuleContext:
        info = PlatformInfo(platform_version="1.0.0", sdk_version="1.0.0", os_name="Windows")
        return ModuleContext(
            module_id=module_id,
            logger=None,
            event_bus=None,
            storage_service=None,
            settings_service=None,
            export_service=None,
            activity_service=None,
            dialog_service=None,
            theme_service=None,
            path_service=None,
            platform_info=info,
        )

    def test_module_id_set(self):
        ctx = self._make_context("test_module")
        assert ctx.module_id == "test_module"

    def test_workspace_service_defaults_none(self):
        ctx = self._make_context()
        assert ctx.workspace_service is None

    def test_platform_info_accessible(self):
        ctx = self._make_context()
        assert ctx.platform_info.platform_version == "1.0.0"
