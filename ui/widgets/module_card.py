"""Module card widget shown in the library view."""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ModuleCard(QFrame):
    """Displays module metadata and provides Open/Details actions."""

    open_requested = Signal(str)     # module_id
    details_requested = Signal(str)  # module_id

    def __init__(
        self,
        module_id: str,
        name: str,
        category: str,
        version: str,
        description: str,
        enabled: bool = True,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("module_card")
        self._module_id = module_id
        self._search_blob = " ".join(
            [module_id, name, category, version, description]
        ).lower()
        self._setup_ui(name, category, version, description, enabled)

    def _setup_ui(
        self,
        name: str,
        category: str,
        version: str,
        description: str,
        enabled: bool,
    ) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(18, 16, 18, 16)
        outer.setSpacing(12)

        header_row = QHBoxLayout()
        header_row.setSpacing(12)

        title_col = QVBoxLayout()
        title_col.setSpacing(3)

        name_label = QLabel(name)
        name_label.setObjectName("moduleTitle")
        meta_label = QLabel(f"{category} • v{version}")
        meta_label.setObjectName("moduleMeta")
        title_col.addWidget(name_label)
        title_col.addWidget(meta_label)

        badge_label = QLabel(category.replace("_", " ").title())
        badge_label.setObjectName("moduleBadge")

        header_row.addLayout(title_col, stretch=1)
        header_row.addWidget(badge_label)
        outer.addLayout(header_row)

        desc_label = QLabel(description or "Chưa có mô tả cho module này.")
        desc_label.setObjectName("moduleDescription")
        desc_label.setWordWrap(True)
        outer.addWidget(desc_label)

        footer_row = QHBoxLayout()
        footer_row.setSpacing(10)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        module_id_label = QLabel(f"ID: {self._module_id}")
        module_id_label.setObjectName("moduleFootnote")
        status_label = QLabel("Sẵn sàng" if enabled else "Tạm khóa")
        status_label.setObjectName("moduleStatus")
        status_label.setProperty("status", "ready" if enabled else "disabled")

        info_col.addWidget(module_id_label)
        info_col.addWidget(status_label)
        footer_row.addLayout(info_col, stretch=1)

        action_col = QHBoxLayout()
        action_col.setSpacing(8)

        open_btn = QPushButton("Mở")
        open_btn.setEnabled(enabled)
        open_btn.clicked.connect(lambda: self.open_requested.emit(self._module_id))

        details_btn = QPushButton("Chi tiết")
        details_btn.setProperty("role", "ghost")
        details_btn.clicked.connect(lambda: self.details_requested.emit(self._module_id))

        action_col.addWidget(details_btn)
        action_col.addWidget(open_btn)
        footer_row.addLayout(action_col)
        outer.addLayout(footer_row)

    def matches_query(self, query: str) -> bool:
        """Return ``True`` when the card matches the current search query."""
        normalized = query.strip().lower()
        return not normalized or normalized in self._search_blob
