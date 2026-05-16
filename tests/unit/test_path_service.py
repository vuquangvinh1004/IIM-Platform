"""Unit tests for PathService."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.services.path_service import PathService


@pytest.fixture
def path_svc(tmp_path, monkeypatch):
    """PathService with all dirs redirected to tmp_path for isolation."""
    import config.paths as paths_mod
    monkeypatch.setattr(paths_mod, "MODULE_DATA_DIR", tmp_path / "module_data")
    monkeypatch.setattr(paths_mod, "TEMP_DIR", tmp_path / "temp")
    monkeypatch.setattr(paths_mod, "EXPORTS_DIR", tmp_path / "exports")
    return PathService()


class TestPathService:

    def test_module_data_path_creates_dir(self, path_svc, tmp_path):
        p = path_svc.module_data_path("my_module")
        assert p.exists()
        assert p.is_dir()

    def test_module_data_path_returns_module_scoped(self, path_svc, tmp_path):
        p = path_svc.module_data_path("mod_a")
        assert p.name == "mod_a"

    def test_module_temp_path_creates_dir(self, path_svc, tmp_path):
        p = path_svc.module_temp_path("my_module")
        assert p.exists()
        assert p.is_dir()

    def test_exports_path_creates_dir(self, path_svc, tmp_path):
        p = path_svc.exports_path()
        assert p.exists()
        assert p.is_dir()

    def test_different_modules_get_different_paths(self, path_svc):
        pa = path_svc.module_data_path("mod_a")
        pb = path_svc.module_data_path("mod_b")
        assert pa != pb
