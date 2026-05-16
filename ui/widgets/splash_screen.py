"""Splash screen shown during IIMP startup.

Displays application name and a progress bar while modules are being
discovered.  Designed to be lightweight — no heavy imports beyond Qt.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QProgressBar,
    QSplashScreen,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QColor, QPixmap


class StartupSplash(QSplashScreen):
    """Minimal splash screen with a progress bar for module discovery."""

    _WIDTH = 420
    _HEIGHT = 200

    def __init__(self) -> None:
        # Create a blank pixmap as background
        pixmap = QPixmap(self._WIDTH, self._HEIGHT)
        pixmap.fill(QColor("#ffffff"))
        super().__init__(pixmap)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)

        # Overlay widget for layout
        container = QWidget(self)
        container.setGeometry(0, 0, self._WIDTH, self._HEIGHT)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(30, 30, 30, 20)
        layout.setSpacing(10)

        # Title
        title = QLabel("IIMP")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size: 28px; font-weight: bold; color: #2c3e50;")
        layout.addWidget(title)

        # Subtitle
        subtitle = QLabel("Integrated Interactive Module Platform")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("font-size: 12px; color: #7f8c8d;")
        layout.addWidget(subtitle)

        layout.addStretch()

        # Status label
        self._status = QLabel("Initializing…")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet("font-size: 11px; color: #555;")
        layout.addWidget(self._status)

        # Progress bar
        self._progress = QProgressBar()
        self._progress.setRange(0, 0)  # indeterminate until total is known
        self._progress.setTextVisible(False)
        self._progress.setFixedHeight(6)
        self._progress.setStyleSheet(
            "QProgressBar { background: #ecf0f1; border: none; border-radius: 3px; }"
            "QProgressBar::chunk { background: #3498db; border-radius: 3px; }"
        )
        layout.addWidget(self._progress)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_status(self, text: str) -> None:
        """Update the status label text."""
        self._status.setText(text)
        QApplication.processEvents()

    def set_progress(self, current: int, total: int, module_name: str = "") -> None:
        """Update the progress bar and status text.

        This is intended to be passed (via a lambda/closure) as the
        ``on_progress`` callback to the discovery pipeline.
        """
        if total > 0 and self._progress.maximum() != total:
            self._progress.setRange(0, total)
        self._progress.setValue(current)
        label = f"Discovering modules… ({current}/{total})"
        if module_name:
            label += f"  —  {module_name}"
        self._status.setText(label)
        QApplication.processEvents()

    def finish_splash(self, main_window: QWidget) -> None:
        """Close the splash and activate the main window."""
        self.finish(main_window)
