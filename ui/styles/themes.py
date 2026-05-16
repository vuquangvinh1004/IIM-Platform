"""Theme manager — applies QSS stylesheets to the application."""
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from ui.styles.qss_styles import LIGHT_STYLESHEET


def apply_theme(app: QApplication, theme: str = "light") -> None:
    """Apply the named theme stylesheet to *app*."""
    if theme == "light":
        app.setStyleSheet(LIGHT_STYLESHEET)
    else:
        # Dark theme: Phase 3+
        app.setStyleSheet(LIGHT_STYLESHEET)
