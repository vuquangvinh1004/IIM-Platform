"""Reusable semantic badge primitive for shell states."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QWidget


class StatusBadge(QLabel):
    """Small semantic badge using the shell design-system variants."""

    def __init__(
        self,
        text: str,
        variant: str = "info",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(text, parent)
        self.setObjectName("statusBadge")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_variant(variant)

    def set_variant(self, variant: str) -> None:
        """Update the semantic variant and refresh the applied style."""
        self.setProperty("variant", variant)
        self.style().unpolish(self)
        self.style().polish(self)
        self.update()