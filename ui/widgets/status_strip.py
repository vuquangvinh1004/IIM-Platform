"""Status strip at the bottom of the main window."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QStatusBar, QWidget


class StatusStrip(QStatusBar):
    """Displays app status, module count, DB state and current module."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._status_label = QLabel("Ready")
        self._module_label = QLabel("Modules: 0")
        self._db_label = QLabel("DB: OK")
        self.addWidget(self._status_label)
        self.addPermanentWidget(self._module_label)
        self.addPermanentWidget(self._db_label)

    def set_status(self, text: str) -> None:
        self._status_label.setText(text)

    def set_module_count(self, count: int) -> None:
        self._module_label.setText(f"Modules: {count}")

    def set_db_status(self, ok: bool) -> None:
        if ok:
            self._db_label.setText("DB: OK")
            self._db_label.setStyleSheet("color: #2ECC71;")
        else:
            self._db_label.setText("DB: Error")
            self._db_label.setStyleSheet("color: #E74C3C;")
