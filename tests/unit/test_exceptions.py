"""Unit tests for the IIMP exception hierarchy."""
from __future__ import annotations

import pytest

from core.utils.exceptions import (
    ExportError,
    IIMPError,
    ManifestError,
    ManifestNotFoundError,
    ManifestValidationError,
    MigrationError,
    ModuleCompatibilityError,
    ModuleLoadError,
    ModuleNotFoundError,
    ServiceUnavailableError,
    StateError,
    StateRestoreError,
    StateSaveError,
    StorageError,
)


class TestExceptionHierarchy:

    def test_iimp_error_is_base(self):
        exc = IIMPError("base")
        assert isinstance(exc, Exception)

    def test_manifest_error_message(self):
        exc = ManifestError("/path/to/mod", "missing field")
        assert "/path/to/mod" in str(exc)
        assert "missing field" in str(exc)
        assert exc.module_path == "/path/to/mod"
        assert exc.detail == "missing field"

    def test_manifest_not_found_is_manifest_error(self):
        exc = ManifestNotFoundError("/path/to/mod")
        assert isinstance(exc, ManifestError)
        assert "module.json not found" in str(exc)

    def test_manifest_validation_error_is_manifest_error(self):
        exc = ManifestValidationError("/path", "bad schema")
        assert isinstance(exc, ManifestError)

    def test_module_load_error_message(self):
        exc = ModuleLoadError("my_mod", "import failed")
        assert "my_mod" in str(exc)
        assert "import failed" in str(exc)
        assert exc.module_id == "my_mod"

    def test_module_not_found_is_load_error(self):
        exc = ModuleNotFoundError("mod", "no class")
        assert isinstance(exc, ModuleLoadError)

    def test_module_compatibility_error(self):
        exc = ModuleCompatibilityError("mod", "2.0.0", "1.0.0")
        assert "2.0.0" in str(exc) or "mod" in str(exc)
        assert isinstance(exc, IIMPError)

    def test_state_errors_hierarchy(self):
        save_err = StateSaveError("fail")
        restore_err = StateRestoreError("fail")
        assert isinstance(save_err, StateError)
        assert isinstance(restore_err, StateError)
        assert isinstance(save_err, IIMPError)

    def test_storage_error_hierarchy(self):
        migration = MigrationError("migration failed")
        assert isinstance(migration, StorageError)
        assert isinstance(migration, IIMPError)

    def test_service_unavailable_error_message(self):
        exc = ServiceUnavailableError("ThemeService")
        assert "ThemeService" in str(exc)
        assert isinstance(exc, IIMPError)

    def test_export_error(self):
        exc = ExportError("write failed")
        assert isinstance(exc, IIMPError)
        assert "write failed" in str(exc)
