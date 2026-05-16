"""Dashboard view — landing page with real platform stats."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from config.settings import APP_NAME, APP_VERSION
from core.storage.models import ActivityLog, ModuleRegistry as DBModuleRegistry
from core.storage.session import get_session
from ui.widgets.page_header import PageHeader


def _stat_card(title: str, value: str, accent: str) -> tuple[QFrame, QLabel]:
    """Create a shell stat card and return the card with its value label."""
    card = QFrame()
    card.setObjectName("statCard")
    card.setProperty("accent", accent)
    layout = QVBoxLayout(card)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(3)

    num_lbl = QLabel(value)
    num_lbl.setObjectName("statValue")
    num_lbl.setProperty("accent", accent)
    num_lbl.setAlignment(Qt.AlignmentFlag.AlignLeft)

    title_lbl = QLabel(title)
    title_lbl.setObjectName("statLabel")

    layout.addWidget(num_lbl)
    layout.addWidget(title_lbl)
    return card, num_lbl


class DashboardView(QWidget):
    """Welcome screen with live platform stats and recent activity feed."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._stat_cards: dict[str, QLabel] = {}  # maps stat key → value label
        self._activity_list: QVBoxLayout | None = None
        self._setup_ui()
        self.refresh()

    # ── Build UI ──────────────────────────────────────────────────────────────

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 20)
        outer.setSpacing(20)

        header = PageHeader(
            eyebrow="DASHBOARD",
            title=APP_NAME,
            description=f"Phiên bản {APP_VERSION} — theo dõi nhanh trạng thái nền tảng và quay lại module gần nhất.",
        )
        outer.addWidget(header)

        # Stat cards row
        stats_row = QWidget()
        grid = QGridLayout(stats_row)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(12)

        stats_meta = [
            ("total", "Tổng module", "primary"),
            ("enabled", "Đang bật", "success"),
            ("disabled", "Đã tắt", "warning"),
            ("error", "Lỗi tải", "danger"),
        ]
        for col, (key, label, accent) in enumerate(stats_meta):
            card, val_lbl = _stat_card(label, "—", accent)
            self._stat_cards[key] = val_lbl
            grid.addWidget(card, 0, col)

        outer.addWidget(stats_row)

        activity_section = QFrame()
        activity_section.setObjectName("dashboardSection")
        al = QVBoxLayout(activity_section)
        al.setContentsMargins(18, 18, 18, 18)
        al.setSpacing(8)

        section_eyebrow = QLabel("RECENT ACTIVITY")
        section_eyebrow.setObjectName("pageEyebrow")
        section_title = QLabel("Hoạt động gần đây")
        section_title.setObjectName("sectionTitle")
        section_meta = QLabel("Các sự kiện mới nhất của shell và module trong phiên làm việc hiện tại.")
        section_meta.setObjectName("sectionMeta")

        al.addWidget(section_eyebrow)
        al.addWidget(section_title)
        al.addWidget(section_meta)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        container = QWidget()
        self._activity_list = QVBoxLayout(container)
        self._activity_list.setContentsMargins(0, 0, 0, 0)
        self._activity_list.setSpacing(8)
        self._activity_list.addStretch()
        scroll.setWidget(container)
        al.addWidget(scroll)
        outer.addWidget(activity_section, stretch=1)

    # ── Public ────────────────────────────────────────────────────────────────

    def refresh(self) -> None:
        """Pull fresh stats from DB and repaint."""
        self._refresh_stats()
        self._refresh_activity()

    # ── Private ───────────────────────────────────────────────────────────────

    def _refresh_stats(self) -> None:
        try:
            with get_session() as session:
                total = session.query(DBModuleRegistry).count()
                enabled = session.query(DBModuleRegistry).filter_by(is_enabled=True).count()
                disabled = total - enabled
        except Exception:  # noqa: BLE001
            total = enabled = disabled = 0

        updates = {
            "total": str(total),
            "enabled": str(enabled),
            "disabled": str(disabled),
            "error": "0",  # populated by registry at runtime; DB has no error column
        }
        for key, val in updates.items():
            lbl = self._stat_cards.get(key)
            if lbl:
                lbl.setText(val)

    def _refresh_activity(self) -> None:
        if self._activity_list is None:
            return
        # Remove all items except the trailing stretch
        while self._activity_list.count() > 1:
            item = self._activity_list.takeAt(0)
            if item and item.widget():
                item.widget().deleteLater()

        try:
            with get_session() as session:
                rows = (
                    session.query(ActivityLog)
                    .order_by(ActivityLog.created_at.desc())
                    .limit(20)
                    .all()
                )
                entries = [
                    (r.created_at, r.activity_type, r.module_id or "", r.message or "")
                    for r in rows
                ]
        except Exception:  # noqa: BLE001
            entries = []

        if not entries:
            placeholder = QLabel("Chưa có hoạt động nào được ghi nhận.")
            placeholder.setObjectName("mutedText")
            self._activity_list.insertWidget(0, placeholder)
            return

        _TYPE_COLORS = {
            "module_loaded": "#2980B9",
            "module_activated": "#27AE60",
            "module_deactivated": "#E67E22",
            "module_load_error": "#E74C3C",
            "app_start": "#3498DB",
            "app_shutdown": "#95A5A6",
            "export_completed": "#8E44AD",
        }

        for idx, (ts, atype, mid, msg) in enumerate(entries):
            row_w = QFrame()
            row_w.setObjectName("activityRow")
            row_w.setProperty("alt", "true" if idx % 2 else "false")
            row_layout = QHBoxLayout(row_w)
            row_layout.setContentsMargins(10, 8, 10, 8)
            row_layout.setSpacing(8)

            color = _TYPE_COLORS.get(atype, "#7F8C8D")
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {color}; font-size: 10px;")
            dot.setFixedWidth(14)

            time_str = ts.strftime("%H:%M:%S") if ts else ""
            time_lbl = QLabel(time_str)
            time_lbl.setObjectName("mutedText")
            time_lbl.setFixedWidth(60)

            type_lbl = QLabel(atype.replace("_", " ").title())
            type_lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: bold;")
            type_lbl.setFixedWidth(150)

            details = f"[{mid}] {msg}".strip(" []") if mid else msg
            detail_lbl = QLabel(details)
            detail_lbl.setObjectName("activityDetail")
            detail_lbl.setWordWrap(False)

            row_layout.addWidget(dot)
            row_layout.addWidget(time_lbl)
            row_layout.addWidget(type_lbl)
            row_layout.addWidget(detail_lbl, stretch=1)

            self._activity_list.insertWidget(idx, row_w)
