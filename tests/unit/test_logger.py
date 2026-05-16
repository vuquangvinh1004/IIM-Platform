"""Unit tests for logger configuration."""
from __future__ import annotations

import pytest


class TestConfigureLogging:

    def test_configure_logging_debug_mode(self, tmp_path, monkeypatch):
        """configure_logging(debug=True) should run without error."""
        import core.utils.logger as log_module
        monkeypatch.setattr(log_module, "LOGS_DIR", tmp_path)
        log_module.configure_logging(debug=True)

    def test_configure_logging_info_mode(self, tmp_path, monkeypatch):
        """configure_logging(debug=False) should run without error."""
        import core.utils.logger as log_module
        monkeypatch.setattr(log_module, "LOGS_DIR", tmp_path)
        log_module.configure_logging(debug=False)

    def test_get_logger_returns_callable(self):
        """get_logger should return a logger-like object with info()."""
        from core.utils.logger import get_logger
        log = get_logger("test.component")
        assert callable(log.info)
        assert callable(log.error)
        assert callable(log.debug)
