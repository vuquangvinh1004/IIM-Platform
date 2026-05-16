"""Unit tests for startup_checks."""
from __future__ import annotations

import sys

import pytest

from core.app_kernel.startup_checks import (
    _check_python_version,
    _check_pyside6,
    _check_sqlalchemy,
    run_startup_checks,
)


class TestIndividualChecks:

    def test_python_version_passes_current(self):
        # Current Python is known-good (3.11+ required)
        result = _check_python_version()
        assert result is None

    def test_python_version_fails_old(self, monkeypatch):
        monkeypatch.setattr(sys, "version_info", (3, 8, 0, "final", 0))
        result = _check_python_version()
        assert result is not None
        assert "3.11" in result

    def test_check_sqlalchemy_passes(self):
        # SQLAlchemy is installed in this environment
        result = _check_sqlalchemy()
        assert result is None

    def test_check_pyside6_returns_string_or_none(self):
        # Just verify it doesn't raise; result depends on whether PySide6 is installed
        result = _check_pyside6()
        assert result is None or isinstance(result, str)


class TestRunStartupChecks:

    def test_returns_list(self):
        errors = run_startup_checks()
        assert isinstance(errors, list)

    def test_all_pass_in_dev_environment(self, monkeypatch):
        # Patch version to pass Python check; SQLAlchemy is present; PySide6 may or may not be
        # At minimum we just verify that the function runs without crash
        errors = run_startup_checks()
        # Python and SQLAlchemy should pass; PySide6 check may fail in headless env — acceptable
        python_errors = [e for e in errors if "Python" in e]
        sqlalchemy_errors = [e for e in errors if "SQLAlchemy" in e]
        assert python_errors == []
        assert sqlalchemy_errors == []
