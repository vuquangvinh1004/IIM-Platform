"""Export service — provides safe file-export capability to modules.

Modules with ``export.file`` permission call this service instead of
writing files directly. The service delegates the save-dialog to Qt so
that the shell controls the UX and the module only receives the chosen path.
"""
from __future__ import annotations

from pathlib import Path

try:
    from PySide6.QtWidgets import QFileDialog, QWidget
except ImportError:  # pragma: no cover — only missing in headless test envs
    QFileDialog = None  # type: ignore[assignment,misc]
    QWidget = object  # type: ignore[assignment,misc]

from core.utils.exceptions import ExportError
from core.utils.logger import get_logger

_log = get_logger("iimp.services.export")


class ExportService:
    """Coordinates file export for modules."""

    def __init__(self, default_export_dir: Path) -> None:
        self._default_dir = default_export_dir

    def ask_save_path(
        self,
        parent: QWidget | None,
        title: str = "Export",
        default_name: str = "export",
        file_filter: str = "PNG Image (*.png);;All Files (*)",
    ) -> Path | None:
        """Open a save-file dialog and return the chosen path or None if cancelled."""
        path, _ = QFileDialog.getSaveFileName(
            parent,
            title,
            str(self._default_dir / default_name),
            file_filter,
        )
        return Path(path) if path else None

    def write_bytes(self, path: Path, data: bytes) -> None:
        """Write *data* to *path*, raising ExportError on failure."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            _log.info(f"Exported to: {path}")
        except OSError as exc:
            raise ExportError(f"Failed to write export file '{path}': {exc}") from exc
