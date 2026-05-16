"""Activity history view — full event log from the activity_logs table."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.storage.models import ActivityLog
from core.storage.session import get_session
from core.utils.logger import get_logger

_log = get_logger("iimp.ui.activity_history")

_ALL_TYPES = [
    "app_start", "app_shutdown",
    "module_loaded", "module_activated", "module_deactivated", "module_load_error",
    "module_installed", "module_uninstalled", "module_enabled", "module_disabled",
    "state_saved", "state_restored", "state_restore_failed",
    "export_started", "export_completed", "export_failed",
]

_COLUMN_HEADERS = ["Thời gian", "Loại sự kiện", "Module", "Nội dung"]


class ActivityHistoryView(QWidget):
    """Full activity log with type filter and clear option."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._filter_combo: QComboBox | None = None
        self._table: QTableWidget | None = None
        self._setup_ui()
        self.refresh()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 16)
        outer.setSpacing(12)

        # Header row
        header_row = QHBoxLayout()
        title = QLabel("Nhật ký hoạt động")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50;")
        header_row.addWidget(title, stretch=1)

        filter_label = QLabel("Lọc:")
        filter_label.setStyleSheet("color: #7F8C8D; font-size: 12px;")
        header_row.addWidget(filter_label)

        filter_combo = QComboBox()
        filter_combo.addItem("Tất cả", "")
        for t in _ALL_TYPES:
            filter_combo.addItem(t.replace("_", " ").title(), t)
        filter_combo.currentIndexChanged.connect(self.refresh)
        self._filter_combo = filter_combo
        header_row.addWidget(filter_combo)

        btn_refresh = QPushButton("↻")
        btn_refresh.setToolTip("Làm mới")
        btn_refresh.setFixedWidth(32)
        btn_refresh.clicked.connect(self.refresh)
        btn_refresh.setStyleSheet(
            "QPushButton { background: #ECF0F1; border-radius: 4px; padding: 4px; }"
            " QPushButton:hover { background: #BDC3C7; }"
        )
        header_row.addWidget(btn_refresh)
        outer.addLayout(header_row)

        # Table
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(_COLUMN_HEADERS)
        table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.setShowGrid(False)
        table.setFrameShape(QFrame.Shape.NoFrame)
        table.setStyleSheet(
            "QTableWidget { border: none; background: white; }"
            "QHeaderView::section { background: #F8F9FA; color: #7F8C8D;"
            " font-weight: bold; font-size: 11px; border: none;"
            " border-bottom: 1px solid #ECF0F1; padding: 4px 8px; }"
            "QTableWidget::item { padding: 4px 8px; color: #2C3E50; font-size: 12px; }"
            "QTableWidget::item:selected { background: #D6EAF8; color: #2C3E50; }"
        )
        self._table = table
        outer.addWidget(table, stretch=1)

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        if self._table is None:
            return
        filter_type = ""
        if self._filter_combo:
            filter_type = self._filter_combo.currentData() or ""

        try:
            with get_session() as session:
                q = session.query(ActivityLog).order_by(ActivityLog.created_at.desc())
                if filter_type:
                    q = q.filter(ActivityLog.activity_type == filter_type)
                rows = q.limit(200).all()
                entries = [
                    (
                        r.created_at.strftime("%Y-%m-%d %H:%M:%S") if r.created_at else "",
                        r.activity_type or "",
                        r.module_id or "",
                        r.message or "",
                    )
                    for r in rows
                ]
        except Exception as exc:  # noqa: BLE001
            _log.error(f"ActivityHistoryView DB query failed: {exc}")
            entries = []

        _TYPE_COLORS = {
            "module_load_error": "#E74C3C",
            "module_loaded": "#2980B9",
            "module_activated": "#27AE60",
            "app_start": "#3498DB",
            "app_shutdown": "#95A5A6",
            "export_completed": "#8E44AD",
            "module_disabled": "#E67E22",
            "module_uninstalled": "#C0392B",
        }

        table = self._table
        table.setRowCount(len(entries))
        for row_idx, (ts, atype, mid, msg) in enumerate(entries):
            color = _TYPE_COLORS.get(atype, "#2C3E50")
            items = [ts, atype.replace("_", " ").title(), mid, msg]
            for col_idx, text in enumerate(items):
                item = QTableWidgetItem(text)
                if col_idx == 1:
                    item.setForeground(QColor(color))
                table.setItem(row_idx, col_idx, item)
