"""StarterModule — minimal BaseModule implementation as a template.

Copy and rename this file (and ``entry.py``, ``module.json``) to create
a new module. Replace all TODO comments with actual implementation.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.module_runtime.base_module import BaseModule


class StarterModule(BaseModule):
    """Minimal working module for use as a development template."""

    def __init__(self, manifest: dict, context) -> None:
        super().__init__(manifest, context)
        self._view: QWidget | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self.context.logger.info(f"[{self.module_id}] on_load()")

    def build_view(self) -> QWidget:
        if self._view is None:
            root = QWidget()
            layout = QVBoxLayout(root)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            label = QLabel(f"Module: {self.module_name}\nVersion: {self.module_version}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 16px; color: #2C3E50;")
            layout.addWidget(label)

            self._view = root
        return self._view

    def on_activate(self) -> None:
        self.context.logger.info(f"[{self.module_id}] on_activate()")

    def on_deactivate(self) -> None:
        self.context.logger.info(f"[{self.module_id}] on_deactivate()")

    def on_unload(self) -> None:
        self.context.logger.info(f"[{self.module_id}] on_unload()")
        self._view = None
