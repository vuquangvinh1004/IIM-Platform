"""QC Inspection — Mô phỏng kiểm tra chất lượng sản phẩm v1.0.0

Mô phỏng quy trình QC (Quality Control) trên băng chuyền sản xuất:

  Giao diện kiểm tra:
    - Nhập số sản phẩm/lần (tối đa 40) và số lần kiểm tra
    - QC Thủ công: xem sản phẩm → đánh dấu phế phẩm → Ghi nhận
    - QC Tự động: tự sinh dữ liệu cho toàn bộ lần còn lại
    - Bảng kết quả: Lần | Tổng SP | Số PP | Tỷ lệ PP

  Giao diện mô phỏng (sau khi hoàn thành):
    - Thống kê tổng hợp
    - Bảng tần số + biểu đồ cột phế phẩm
    - Đối chiếu Phân phối Nhị thức Bin(n, p) và Poisson Po(μ=n·p)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Any

try:
    from PySide6.QtCore import Qt, QPointF, QRectF
    from PySide6.QtGui import (
        QBrush, QColor, QFont, QPainter, QPainterPath, QPen,
    )
    from PySide6.QtWidgets import (
        QAbstractSpinBox, QDialog, QDialogButtonBox, QDoubleSpinBox,
        QFormLayout, QFrame, QGridLayout, QGroupBox,
        QHBoxLayout, QHeaderView, QLabel, QPushButton,
        QScrollArea, QSizePolicy, QSpinBox,
        QStackedWidget, QTableWidget, QTableWidgetItem,
        QVBoxLayout, QWidget,
    )
    _QT = True
except ImportError:  # pragma: no cover
    _QT = False

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    _MPL = True
except ImportError:  # pragma: no cover
    _MPL = False

from core.module_runtime.base_module import BaseModule
from core.module_runtime.module_context import ModuleContext

_WidgetBase = QWidget if _QT else object  # type: ignore[misc]
_DialogBase = QDialog if _QT else object  # type: ignore[misc]

# ─── Constants ────────────────────────────────────────────────────────────────

MAX_PRODUCTS: int = 60
DEFAULT_N_PRODUCTS: int = 10
DEFAULT_N_ROUNDS: int = 10
_DEFECT_PROB: float = 0.25  # background defect rate (hidden from user in inspection view)


# ─── Pure-Python Engine ───────────────────────────────────────────────────────


@dataclass
class QCRecord:
    """Single inspection round result."""

    round_no: int
    total: int
    defects: int

    @property
    def rate(self) -> float:
        return self.defects / self.total if self.total > 0 else 0.0


class QCInspectionEngine:
    """Stateful QC inspection engine — pure Python, fully testable without Qt."""

    def __init__(self) -> None:
        self.n_products: int = DEFAULT_N_PRODUCTS
        self.n_rounds: int = DEFAULT_N_ROUNDS
        self._defect_prob: float = _DEFECT_PROB
        self.records: list[QCRecord] = []
        self.current_products: list[bool] = []   # True = defective
        self._round_pending: bool = False

    # ── Configuration ─────────────────────────────────────────────────────────

    def configure(self, n_products: int, n_rounds: int, defect_prob: float | None = None) -> None:
        """Set inspection parameters. Only allowed when no records yet."""
        self.n_products = max(1, min(MAX_PRODUCTS, n_products))
        self.n_rounds = max(1, n_rounds)
        if defect_prob is not None:
            self._defect_prob = max(0.01, min(1.0, defect_prob))

    # ── Simulation API ────────────────────────────────────────────────────────

    def generate_round(self) -> list[bool]:
        """Generate one batch of products for manual inspection.

        Returns a list of booleans (True = defective).
        """
        self.current_products = [
            random.random() < self._defect_prob
            for _ in range(self.n_products)
        ]
        self._round_pending = True
        return list(self.current_products)

    def record_manual(self, selected_indices: list[int]) -> QCRecord:
        """Commit a manual inspection round.

        Args:
            selected_indices: Positions the user marked as defective (0-based).

        Returns:
            The newly created QCRecord.
        """
        rec = QCRecord(
            round_no=len(self.records) + 1,
            total=self.n_products,
            defects=len(selected_indices),
        )
        self.records.append(rec)
        self.current_products = []
        self._round_pending = False
        return rec

    def auto_complete(self) -> list[QCRecord]:
        """Auto-generate and record all remaining rounds.

        Returns:
            Newly added QCRecord list.
        """
        new_records: list[QCRecord] = []
        for _ in range(self.n_rounds - len(self.records)):
            defects = sum(
                1 for _ in range(self.n_products)
                if random.random() < self._defect_prob
            )
            rec = QCRecord(
                round_no=len(self.records) + 1,
                total=self.n_products,
                defects=defects,
            )
            self.records.append(rec)
            new_records.append(rec)
        self.current_products = []
        self._round_pending = False
        return new_records

    def reset(self) -> None:
        self.records.clear()
        self.current_products = []
        self._round_pending = False

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def rounds_done(self) -> int:
        return len(self.records)

    @property
    def is_complete(self) -> bool:
        return len(self.records) >= self.n_rounds

    @property
    def is_pending_record(self) -> bool:
        return self._round_pending and bool(self.current_products)

    @property
    def total_products(self) -> int:
        return sum(r.total for r in self.records)

    @property
    def total_defects(self) -> int:
        return sum(r.defects for r in self.records)

    @property
    def empirical_p(self) -> float:
        tp = self.total_products
        return self.total_defects / tp if tp > 0 else 0.0

    @property
    def defect_prob(self) -> float:
        """The configured (true) defect probability used to generate products."""
        return self._defect_prob

    # ── Statistics ────────────────────────────────────────────────────────────

    def frequency_table(self) -> dict[int, int]:
        """Return {k: count} — how many rounds had exactly k defects."""
        freq: dict[int, int] = {}
        for r in self.records:
            freq[r.defects] = freq.get(r.defects, 0) + 1
        return freq

    # ── Persistence ───────────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "state_version": "1.0.0",
            "n_products": self.n_products,
            "n_rounds": self.n_rounds,
            "defect_prob": self._defect_prob,
            "records": [
                {"round_no": r.round_no, "total": r.total, "defects": r.defects}
                for r in self.records
            ],
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.n_products = int(state.get("n_products", DEFAULT_N_PRODUCTS))
        self.n_rounds = int(state.get("n_rounds", DEFAULT_N_ROUNDS))
        self._defect_prob = float(state.get("defect_prob", _DEFECT_PROB))
        self.records = [
            QCRecord(r["round_no"], r["total"], r["defects"])
            for r in state.get("records", [])
        ]
        # Never restore a pending round — grid state cannot be serialised
        self.current_products = []
        self._round_pending = False


# ─── UI: ProductWidget ────────────────────────────────────────────────────────


class _ProductWidget(_WidgetBase):  # type: ignore[misc]
    """Clickable product tile — shows good/defective visually, user-selectable."""

    SIZE: int = 62

    def __init__(self, product_id: int, is_defective: bool,
                 parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self.product_id = product_id
        self.is_defective = is_defective
        self.is_marked: bool = False
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        tip = f"Sản phẩm #{product_id + 1} — {'Phế phẩm' if is_defective else 'Thành phẩm'}"
        self.setToolTip(tip)

    def mousePressEvent(self, event: Any) -> None:  # noqa: N802
        self.is_marked = not self.is_marked
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        if not _QT:  # pragma: no cover
            return
        S = self.SIZE
        pa = QPainter(self)
        pa.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── Isometric box keypoints ───────────────────────────────────────
        TC = QPointF(31,  4)   # top apex
        ML = QPointF( 4, 18)   # mid-left
        MC = QPointF(31, 32)   # mid-center (equator)
        MR = QPointF(58, 18)   # mid-right
        BL = QPointF( 4, 46)   # bottom-left
        BC = QPointF(31, 60)   # bottom apex
        BR = QPointF(58, 46)   # bottom-right

        # ── Face colours ─────────────────────────────────────────────────
        if self.is_defective:
            c_top, c_left, c_rght = QColor("#B8895A"), QColor("#8F6535"), QColor("#6E4A1F")
        else:
            c_top, c_left, c_rght = QColor("#DEB887"), QColor("#C49A5B"), QColor("#A07848")

        edge = QPen(QColor(0, 0, 0, 55), 0.8)

        def _face(pts: list) -> QPainterPath:
            pp = QPainterPath()
            pp.moveTo(pts[0])
            for pt in pts[1:]:
                pp.lineTo(pt)
            pp.closeSubpath()
            return pp

        # ── Top face ─────────────────────────────────────────────────────
        pa.fillPath(_face([TC, MR, MC, ML]), QBrush(c_top))
        pa.setPen(edge)
        pa.drawPath(_face([TC, MR, MC, ML]))

        # ── Left face ────────────────────────────────────────────────────
        pa.fillPath(_face([ML, MC, BC, BL]), QBrush(c_left))
        pa.setPen(edge)
        pa.drawPath(_face([ML, MC, BC, BL]))

        # ── Right face ───────────────────────────────────────────────────
        pa.fillPath(_face([MC, MR, BR, BC]), QBrush(c_rght))
        pa.setPen(edge)
        pa.drawPath(_face([MC, MR, BR, BC]))

        # ── Tape stripes ─────────────────────────────────────────────────
        tape = QPen(QColor("#8B6914"), 2.2, Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.FlatCap)
        pa.setPen(tape)
        pa.drawLine(TC, MC)                                    # spine on top face
        pa.drawLine(MC, BC)                                    # spine on left+right
        pa.drawLine(QPointF(17, 11), QPointF(45, 11))         # cross-strap on top

        # ── Damaged cracks (phế phẩm) ────────────────────────────────────
        if self.is_defective:
            crack = QPen(QColor("#4A2800"), 1.6, Qt.PenStyle.SolidLine,
                         Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
            pa.setPen(crack)
            pa.drawLine(QPointF(39, 35), QPointF(44, 41))   # crack right face
            pa.drawLine(QPointF(44, 41), QPointF(40, 45))
            pa.drawLine(QPointF(40, 45), QPointF(47, 52))
            pa.drawLine(QPointF(14, 39), QPointF(19, 44))   # dent left face
            pa.drawLine(QPointF(19, 44), QPointF(15, 49))
            pa.setPen(QPen(QColor("#4A2800"), 1.2))
            pa.drawLine(QPointF(50, 19), QPointF(55, 24))   # torn top-right

        # ── Product number on top face ────────────────────────────────────
        pa.setPen(QPen(QColor(60, 38, 4, 210)))
        fnt = QFont()
        fnt.setPointSize(7)
        fnt.setBold(True)
        pa.setFont(fnt)
        pa.drawText(QRectF(17, 7, 28, 14),
                    Qt.AlignmentFlag.AlignCenter, str(self.product_id + 1))

        # ── Badge: ✓ green (thành phẩm) / ✕ red (phế phẩm) ─────────────
        bx, by, br = S - 11, S - 11, 10
        badge_col = QColor("#C62828") if self.is_defective else QColor("#2E7D32")
        badge_pp = QPainterPath()
        badge_pp.addEllipse(bx - br, by - br, br * 2, br * 2)
        pa.fillPath(badge_pp, QBrush(badge_col))
        pa.setPen(QPen(QColor("white"), 2.0, Qt.PenStyle.SolidLine,
                       Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        off = 5
        if self.is_defective:
            pa.drawLine(QPointF(bx - off, by - off), QPointF(bx + off, by + off))
            pa.drawLine(QPointF(bx + off, by - off), QPointF(bx - off, by + off))
        else:
            pa.drawLine(QPointF(bx - off + 1, by + 1), QPointF(bx - 1, by + 4))
            pa.drawLine(QPointF(bx - 1, by + 4), QPointF(bx + off, by - 3))

        # ── Selection highlight ───────────────────────────────────────────
        if self.is_marked:
            sel = QPainterPath()
            sel.addRoundedRect(1, 1, S - 2, S - 2, 6, 6)
            pa.fillPath(sel, QBrush(QColor(21, 101, 192, 35)))
            pa.setPen(QPen(QColor("#1565C0"), 2.5))
            pa.drawPath(sel)

        pa.end()


# ─── UI: Product grid frame ───────────────────────────────────────────────────


class _ProductGridFrame(_WidgetBase):  # type: ignore[misc]
    """Scrollable grid of product widgets plus the Ghi nhận button."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        # Progress label
        self._lbl_progress = QLabel("Nhấn 'QC Thủ công' để bắt đầu")
        self._lbl_progress.setStyleSheet("color: #607D8B; font-style: italic; font-size: 14px;")
        outer.addWidget(self._lbl_progress)

        # Lưới sản phẩm — không dùng ScrollArea để luôn hiển thị đủ sản phẩm
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(6)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        outer.addWidget(self._grid_container)

        # Ghi nhận button (right-aligned)
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._btn_record = QPushButton("✔  Ghi nhận")
        self._btn_record.setMinimumWidth(130)
        self._btn_record.setMinimumHeight(34)
        self._btn_record.setEnabled(False)
        self._btn_record.setStyleSheet(
            "QPushButton { background:#2E7D32; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 16px; }"
            "QPushButton:hover { background:#388E3C; }"
            "QPushButton:disabled { background:#BDBDBD; color:#777; }"
        )
        btn_row.addWidget(self._btn_record)
        outer.addLayout(btn_row)

        self._product_widgets: list[Any] = []

    # ── Public interface ──────────────────────────────────────────────────────

    def load_products(self, products: list[bool], round_no: int,
                      n_rounds: int) -> None:
        """Populate the grid with a new batch of products."""
        self._clear_grid()
        # Dynamic columns: fill available width without a hard per-row cap
        tile = _ProductWidget.SIZE + self._grid_layout.spacing()
        avail = self._grid_container.width() - 8
        cols = max(1, avail // tile) if avail >= tile else max(1, len(products))
        for idx, is_defective in enumerate(products):
            w = _ProductWidget(idx, is_defective, self._grid_container)
            self._grid_layout.addWidget(w, idx // cols, idx % cols)
            self._product_widgets.append(w)
        self._lbl_progress.setText(
            f"Lần kiểm tra {round_no}/{n_rounds} — Đánh dấu phế phẩm (click) ▸ nhấn Ghi nhận"
        )
        self._btn_record.setEnabled(True)

    def get_marked_indices(self) -> list[int]:
        """Return 0-based indices of products marked as defective by the user."""
        return [i for i, w in enumerate(self._product_widgets) if w.is_marked]

    def clear(self, message: str = "Nhấn 'QC Thủ công' để bắt đầu") -> None:
        self._clear_grid()
        self._lbl_progress.setText(message)
        self._btn_record.setEnabled(False)

    def connect_record(self, slot: Any) -> None:
        self._btn_record.clicked.connect(slot)

    def _clear_grid(self) -> None:
        for w in self._product_widgets:
            self._grid_layout.removeWidget(w)
            w.setParent(None)  # type: ignore[call-arg]
            w.deleteLater()
        self._product_widgets.clear()


# ─── UI: Records table ────────────────────────────────────────────────────────


class _RecordsTable(_WidgetBase):  # type: ignore[misc]
    """Read-only table: Lần | Tổng SP | Số PP | Tỷ lệ PP."""

    _HEADERS = ["Lần kiểm tra", "Tổng sản phẩm", "Số phế phẩm", "Tỷ lệ phế phẩm"]

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, 4)
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(
            "QTableWidget { gridline-color: #DDE2E8; font-size: 14px; }"
            "QHeaderView::section { background-color: #2C3E50; color: #FFF;"
            " padding: 8px; font-weight: bold; font-size: 15px; }"
        )
        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(True)
        for col in range(3):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table)

    def add_record(self, rec: QCRecord) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._set_cell(row, 0, str(rec.round_no))
        self._set_cell(row, 1, str(rec.total))
        self._set_cell(row, 2, str(rec.defects))
        rate_str = f"{rec.rate:.2%}"
        item = QTableWidgetItem(rate_str)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        if rec.rate == 0.0:
            item.setForeground(QColor("#2E7D32"))
        elif rec.rate < 0.20:
            item.setForeground(QColor("#E65100"))
        else:
            item.setForeground(QColor("#C62828"))
        self._table.setItem(row, 3, item)
        self._table.scrollToBottom()

    def populate(self, records: list[QCRecord]) -> None:
        self._table.setRowCount(0)
        for rec in records:
            self.add_record(rec)

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, col, item)


# ─── UI: Frequency table (simulation) ────────────────────────────────────────


class _FreqTableWidget(_WidgetBase):  # type: ignore[misc]
    """Condensed frequency table: k | Tần số | Tần suất."""

    _HEADERS = ["Số phế phẩm (k)", "Tần số", "Tần suất"]

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("Bảng tần số phế phẩm")
        lbl.setStyleSheet("font-size: 14px; font-weight: bold; color: #37474F;")
        layout.addWidget(lbl)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(self._HEADERS)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.setStyleSheet(
            "QTableWidget { gridline-color: #DDE2E8; font-size: 14px; }"
            "QHeaderView::section { background-color: #2C3E50; color: #FFF;"
            " padding: 8px; font-weight: bold; font-size: 15px; }"
        )
        self._table.setMaximumWidth(300)
        hdr = self._table.horizontalHeader()
        hdr.setStretchLastSection(True)
        for col in range(2):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        layout.addWidget(self._table)

    def populate(self, freq: dict[int, int], n_rounds: int) -> None:
        self._table.setRowCount(0)
        if not freq:
            return
        for k in sorted(freq.keys()):
            count = freq[k]
            row = self._table.rowCount()
            self._table.insertRow(row)
            rel = f"{count / n_rounds:.4f}" if n_rounds > 0 else "—"
            for col, text in enumerate([str(k), str(count), rel]):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(row, col, item)


# ─── UI: Frequency bar chart ──────────────────────────────────────────────────


class _FreqChartCanvas(_WidgetBase):  # type: ignore[misc]
    """Matplotlib bar chart — empirical frequency of defect counts."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._figure = Figure(figsize=(6, 3.5), dpi=100)
            self._figure.patch.set_facecolor("#F8F9FA")
            self._ax = self._figure.add_subplot(111)
            self._canvas = FigureCanvas(self._figure)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self._canvas)
        else:  # pragma: no cover
            layout.addWidget(QLabel("(matplotlib không khả dụng)"))
            self._figure = None
            self._ax = None
            self._canvas = None

    def render(self, freq: dict[int, int], n_rounds: int) -> None:
        if not _MPL or self._ax is None:  # pragma: no cover
            return
        assert self._figure is not None and self._canvas is not None
        ax = self._ax
        ax.clear()
        ax.set_facecolor("#FDFEFE")

        if not freq:
            ax.text(0.5, 0.5, "Chưa có dữ liệu", ha="center", va="center",
                    transform=ax.transAxes, fontsize=12, color="#9E9E9E")
            self._canvas.draw()
            return

        k_max = max(freq.keys())
        k_vals = list(range(0, k_max + 1))
        counts = [freq.get(k, 0) for k in k_vals]

        bars = ax.bar(k_vals, counts, color="#1976D2", alpha=0.82,
                      edgecolor="white", linewidth=0.9)
        for bar, count in zip(bars, counts):
            if count > 0:
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + 0.06,
                        str(count),
                        ha="center", va="bottom", fontsize=9, color="#333")

        ax.set_xticks(k_vals)
        ax.set_xlabel("Số phế phẩm (k)", fontsize=10, color="#555")
        ax.set_ylabel("Tần số (số lần KT)", fontsize=10, color="#555")
        ax.tick_params(labelsize=9, colors="#555")
        for spine in ax.spines.values():
            spine.set_edgecolor("#DDD")
        ax.grid(True, axis="y", linestyle="--", linewidth=0.5,
                color="#E0E0E0", alpha=0.7)
        ax.set_title("Biểu đồ tần số phế phẩm",
                     fontsize=11, fontweight="bold", pad=8,
                     bbox=dict(boxstyle="round,pad=0.3", fc="white",
                               ec="#BDBDBD", alpha=0.85))
        self._figure.tight_layout(pad=1.2)
        self._canvas.draw()


# ─── UI: Binomial + Poisson charts ────────────────────────────────────────────


class _DistributionCanvas(_WidgetBase):  # type: ignore[misc]
    """Side-by-side Binomial and Poisson distribution charts with empirical overlay."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._figure = Figure(figsize=(12, 4.2), dpi=96)
            self._figure.patch.set_facecolor("#F8F9FA")
            self._ax_binom = self._figure.add_subplot(1, 2, 1)
            self._ax_pois = self._figure.add_subplot(1, 2, 2)
            self._canvas = FigureCanvas(self._figure)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self._canvas)
        else:  # pragma: no cover
            layout.addWidget(QLabel("(matplotlib không khả dụng)"))
            self._figure = None
            self._ax_binom = None
            self._ax_pois = None
            self._canvas = None

    @staticmethod
    def _binom_pmf(k: int, n: int, p: float) -> float:
        if p <= 0.0:
            return 1.0 if k == 0 else 0.0
        if p >= 1.0:
            return 1.0 if k == n else 0.0
        return math.comb(n, k) * (p ** k) * ((1.0 - p) ** (n - k))

    @staticmethod
    def _poisson_pmf(k: int, lam: float) -> float:
        if lam <= 0.0:
            return 1.0 if k == 0 else 0.0
        return math.exp(-lam) * (lam ** k) / math.factorial(k)

    @staticmethod
    def _decorate(ax: Any, title: str) -> None:
        ax.set_facecolor("#FDFEFE")
        ax.set_xlabel("Số phế phẩm k", fontsize=9, color="#555")
        ax.set_ylabel("Xác suất / Tần suất", fontsize=9, color="#555")
        ax.tick_params(labelsize=8, colors="#555")
        for spine in ax.spines.values():
            spine.set_edgecolor("#DDD")
        ax.grid(True, axis="y", linestyle="--", linewidth=0.5,
                color="#E0E0E0", alpha=0.7)
        ax.set_title(title, fontsize=11, fontweight="bold", pad=8,
                     bbox=dict(boxstyle="round,pad=0.3", fc="white",
                               ec="#BDBDBD", alpha=0.85))

    def render(self, engine: QCInspectionEngine) -> None:
        if not _MPL or self._ax_binom is None:  # pragma: no cover
            return
        assert self._ax_pois is not None
        assert self._figure is not None and self._canvas is not None

        n = engine.n_products
        p = engine.empirical_p
        mu = n * p
        m = engine.rounds_done
        freq = engine.frequency_table()

        if m == 0:  # pragma: no cover
            return

        # k range covering both distributions
        k_binom_max = n
        k_pois_max = max(k_binom_max,
                         int(mu + 4 * math.sqrt(mu) + 2) if mu > 0 else k_binom_max)
        k_binom = list(range(0, k_binom_max + 1))
        k_pois = list(range(0, k_pois_max + 1))

        # Empirical relative frequencies
        emp_binom = [freq.get(k, 0) / m for k in k_binom]
        emp_pois = [freq.get(k, 0) / m for k in k_pois]

        # Theoretical probabilities
        binom_probs = [self._binom_pmf(k, n, p) for k in k_binom]
        pois_probs = [self._poisson_pmf(k, mu) for k in k_pois]

        bw = 0.38  # bar half-width

        # ── Binomial ──────────────────────────────────────────────────────────
        ax_b = self._ax_binom
        ax_b.clear()
        ax_b.bar([x - bw / 2 for x in k_binom], binom_probs,
                 width=bw, color="#1976D2", alpha=0.78,
                 label=f"Bin(n={n}, p={p:.3f})")
        ax_b.bar([x + bw / 2 for x in k_binom], emp_binom,
                 width=bw, color="#FB8C00", alpha=0.78,
                 label="Thực tế")
        ax_b.set_xticks(k_binom)
        ax_b.legend(fontsize=8, framealpha=0.9, loc="upper right")
        self._decorate(ax_b, f"Phân phối Nhị thức\nBin(n={n},  p={p:.4f})")

        # ── Poisson ───────────────────────────────────────────────────────────
        ax_p = self._ax_pois
        ax_p.clear()
        ax_p.bar([x - bw / 2 for x in k_pois], pois_probs,
                 width=bw, color="#7B1FA2", alpha=0.78,
                 label=f"Po(μ={mu:.3f})")
        ax_p.bar([x + bw / 2 for x in k_pois], emp_pois,
                 width=bw, color="#FB8C00", alpha=0.78,
                 label="Thực tế")
        ax_p.set_xticks(k_pois)
        ax_p.legend(fontsize=8, framealpha=0.9, loc="upper right")
        self._decorate(ax_p, f"Phân phối Poisson\nPo(μ = n·p = {mu:.4f})")

        self._figure.tight_layout(pad=1.8)
        self._canvas.draw()


# ─── UI: Simulation view ──────────────────────────────────────────────────────


class _SimulationView(_WidgetBase):  # type: ignore[misc]
    """Full-page simulation analysis view."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Top bar ───────────────────────────────────────────────────────────
        top = QHBoxLayout()
        self._btn_back = QPushButton("← Quay lại")
        self._btn_back.setMinimumWidth(120)
        self._btn_back.setMinimumHeight(34)
        self._btn_back.setStyleSheet(
            "QPushButton { background:#546E7A; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 14px; }"
            "QPushButton:hover { background:#607D8B; }"
        )
        top.addWidget(self._btn_back)
        ttl = QLabel("📊  Mô phỏng Phân tích Chất lượng Sản phẩm")
        ttl.setStyleSheet("font-size: 18px; font-weight: bold; color: #37474F; margin-left:8px;")
        top.addWidget(ttl, stretch=1)
        root.addLayout(top)

        # ── Stats bar ─────────────────────────────────────────────────────────
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.Shape.StyledPanel)
        stats_frame.setStyleSheet(
            "QFrame { background:#E8F5E9; border-radius:6px; border:1px solid #C8E6C9; }")
        stats_row = QHBoxLayout(stats_frame)
        stats_row.setContentsMargins(14, 8, 14, 8)
        stats_row.setSpacing(0)

        self._lbl_total_sp = QLabel("—")
        self._lbl_total_pp = QLabel("—")
        self._lbl_rate = QLabel("—")
        self._lbl_n = QLabel("—")
        self._lbl_mu = QLabel("—")

        stat_style = ("font-size: 15px; font-weight: bold; color: #1B5E20;"
                      " padding: 0 16px; border-right: 1px solid #A5D6A7;")
        last_style = ("font-size: 15px; font-weight: bold; color: #1B5E20;"
                      " padding: 0 16px;")
        labels_data = [
            (self._lbl_total_sp, "Tổng sản phẩm: ", stat_style),
            (self._lbl_total_pp, "Tổng phế phẩm: ", stat_style),
            (self._lbl_rate,     "p = ",       stat_style),
            (self._lbl_n,        "n = ",        stat_style),
            (self._lbl_mu,       "μ = n·p = ",  last_style),
        ]
        for lbl, prefix, style in labels_data:
            pair = QHBoxLayout()
            pair.setSpacing(2)
            plbl = QLabel(prefix)
            plbl.setStyleSheet("font-size: 15px; color: #2E7D32; padding: 0 0 0 16px;")
            lbl.setStyleSheet(style)
            pair.addWidget(plbl)
            pair.addWidget(lbl)
            stats_row.addLayout(pair)
        stats_row.addStretch()
        root.addWidget(stats_frame)

        # ── Scrollable content ────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        c_layout = QVBoxLayout(content)
        c_layout.setSpacing(12)
        c_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(content)

        # Section 1: Frequency analysis
        freq_group = QGroupBox("Phân tích Tần số Phế phẩm")
        freq_group.setStyleSheet("QGroupBox { font-weight:bold; font-size:15px; }")
        freq_layout = QHBoxLayout(freq_group)
        freq_layout.setContentsMargins(8, 14, 8, 8)
        freq_layout.setSpacing(12)
        self._freq_table = _FreqTableWidget()
        freq_layout.addWidget(self._freq_table, stretch=0)
        self._freq_chart = _FreqChartCanvas()
        freq_layout.addWidget(self._freq_chart, stretch=1)
        c_layout.addWidget(freq_group)

        # Section 2: Distribution comparison
        dist_group = QGroupBox(
            "Đối chiếu Phân phối Lý thuyết — Nhị thức & Poisson"
        )
        dist_group.setStyleSheet("QGroupBox { font-weight:bold; font-size:15px; }")
        dist_layout = QVBoxLayout(dist_group)
        dist_layout.setContentsMargins(8, 14, 8, 8)
        self._dist_canvas = _DistributionCanvas()
        dist_layout.addWidget(self._dist_canvas)
        c_layout.addWidget(dist_group)

        c_layout.addStretch()
        root.addWidget(scroll, stretch=1)

    # ── Public API ────────────────────────────────────────────────────────────

    def connect_back(self, slot: Any) -> None:
        self._btn_back.clicked.connect(slot)

    def refresh(self, engine: QCInspectionEngine) -> None:
        n = engine.n_products
        tp = engine.total_products
        td = engine.total_defects
        p = engine.empirical_p
        mu = n * p

        self._lbl_total_sp.setText(str(tp))
        self._lbl_total_pp.setText(str(td))
        self._lbl_rate.setText(f"{p:.4f}")
        self._lbl_n.setText(str(n))
        self._lbl_mu.setText(f"{mu:.4f}")

        freq = engine.frequency_table()
        self._freq_table.populate(freq, engine.rounds_done)
        self._freq_chart.render(freq, engine.rounds_done)
        self._dist_canvas.render(engine)


# ─── UI: Config dialog ────────────────────────────────────────────────────────


class _ConfigDialog(_DialogBase):  # type: ignore[misc]
    """Modal dialog for editing QC inspection parameters."""

    def __init__(self, n_products: int, n_rounds: int, defect_rate: float,
                 parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cấu hình kiểm tra")
        self.setFixedWidth(370)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(14)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.spin_n_products = QSpinBox()
        self.spin_n_products.setRange(1, MAX_PRODUCTS)
        self.spin_n_products.setValue(n_products)
        self.spin_n_products.setSuffix(f"  (max {MAX_PRODUCTS})")
        self.spin_n_products.setMinimumWidth(170)
        self.spin_n_products.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        form.addRow("Số sản phẩm mỗi lần:", self.spin_n_products)

        self.spin_n_rounds = QSpinBox()
        self.spin_n_rounds.setRange(1, 9999)
        self.spin_n_rounds.setValue(n_rounds)
        self.spin_n_rounds.setSuffix("  lần")
        self.spin_n_rounds.setMinimumWidth(170)
        self.spin_n_rounds.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        form.addRow("Số lần kiểm tra:", self.spin_n_rounds)

        self.spin_defect_rate = QDoubleSpinBox()
        self.spin_defect_rate.setRange(0.01, 1.00)
        self.spin_defect_rate.setSingleStep(0.01)
        self.spin_defect_rate.setDecimals(2)
        self.spin_defect_rate.setValue(defect_rate)
        self.spin_defect_rate.setSuffix("  (1% – 100%)")
        self.spin_defect_rate.setMinimumWidth(170)
        self.spin_defect_rate.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        form.addRow("Tỷ lệ lỗi:", self.spin_defect_rate)

        layout.addLayout(form)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)

    @property
    def n_products(self) -> int:
        return self.spin_n_products.value()

    @property
    def n_rounds(self) -> int:
        return self.spin_n_rounds.value()

    @property
    def defect_rate(self) -> float:
        return self.spin_defect_rate.value()


# ─── UI: Inspection page ──────────────────────────────────────────────────────


class _InspectionPage(_WidgetBase):  # type: ignore[misc]
    """Main QC inspection page."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 10)
        root.setSpacing(10)

        # ── Header row ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("🏭  Kiểm tra Chất lượng Sản phẩm")
        title.setStyleSheet("font-size: 19px; font-weight: bold; color: #37474F;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._btn_simulate = QPushButton("📊  Mô phỏng →")
        self._btn_simulate.setMinimumWidth(145)
        self._btn_simulate.setMinimumHeight(36)
        self._btn_simulate.setEnabled(False)
        self._btn_simulate.setToolTip(
            "Hoàn thành đủ số lần kiểm tra để mở khóa mô phỏng")
        self._btn_simulate.setStyleSheet(
            "QPushButton { background:#1565C0; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 16px; }"
            "QPushButton:hover { background:#1976D2; }"
            "QPushButton:disabled { background:#B0BEC5; color:#777; }"
        )
        hdr.addWidget(self._btn_simulate)
        root.addLayout(hdr)

        # ── Description ───────────────────────────────────────────────────────
        desc = QLabel(
            "Dây chuyền sản xuất đang hoạt động. Bạn là nhân viên QC (Quality Control) "
            "và đang kiểm tra sản phẩm trên băng chuyền để phân loại "
            "(thành phẩm hoặc phế phẩm) và ghi nhận lại. Các sản phẩm đang di chuyển tới..."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #546E7A; font-size: 14px; font-style: italic;")
        root.addWidget(desc)

        # ── Controls ──────────────────────────────────────────────────────────
        ctrl_box = QGroupBox()
        ctrl_box.setStyleSheet("QGroupBox { border: none; }")
        ctrl_row = QHBoxLayout(ctrl_box)
        ctrl_row.setContentsMargins(0, 4, 0, 4)
        ctrl_row.setSpacing(12)

        # Config values (stored internally, edited via _ConfigDialog)
        self._cfg_n_products: int = DEFAULT_N_PRODUCTS
        self._cfg_n_rounds: int = DEFAULT_N_ROUNDS
        self._cfg_defect_rate: float = _DEFECT_PROB

        self._btn_config = QPushButton("⚙  Cấu hình")
        self._btn_config.setMinimumWidth(120)
        self._btn_config.setMinimumHeight(36)
        self._btn_config.setStyleSheet(
            "QPushButton { background:#455A64; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 14px; }"
            "QPushButton:hover { background:#546E7A; }"
            "QPushButton:disabled { background:#B0BEC5; color:#777; }"
        )
        self._btn_config.clicked.connect(self._open_config_dialog)
        ctrl_row.addWidget(self._btn_config)

        self._lbl_config_summary = QLabel()
        self._lbl_config_summary.setStyleSheet(
            "color: #546E7A; font-size: 13px; font-style: italic;")
        ctrl_row.addWidget(self._lbl_config_summary)
        self._update_config_summary()

        ctrl_row.addSpacing(16)

        self._btn_manual = QPushButton("🔍  QC Thủ công")
        self._btn_manual.setMinimumWidth(145)
        self._btn_manual.setMinimumHeight(36)
        self._btn_manual.setStyleSheet(
            "QPushButton { background:#37474F; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 14px; }"
            "QPushButton:hover { background:#455A64; }"
            "QPushButton:disabled { background:#B0BEC5; color:#777; }"
        )
        ctrl_row.addWidget(self._btn_manual)

        self._btn_auto = QPushButton("⚡  QC Tự động")
        self._btn_auto.setMinimumWidth(145)
        self._btn_auto.setMinimumHeight(36)
        self._btn_auto.setStyleSheet(
            "QPushButton { background:#E65100; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 14px; }"
            "QPushButton:hover { background:#F4511E; }"
            "QPushButton:disabled { background:#B0BEC5; color:#777; }"
        )
        ctrl_row.addWidget(self._btn_auto)

        self._btn_reset = QPushButton("↺  Đặt lại")
        self._btn_reset.setMinimumHeight(36)
        self._btn_reset.setStyleSheet(
            "QPushButton { background:#78909C; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 12px; }"
            "QPushButton:hover { background:#90A4AE; }"
        )
        ctrl_row.addWidget(self._btn_reset)

        ctrl_row.addStretch()
        self._lbl_status = QLabel("Sẵn sàng")
        self._lbl_status.setStyleSheet(
            "color: #2E7D32; font-size: 14px; font-weight: bold;")
        ctrl_row.addWidget(self._lbl_status)

        root.addWidget(ctrl_box)

        # ── Product inspection frame ──────────────────────────────────────────
        insp_box = QGroupBox("Kiểm tra sản phẩm")
        insp_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        insp_layout = QVBoxLayout(insp_box)
        insp_layout.setContentsMargins(6, 10, 6, 6)
        self._grid_frame = _ProductGridFrame()
        insp_layout.addWidget(self._grid_frame)
        root.addWidget(insp_box)

        # ── Records table ─────────────────────────────────────────────────────
        rec_box = QGroupBox("Kết quả ghi nhận")
        rec_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        rec_layout = QVBoxLayout(rec_box)
        rec_layout.setContentsMargins(6, 10, 6, 6)
        self._records_table = _RecordsTable()
        rec_layout.addWidget(self._records_table)
        root.addWidget(rec_box, stretch=1)

    # ── Connections ───────────────────────────────────────────────────────────

    def connect_simulate(self, slot: Any) -> None:
        self._btn_simulate.clicked.connect(slot)

    def connect_manual(self, slot: Any) -> None:
        self._btn_manual.clicked.connect(slot)

    def connect_auto(self, slot: Any) -> None:
        self._btn_auto.clicked.connect(slot)

    def connect_reset(self, slot: Any) -> None:
        self._btn_reset.clicked.connect(slot)

    def connect_record(self, slot: Any) -> None:
        self._grid_frame.connect_record(slot)

    # ── State control ─────────────────────────────────────────────────────────

    def set_simulate_enabled(self, enabled: bool) -> None:
        self._btn_simulate.setEnabled(enabled)

    def set_manual_enabled(self, enabled: bool) -> None:
        self._btn_manual.setEnabled(enabled)

    def set_auto_enabled(self, enabled: bool) -> None:
        self._btn_auto.setEnabled(enabled)

    def lock_config(self) -> None:
        """Lock config button after first use."""
        self._btn_config.setEnabled(False)

    def unlock_config(self) -> None:
        self._btn_config.setEnabled(True)

    def update_status(self, msg: str, ok: bool = True) -> None:
        color = "#2E7D32" if ok else "#C62828"
        self._lbl_status.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold;")
        self._lbl_status.setText(msg)

    def get_n_products(self) -> int:
        return self._cfg_n_products

    def get_n_rounds(self) -> int:
        return self._cfg_n_rounds

    def get_defect_rate(self) -> float:
        return self._cfg_defect_rate

    def sync_spinners(self, n_products: int, n_rounds: int,
                      defect_rate: float = _DEFECT_PROB) -> None:
        self._cfg_n_products = n_products
        self._cfg_n_rounds = n_rounds
        self._cfg_defect_rate = defect_rate
        self._update_config_summary()

    def _open_config_dialog(self) -> None:
        """Open config dialog and apply changes on accept."""
        dlg = _ConfigDialog(
            self._cfg_n_products, self._cfg_n_rounds,
            self._cfg_defect_rate, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cfg_n_products = dlg.n_products
            self._cfg_n_rounds = dlg.n_rounds
            self._cfg_defect_rate = dlg.defect_rate
            self._update_config_summary()

    def _update_config_summary(self) -> None:
        self._lbl_config_summary.setText(
            f"{self._cfg_n_products} SP \u00d7 {self._cfg_n_rounds} l\u1ea7n, "
            f"p = {self._cfg_defect_rate:.2f}")


# ─── Module ───────────────────────────────────────────────────────────────────


class QCInspectionModule(BaseModule):
    """IIMP module — QC Kiểm tra Chất lượng v1.0.0.

    Simulates a quality-control inspection station on a production line:
    - Manual QC: user inspects products and marks defectives
    - Auto QC: simulation auto-fills all remaining rounds
    - Simulation mode: frequency analysis and distribution comparison
    """

    MODULE_ID = "qc_inspection"
    MODULE_NAME = "QC Kiểm tra Chất lượng"
    MODULE_VERSION = "1.0.0"

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def module_id(self) -> str:
        return self.MODULE_ID

    @property
    def module_name(self) -> str:
        return self.MODULE_NAME

    @property
    def module_version(self) -> str:
        return self.MODULE_VERSION

    # ── Init ──────────────────────────────────────────────────────────────────

    def __init__(self, manifest: dict, context: Any) -> None:
        super().__init__(manifest=manifest, context=context)
        self._engine = QCInspectionEngine()
        self._widget: Any = None
        self._stack: Any = None
        self._insp_page: Any = None
        self._sim_view: Any = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        saved = self.context.settings_service.get_module_setting(
            self.MODULE_ID, "state"
        )
        if saved and isinstance(saved, dict):
            try:
                self._engine.restore_state(saved)
            except Exception:
                pass  # fallback to default state on corrupted data

    def on_activate(self) -> None:
        if self._insp_page is not None:
            self._refresh_page()

    def on_deactivate(self) -> None:
        self._persist_state()

    def on_unload(self) -> None:
        self._persist_state()

    def get_state(self) -> dict[str, Any]:
        return {"engine": self._engine.get_state()}

    def restore_state(self, state: dict[str, Any]) -> None:
        if "engine" in state:
            try:
                self._engine.restore_state(state["engine"])
            except Exception:
                pass

    def _persist_state(self) -> None:
        self.context.settings_service.set_module_setting(
            self.MODULE_ID, "state", self._engine.get_state()
        )

    # ── View ──────────────────────────────────────────────────────────────────

    def build_view(self) -> Any:
        if not _QT:  # pragma: no cover
            return None

        root = QWidget()
        root.setObjectName("qc_inspection_root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        stack = QStackedWidget()
        self._stack = stack

        # Page 0 — inspection
        insp_page = _InspectionPage()
        self._insp_page = insp_page
        insp_page.connect_manual(self._on_manual_qc)
        insp_page.connect_auto(self._on_auto_qc)
        insp_page.connect_reset(self._on_reset)
        insp_page.connect_record(self._on_record)
        insp_page.connect_simulate(self._on_show_simulation)
        stack.addWidget(insp_page)

        # Page 1 — simulation
        sim_view = _SimulationView()
        self._sim_view = sim_view
        sim_view.connect_back(self._on_back)
        stack.addWidget(sim_view)

        layout.addWidget(stack)
        self._widget = root

        # Sync UI state from (possibly restored) engine
        self._refresh_page()
        return root

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_manual_qc(self) -> None:
        """Load next round of products for manual inspection."""
        if self._insp_page is None:  # pragma: no cover
            return
        if self._engine.rounds_done == 0:
            self._engine.configure(
                self._insp_page.get_n_products(),
                self._insp_page.get_n_rounds(),
                self._insp_page.get_defect_rate(),
            )
            self._insp_page.lock_config()

        if self._engine.is_complete:
            return

        products = self._engine.generate_round()
        round_no = self._engine.rounds_done + 1
        self._insp_page._grid_frame.load_products(
            products, round_no, self._engine.n_rounds
        )
        self._insp_page.set_manual_enabled(False)
        self._insp_page.set_auto_enabled(False)
        self._insp_page.update_status(
            f"Lần {round_no}/{self._engine.n_rounds} — Đánh dấu phế phẩm → Ghi nhận"
        )

    def _on_auto_qc(self) -> None:
        """Auto-fill all remaining rounds."""
        if self._insp_page is None:  # pragma: no cover
            return
        if self._engine.rounds_done == 0:
            self._engine.configure(
                self._insp_page.get_n_products(),
                self._insp_page.get_n_rounds(),
                self._insp_page.get_defect_rate(),
            )
            self._insp_page.lock_config()

        new_recs = self._engine.auto_complete()
        for rec in new_recs:
            self._insp_page._records_table.add_record(rec)

        self._insp_page._grid_frame.clear("QC tự động hoàn tất.")
        self._refresh_page()

    def _on_record(self) -> None:
        """Commit the current manual inspection round."""
        if self._insp_page is None:  # pragma: no cover
            return
        if not self._engine.is_pending_record:
            return

        marked = self._insp_page._grid_frame.get_marked_indices()
        rec = self._engine.record_manual(marked)
        self._insp_page._records_table.add_record(rec)

        if self._engine.is_complete:
            self._insp_page._grid_frame.clear(
                "Hoàn thành! Nhấn  'Mô phỏng →'  để phân tích thống kê.")
            self._refresh_page()
        else:
            remaining = self._engine.n_rounds - self._engine.rounds_done
            self._insp_page._grid_frame.clear(
                f"Đã ghi nhận lần {rec.round_no}. Còn {remaining} lần nữa."
            )
            self._insp_page.set_manual_enabled(True)
            self._insp_page.set_auto_enabled(True)
            self._insp_page.update_status(
                f"Đã kiểm tra {self._engine.rounds_done}/{self._engine.n_rounds} lần"
            )

    def _on_reset(self) -> None:
        """Reset all records and return to initial state."""
        if self._insp_page is None:  # pragma: no cover
            return
        self._engine.reset()
        self._insp_page._records_table.populate([])
        self._insp_page._grid_frame.clear()
        self._insp_page.unlock_config()
        self._refresh_page()

    def _on_show_simulation(self) -> None:
        """Switch to simulation view."""
        if not self._engine.is_complete:
            return
        if self._sim_view is not None:
            self._sim_view.refresh(self._engine)
        if self._stack is not None:
            self._stack.setCurrentIndex(1)

    def _on_back(self) -> None:
        """Return to inspection page."""
        if self._stack is not None:
            self._stack.setCurrentIndex(0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _refresh_page(self) -> None:
        """Sync inspection page button states from engine."""
        if self._insp_page is None:  # pragma: no cover
            return

        complete = self._engine.is_complete
        pending = self._engine.is_pending_record
        done = self._engine.rounds_done
        total = self._engine.n_rounds

        self._insp_page.set_simulate_enabled(complete)
        self._insp_page.set_manual_enabled(not complete and not pending)
        self._insp_page.set_auto_enabled(not complete and not pending)

        if complete:
            self._insp_page.update_status(
                f"✔ Hoàn thành {done}/{total} lần — Sẵn sàng mô phỏng!")
        elif done > 0:
            self._insp_page.update_status(
                f"Đã kiểm tra {done}/{total} lần")
            self._insp_page.lock_config()
        else:
            self._insp_page.update_status("Sẵn sàng")
            self._insp_page.unlock_config()

        # Sync spinners and repopulate records from engine
        self._insp_page.sync_spinners(
            self._engine.n_products, self._engine.n_rounds, self._engine.defect_prob)
        self._insp_page._records_table.populate(self._engine.records)
