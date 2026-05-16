"""Workspace view — wraps the ModuleHostFrame for the navigation stack."""
from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.widgets.module_host_frame import ModuleHostFrame


class WorkspaceView(QWidget):
    """Navigation destination that hosts the active module."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.host_frame = ModuleHostFrame(self)
        layout.addWidget(self.host_frame)
