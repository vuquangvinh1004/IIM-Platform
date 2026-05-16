"""Reusable empty and error state panel for shell views."""
from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QLabel, QPushButton, QVBoxLayout, QWidget


class EmptyState(QFrame):
    """Centered state panel with title, message, and optional action."""

    def __init__(
        self,
        kicker: str,
        title: str,
        message: str,
        *,
        action_label: str | None = None,
        action_role: str = "workspace-link",
        on_action: Callable[[], None] | None = None,
        state: str = "empty",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("workspace_state_container")
        self.setProperty("state", state)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(36, 36, 36, 36)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        kicker_label = QLabel(kicker)
        kicker_label.setObjectName("workspace_state_kicker")

        title_label = QLabel(title)
        title_label.setObjectName("workspace_state_title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        message_label = QLabel(message)
        message_label.setObjectName("workspace_state_message")
        message_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        message_label.setWordWrap(True)

        layout.addWidget(kicker_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message_label, alignment=Qt.AlignmentFlag.AlignCenter)

        if action_label and on_action is not None:
            layout.addSpacing(8)
            button = QPushButton(action_label)
            button.setProperty("role", action_role)
            button.clicked.connect(on_action)
            layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)