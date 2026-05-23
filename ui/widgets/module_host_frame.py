"""ModuleHostFrame — the QWidget region where a module's view is embedded.

Rules:
- Only one module view may be active at a time.
- Module view must never manage this frame directly.
- Shows a fallback placeholder when no module is loaded or load failed.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QVBoxLayout,
    QWidget,
)

from core.utils.logger import get_logger
from ui.widgets.empty_state import EmptyState

_log = get_logger("iimp.ui.host_frame")


class ModuleHostFrame(QFrame):
    """Container that hosts module views inside the shell."""

    browse_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("module_host_frame")
        self._current_module_id: str | None = None
        self._current_widget: QWidget | None = None
        self._setup_ui()

    def _setup_ui(self) -> None:
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

        self._placeholder = self._make_state_widget(
            kicker="WORKSPACE",
            title="Chưa có module đang mở",
            message=(
                "Mở Library để chọn một module và bắt đầu làm việc trong không gian tương tác chính của IIMP."
            ),
        )
        self._layout.addWidget(self._placeholder)
        self._current_widget = self._placeholder

    def _make_state_widget(
        self,
        kicker: str,
        title: str,
        message: str,
        *,
        is_error: bool = False,
    ) -> QWidget:
        panel = EmptyState(
            kicker=kicker,
            title=title,
            message=message,
            action_label="Mở Library",
            action_role="workspace-link",
            on_action=self.browse_requested.emit,
            state="error" if is_error else "empty",
        )
        panel.setProperty("hostOwned", True)
        return panel

    def show_module(self, module_id: str, widget: QWidget) -> None:
        """Replace the current content with *widget* for *module_id*."""
        self._clear()
        self._current_module_id = module_id
        self._current_widget = widget
        self._layout.addWidget(widget)
        widget.show()
        _log.debug(f"Hosting module view: {module_id}")

    def show_error(self, module_id: str, message: str) -> None:
        """Display a user-friendly error placeholder for a failed module."""
        self._clear()
        container = self._make_state_widget(
            kicker=module_id,
            title="Không thể mở module",
            message=message or "Đã xảy ra lỗi khi nạp hoặc kích hoạt module này.",
            is_error=True,
        )
        self._current_module_id = module_id
        self._current_widget = container
        self._layout.addWidget(container)

    def show_placeholder(self) -> None:
        """Return to the default empty state."""
        self._clear()
        self._current_module_id = None
        self._current_widget = self._placeholder
        self._layout.addWidget(self._placeholder)
        self._placeholder.show()

    def _clear(self) -> None:
        if self._current_widget is not None:
            widget = self._current_widget
            self._layout.removeWidget(widget)
            widget.hide()
            if widget is self._placeholder:
                pass
            elif bool(widget.property("hostOwned")):
                widget.deleteLater()
            else:
                # Keep module-owned views alive for modules that cache and reuse their root widget.
                widget.setParent(None)
            self._current_widget = None

    @property
    def active_module_id(self) -> str | None:
        return self._current_module_id
