"""Integration tests for ExportService (headless, no Qt)."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.services.export_service import ExportService
from core.utils.exceptions import ExportError


class TestExportServiceInit:

    def test_default_dir_stored(self, tmp_path):
        svc = ExportService(tmp_path)
        assert svc._default_dir == tmp_path


class TestWriteBytes:

    def test_creates_file_with_content(self, tmp_path):
        svc = ExportService(tmp_path)
        target = tmp_path / "output.bin"
        svc.write_bytes(target, b"hello world")
        assert target.read_bytes() == b"hello world"

    def test_creates_nested_parent_dirs(self, tmp_path):
        svc = ExportService(tmp_path)
        target = tmp_path / "sub" / "deep" / "out.dat"
        svc.write_bytes(target, b"\x00\x01\x02")
        assert target.exists()
        assert target.read_bytes() == b"\x00\x01\x02"

    def test_oserror_wrapped_as_export_error(self, tmp_path):
        """Writing a file whose parent path is blocked by an existing file raises ExportError."""
        svc = ExportService(tmp_path)
        # Create a file where we'd need a directory
        blocking = tmp_path / "block"
        blocking.write_bytes(b"")
        bad_path = blocking / "child.bin"  # Can't mkdir: blocking is a file
        with pytest.raises(ExportError, match="Failed to write export file"):
            svc.write_bytes(bad_path, b"data")
