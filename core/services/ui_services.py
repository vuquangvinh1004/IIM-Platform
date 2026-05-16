"""UI service interfaces: DialogService and ThemeService.

Both classes expose a stable API that the rest of the application depends
on today.  Phase 3 will replace the implementations (e.g. modal dialogs,
a theme file loader) without changing the public signatures.
"""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox, QWidget

from core.utils.logger import get_logger

_log = get_logger("iimp.services.dialog")


class DialogService:
    """Present modal feedback to the user from any service or module.

    All methods block until the user dismisses the dialog.  Phase 3 will
    add async variants and an injectable backend for testing (so tests can
    assert dialogs without showing a real window).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        self._parent = parent

    def info(self, title: str, message: str) -> None:
        QMessageBox.information(self._parent, title, message)

    def warning(self, title: str, message: str) -> None:
        QMessageBox.warning(self._parent, title, message)

    def error(self, title: str, message: str) -> None:
        QMessageBox.critical(self._parent, title, message)

    def confirm(self, title: str, message: str) -> bool:
        result = QMessageBox.question(self._parent, title, message)
        return result == QMessageBox.StandardButton.Yes


class ThemeService:
    """Resolve design-token names to concrete color values.

    Consumers call ``get_color(token)`` rather than hard-coding hex values;
    this lets Phase 3 swap the implementation for a theme file loader
    (JSON/TOML) or a dark-mode toggle without touching call sites.
    """

    def get_color(self, token: str) -> str:
        _defaults = {
            "primary": "#3498DB",
            "error": "#E74C3C",
            "success": "#2ECC71",
            "surface": "#FFFFFF",
            "on_surface": "#2C3E50",
        }
        return _defaults.get(token, "#000000")
