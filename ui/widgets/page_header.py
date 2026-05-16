"""Reusable page header primitive for shell views."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QFrame, QVBoxLayout, QWidget


class PageHeader(QFrame):
    """Consistent shell page header with eyebrow, title, and description."""

    def __init__(
        self,
        eyebrow: str,
        title: str,
        description: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("pageHeaderPanel")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(4)

        eyebrow_label = QLabel(eyebrow)
        eyebrow_label.setObjectName("pageEyebrow")

        title_label = QLabel(title)
        title_label.setObjectName("pageTitle")

        description_label = QLabel(description)
        description_label.setObjectName("pageDescription")
        description_label.setWordWrap(True)

        layout.addWidget(eyebrow_label)
        layout.addWidget(title_label)
        layout.addWidget(description_label)