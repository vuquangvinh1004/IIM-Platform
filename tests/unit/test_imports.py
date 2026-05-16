"""Unit tests for core.utils.imports — safe_import() and check_dependencies()."""
from __future__ import annotations

from core.utils.imports import check_dependencies, safe_import


class TestSafeImport:

    def test_import_existing_module(self):
        mod, ok = safe_import("json")
        assert ok is True
        assert mod is not None
        assert hasattr(mod, "dumps")

    def test_import_nonexistent_module(self):
        mod, ok = safe_import("nonexistent_pkg_abc_xyz_12345")
        assert ok is False
        assert mod is None

    def test_import_submodule(self):
        mod, ok = safe_import("os.path")
        assert ok is True
        assert mod is not None


class TestCheckDependencies:

    def test_empty_list_returns_empty(self):
        assert check_dependencies([]) == []

    def test_all_present(self):
        assert check_dependencies(["json", "os", "sys"]) == []

    def test_all_missing(self):
        missing = check_dependencies(["no_such_pkg_aaa", "no_such_pkg_bbb"])
        assert missing == ["no_such_pkg_aaa", "no_such_pkg_bbb"]

    def test_mixed(self):
        missing = check_dependencies(["json", "no_such_pkg_ccc", "os"])
        assert missing == ["no_such_pkg_ccc"]

    def test_preserves_order(self):
        deps = ["zzz_missing", "json", "aaa_missing"]
        missing = check_dependencies(deps)
        assert missing == ["zzz_missing", "aaa_missing"]
