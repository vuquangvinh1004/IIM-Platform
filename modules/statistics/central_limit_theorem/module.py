"""Central Limit Theorem — Mô phỏng Định lý Giới hạn Trung tâm v1.0.0

Bối cảnh: cân trọng lượng sản phẩm trên dây chuyền sản xuất.

  Giao diện thu thập dữ liệu:
    - Cài đặt: cỡ mẫu n, số mẫu m, trung bình & độ lệch chuẩn quần thể (μ_pop, σ_pop),
      trung bình & độ lệch chuẩn phân phối chuẩn đối chiếu (μ_norm, σ_norm)
    - Cân thủ công: sản phẩm xuất hiện → kéo-đặt lên cân → Ghi nhận
    - Cân tự động: tự sinh dữ liệu cho toàn bộ mẫu còn lại
    - Bảng kết quả: Mẫu | n | x̄ | s

  Giao diện mô phỏng (sau khi hoàn thành):
    - Thống kê tổng hợp
    - Histogram phân phối trung bình mẫu
    - Đối chiếu phân phối Student t(n-1) và phân phối chuẩn N(μ_norm, σ_norm)
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from typing import Any

try:
    from PySide6.QtCore import Qt, QMimeData, QPointF, QRectF, QSize
    from PySide6.QtGui import (
        QBrush, QColor, QDrag, QFont, QPainter, QPainterPath, QPen,
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

MAX_SAMPLE_SIZE: int = 100      # max n (products per sample)
MAX_SAMPLES: int = 10000        # max m (number of samples)
DEFAULT_SAMPLE_SIZE: int = 5    # default n
DEFAULT_NUM_SAMPLES: int = 30   # default m
DEFAULT_POP_MEAN: float = 500.0     # μ population (grams)
DEFAULT_POP_STD: float = 20.0      # σ population (grams)
DEFAULT_NORM_MEAN: float = 500.0    # μ for comparison normal dist
DEFAULT_NORM_STD: float = 20.0      # σ for comparison normal dist


# ─── Pure-Python Engine ───────────────────────────────────────────────────────


@dataclass
class SampleRecord:
    """Result of weighing one sample of n products."""
    sample_no: int
    weights: list[float]

    @property
    def n(self) -> int:
        return len(self.weights)

    @property
    def mean(self) -> float:
        return sum(self.weights) / len(self.weights) if self.weights else 0.0

    @property
    def std(self) -> float:
        if len(self.weights) < 2:
            return 0.0
        m = self.mean
        return math.sqrt(sum((w - m) ** 2 for w in self.weights) / (len(self.weights) - 1))


class CLTEngine:
    """Stateful CLT simulation engine — pure Python, fully testable without Qt."""

    def __init__(self) -> None:
        self.sample_size: int = DEFAULT_SAMPLE_SIZE
        self.num_samples: int = DEFAULT_NUM_SAMPLES
        self.pop_mean: float = DEFAULT_POP_MEAN
        self.pop_std: float = DEFAULT_POP_STD
        self.norm_mean: float = DEFAULT_NORM_MEAN
        self.norm_std: float = DEFAULT_NORM_STD
        self.records: list[SampleRecord] = []
        self.current_weights: list[float] = []   # weights generated but not yet recorded
        self._products_generated: int = 0         # how many products generated this round
        self._round_pending: bool = False

    # ── Configuration ─────────────────────────────────────────────────────────

    def configure(
        self, sample_size: int, num_samples: int,
        pop_mean: float, pop_std: float,
        norm_mean: float, norm_std: float,
    ) -> None:
        self.sample_size = max(2, min(MAX_SAMPLE_SIZE, sample_size))
        self.num_samples = max(1, min(MAX_SAMPLES, num_samples))
        self.pop_mean = pop_mean
        self.pop_std = max(0.01, pop_std)
        self.norm_mean = norm_mean
        self.norm_std = max(0.01, norm_std)

    # ── Manual weighing API ───────────────────────────────────────────────────

    def generate_product(self) -> float:
        """Generate a single product weight for manual weighing.

        Returns the weight. The product is NOT recorded yet —
        user must call record_weight() after placing on scale.
        """
        weight = random.gauss(self.pop_mean, self.pop_std)
        weight = max(0.01, weight)  # physical weight cannot be ≤ 0
        self._products_generated += 1
        self._round_pending = True
        return weight

    def record_weight(self, weight: float) -> None:
        """Record a single weight after user places product on scale."""
        self.current_weights.append(weight)

    def finish_sample(self) -> SampleRecord:
        """Finish current sample — commit all recorded weights."""
        rec = SampleRecord(
            sample_no=len(self.records) + 1,
            weights=list(self.current_weights),
        )
        self.records.append(rec)
        self.current_weights = []
        self._products_generated = 0
        self._round_pending = False
        return rec

    @property
    def products_weighed_this_round(self) -> int:
        return len(self.current_weights)

    @property
    def products_remaining_this_round(self) -> int:
        return self.sample_size - len(self.current_weights)

    # ── Auto weighing API ─────────────────────────────────────────────────────

    def auto_complete(self) -> list[SampleRecord]:
        """Auto-generate and record all remaining samples."""
        new_records: list[SampleRecord] = []
        remaining = self.num_samples - len(self.records)
        for _ in range(remaining):
            weights = [max(0.01, random.gauss(self.pop_mean, self.pop_std))
                       for _ in range(self.sample_size)]
            rec = SampleRecord(
                sample_no=len(self.records) + 1,
                weights=weights,
            )
            self.records.append(rec)
            new_records.append(rec)
        self.current_weights = []
        self._products_generated = 0
        self._round_pending = False
        return new_records

    def reset(self) -> None:
        self.records.clear()
        self.current_weights = []
        self._products_generated = 0
        self._round_pending = False

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def samples_done(self) -> int:
        return len(self.records)

    @property
    def is_complete(self) -> bool:
        return len(self.records) >= self.num_samples

    @property
    def is_pending(self) -> bool:
        return self._round_pending and len(self.current_weights) < self.sample_size

    @property
    def sample_means(self) -> list[float]:
        return [r.mean for r in self.records]

    @property
    def grand_mean(self) -> float:
        means = self.sample_means
        return sum(means) / len(means) if means else 0.0

    @property
    def std_of_means(self) -> float:
        means = self.sample_means
        if len(means) < 2:
            return 0.0
        gm = self.grand_mean
        return math.sqrt(sum((m - gm) ** 2 for m in means) / (len(means) - 1))

    # ── Persistence ───────────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "state_version": "1.0.0",
            "sample_size": self.sample_size,
            "num_samples": self.num_samples,
            "pop_mean": self.pop_mean,
            "pop_std": self.pop_std,
            "norm_mean": self.norm_mean,
            "norm_std": self.norm_std,
            "records": [
                {"sample_no": r.sample_no, "weights": r.weights}
                for r in self.records
            ],
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.sample_size = int(state.get("sample_size", DEFAULT_SAMPLE_SIZE))
        self.num_samples = int(state.get("num_samples", DEFAULT_NUM_SAMPLES))
        self.pop_mean = float(state.get("pop_mean", DEFAULT_POP_MEAN))
        self.pop_std = float(state.get("pop_std", DEFAULT_POP_STD))
        self.norm_mean = float(state.get("norm_mean", DEFAULT_NORM_MEAN))
        self.norm_std = float(state.get("norm_std", DEFAULT_NORM_STD))
        self.records = [
            SampleRecord(r["sample_no"], r["weights"])
            for r in state.get("records", [])
        ]
        self.current_weights = []
        self._products_generated = 0
        self._round_pending = False


# ─── UI: Product on conveyor belt (draggable) ─────────────────────────────────


class _ConveyorProduct(_WidgetBase):  # type: ignore[misc]
    """Draggable product widget — isometric 3D-styled box."""

    SIZE: int = 72

    def __init__(self, product_id: int, weight: float,
                 parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self.product_id = product_id
        self.weight = weight
        self.is_placed: bool = False
        self.setFixedSize(self.SIZE, self.SIZE)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip(f"Sản phẩm #{product_id + 1}\nKéo vào cân để đo")

    def mousePressEvent(self, event: Any) -> None:  # noqa: N802
        if not _QT or self.is_placed:  # pragma: no cover
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseReleaseEvent(self, event: Any) -> None:  # noqa: N802
        if not _QT or self.is_placed:  # pragma: no cover
            return
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseMoveEvent(self, event: Any) -> None:  # noqa: N802
        if not _QT or self.is_placed:  # pragma: no cover
            return
        drag = QDrag(self)
        mime = QMimeData()
        mime.setText(str(self.product_id))
        drag.setMimeData(mime)
        drag.exec(Qt.DropAction.MoveAction)

    def mark_placed(self) -> None:
        self.is_placed = True
        self.setCursor(Qt.CursorShape.ForbiddenCursor)
        self.setToolTip(f"SP #{self.product_id + 1} — Đã cân: {self.weight:.2f}g")
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        if not _QT:  # pragma: no cover
            return
        pa = QPainter(self)
        pa.setRenderHint(QPainter.RenderHint.Antialiasing)

        # ── Isometric box keypoints ───────────────────────────────────────
        TC = QPointF(36,  4)
        ML = QPointF( 4, 20)
        MC = QPointF(36, 36)
        MR = QPointF(68, 20)
        BL = QPointF( 4, 52)
        BC = QPointF(36, 68)
        BR = QPointF(68, 52)

        # ── Face colours ─────────────────────────────────────────────────
        if self.is_placed:
            c_top = QColor("#A5D6A7")
            c_left = QColor("#81C784")
            c_rght = QColor("#66BB6A")
        else:
            c_top = QColor("#DEB887")
            c_left = QColor("#C49A5B")
            c_rght = QColor("#A07848")

        edge = QPen(QColor(0, 0, 0, 55), 0.8)

        def _face(pts: list) -> QPainterPath:
            pp = QPainterPath()
            pp.moveTo(pts[0])
            for pt in pts[1:]:
                pp.lineTo(pt)
            pp.closeSubpath()
            return pp

        pa.fillPath(_face([TC, MR, MC, ML]), QBrush(c_top))
        pa.setPen(edge)
        pa.drawPath(_face([TC, MR, MC, ML]))

        pa.fillPath(_face([ML, MC, BC, BL]), QBrush(c_left))
        pa.setPen(edge)
        pa.drawPath(_face([ML, MC, BC, BL]))

        pa.fillPath(_face([MC, MR, BR, BC]), QBrush(c_rght))
        pa.setPen(edge)
        pa.drawPath(_face([MC, MR, BR, BC]))

        # ── Tape stripes ─────────────────────────────────────────────────
        tape = QPen(QColor("#8B6914"), 2.2, Qt.PenStyle.SolidLine,
                    Qt.PenCapStyle.FlatCap)
        pa.setPen(tape)
        pa.drawLine(TC, MC)
        pa.drawLine(MC, BC)
        pa.drawLine(QPointF(20, 12), QPointF(52, 12))

        # ── Product number ────────────────────────────────────────────────
        pa.setPen(QPen(QColor(60, 38, 4, 210)))
        fnt = QFont()
        fnt.setPointSize(8)
        fnt.setBold(True)
        pa.setFont(fnt)
        pa.drawText(QRectF(18, 8, 36, 16),
                    Qt.AlignmentFlag.AlignCenter, str(self.product_id + 1))

        # ── Placed checkmark ─────────────────────────────────────────────
        if self.is_placed:
            bx, by, br = self.SIZE - 13, self.SIZE - 13, 10
            badge_pp = QPainterPath()
            badge_pp.addEllipse(bx - br, by - br, br * 2, br * 2)
            pa.fillPath(badge_pp, QBrush(QColor("#2E7D32")))
            pa.setPen(QPen(QColor("white"), 2.0, Qt.PenStyle.SolidLine,
                           Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            off = 5
            pa.drawLine(QPointF(bx - off + 1, by + 1), QPointF(bx - 1, by + 4))
            pa.drawLine(QPointF(bx - 1, by + 4), QPointF(bx + off, by - 3))

        pa.end()


# ─── UI: Scale (drop target) ──────────────────────────────────────────────────


class _ScaleWidget(_WidgetBase):  # type: ignore[misc]
    """Drop target — digital scale that displays weight on drop."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setMinimumSize(200, 140)
        self.setMaximumSize(260, 180)
        self._weight: float | None = None
        self._on_drop_callback: Any = None

    def set_on_drop(self, callback: Any) -> None:
        self._on_drop_callback = callback

    def display_weight(self, weight: float) -> None:
        self._weight = weight
        self.update()

    def clear_display(self) -> None:
        self._weight = None
        self.update()

    def dragEnterEvent(self, event: Any) -> None:  # noqa: N802
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event: Any) -> None:  # noqa: N802
        product_id_str = event.mimeData().text()
        try:
            product_id = int(product_id_str)
        except (ValueError, TypeError):
            return
        event.acceptProposedAction()
        if self._on_drop_callback:
            self._on_drop_callback(product_id)

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        if not _QT:  # pragma: no cover
            return
        pa = QPainter(self)
        pa.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # ── Scale platform ────────────────────────────────────────────────
        platform = QPainterPath()
        platform.addRoundedRect(10, h * 0.45, w - 20, h * 0.5, 10, 10)
        pa.fillPath(platform, QBrush(QColor("#B0BEC5")))
        pa.setPen(QPen(QColor("#78909C"), 1.5))
        pa.drawPath(platform)

        # ── Top surface ──────────────────────────────────────────────────
        top = QPainterPath()
        top.addRoundedRect(20, h * 0.35, w - 40, h * 0.18, 6, 6)
        pa.fillPath(top, QBrush(QColor("#CFD8DC")))
        pa.setPen(QPen(QColor("#90A4AE"), 1))
        pa.drawPath(top)

        # ── Display screen ───────────────────────────────────────────────
        screen_rect = QRectF(w * 0.2, h * 0.58, w * 0.6, h * 0.22)
        screen = QPainterPath()
        screen.addRoundedRect(screen_rect, 4, 4)
        pa.fillPath(screen, QBrush(QColor("#263238")))
        pa.setPen(QPen(QColor("#37474F"), 1))
        pa.drawPath(screen)

        # ── Weight text ──────────────────────────────────────────────────
        fnt = QFont("Consolas", 14)
        fnt.setBold(True)
        pa.setFont(fnt)
        pa.setPen(QPen(QColor("#76FF03")))
        if self._weight is not None:
            txt = f"{self._weight:.2f} g"
        else:
            txt = "--- g"
        pa.drawText(screen_rect, Qt.AlignmentFlag.AlignCenter, txt)

        # ── Label ─────────────────────────────────────────────────────────
        fnt2 = QFont()
        fnt2.setPointSize(8)
        pa.setFont(fnt2)
        pa.setPen(QPen(QColor("#546E7A")))
        pa.drawText(QRectF(0, h * 0.85, w, 16),
                    Qt.AlignmentFlag.AlignCenter, "CÂN ĐIỆN TỬ")

        pa.end()


# ─── UI: Weighing frame (conveyor + scale) ────────────────────────────────────


class _WeighingFrame(_WidgetBase):  # type: ignore[misc]
    """Conveyor belt products + scale + record button."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(8)

        # Progress label
        self._lbl_progress = QLabel("Nhấn 'Cân thủ công' để bắt đầu")
        self._lbl_progress.setStyleSheet(
            "color: #607D8B; font-style: italic; font-size: 14px;")
        outer.addWidget(self._lbl_progress)

        # Main area: products grid | scale
        main_row = QHBoxLayout()
        main_row.setSpacing(12)

        # Product grid on left
        self._grid_container = QWidget()
        self._grid_layout = QGridLayout(self._grid_container)
        self._grid_layout.setSpacing(6)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        self._grid_layout.setAlignment(
            Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        main_row.addWidget(self._grid_container, stretch=1)

        # Scale on right
        self._scale = _ScaleWidget()
        self._scale.set_on_drop(self._on_product_dropped)
        scale_container = QVBoxLayout()
        scale_container.addStretch()
        scale_container.addWidget(self._scale, alignment=Qt.AlignmentFlag.AlignCenter)
        scale_container.addStretch()
        main_row.addLayout(scale_container)

        outer.addLayout(main_row, stretch=1)

        # Weight display + record button row
        bottom = QHBoxLayout()
        self._lbl_weight = QLabel("")
        self._lbl_weight.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #1565C0;")
        bottom.addWidget(self._lbl_weight)
        bottom.addStretch()

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
        bottom.addWidget(self._btn_record)

        self._btn_finish = QPushButton("⏎  Hoàn thành mẫu")
        self._btn_finish.setMinimumWidth(150)
        self._btn_finish.setMinimumHeight(34)
        self._btn_finish.setEnabled(False)
        self._btn_finish.setStyleSheet(
            "QPushButton { background:#1565C0; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 16px; }"
            "QPushButton:hover { background:#1976D2; }"
            "QPushButton:disabled { background:#B0BEC5; color:#777; }"
        )
        bottom.addWidget(self._btn_finish)

        outer.addLayout(bottom)

        self._product_widgets: list[_ConveyorProduct] = []
        self._current_product_id: int | None = None
        self._current_weight: float | None = None
        self._on_record_callback: Any = None
        self._on_finish_callback: Any = None

        self._btn_record.clicked.connect(self._on_record_clicked)
        self._btn_finish.clicked.connect(self._on_finish_clicked)

    # ── Public interface ──────────────────────────────────────────────────────

    def load_products(self, weights: list[float], sample_no: int,
                      num_samples: int) -> None:
        """Populate the conveyor with products for this sample."""
        self._clear_grid()
        tile = _ConveyorProduct.SIZE + self._grid_layout.spacing()
        avail = self._grid_container.width() - 8
        cols = max(1, avail // tile) if avail >= tile else max(1, len(weights))
        for idx, weight in enumerate(weights):
            w = _ConveyorProduct(idx, weight, self._grid_container)
            self._grid_layout.addWidget(w, idx // cols, idx % cols)
            self._product_widgets.append(w)
        self._lbl_progress.setText(
            f"Mẫu {sample_no}/{num_samples} — Kéo sản phẩm vào cân → Ghi nhận"
        )
        self._btn_record.setEnabled(False)
        self._btn_finish.setEnabled(False)
        self._scale.clear_display()
        self._current_product_id = None
        self._current_weight = None
        self._lbl_weight.setText("")

    def clear(self, message: str = "Nhấn 'Cân thủ công' để bắt đầu") -> None:
        self._clear_grid()
        self._lbl_progress.setText(message)
        self._btn_record.setEnabled(False)
        self._btn_finish.setEnabled(False)
        self._scale.clear_display()
        self._current_product_id = None
        self._current_weight = None
        self._lbl_weight.setText("")

    def set_record_callback(self, callback: Any) -> None:
        self._on_record_callback = callback

    def set_finish_callback(self, callback: Any) -> None:
        self._on_finish_callback = callback

    def update_progress(self, weighed: int, total: int,
                        sample_no: int, num_samples: int) -> None:
        self._lbl_progress.setText(
            f"Mẫu {sample_no}/{num_samples} — "
            f"Đã cân {weighed}/{total} sản phẩm"
        )
        # Enable finish only when all products weighed
        self._btn_finish.setEnabled(weighed >= total)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_product_dropped(self, product_id: int) -> None:
        """Called when a product is dropped on the scale."""
        if product_id < 0 or product_id >= len(self._product_widgets):
            return
        pw = self._product_widgets[product_id]
        if pw.is_placed:
            return  # already weighed
        self._current_product_id = product_id
        self._current_weight = pw.weight
        self._scale.display_weight(pw.weight)
        self._lbl_weight.setText(
            f"SP #{product_id + 1}: {pw.weight:.2f} g")
        self._btn_record.setEnabled(True)

    def _on_record_clicked(self) -> None:
        if self._current_product_id is None or self._current_weight is None:
            return
        pw = self._product_widgets[self._current_product_id]
        pw.mark_placed()
        if self._on_record_callback:
            self._on_record_callback(self._current_weight)
        self._current_product_id = None
        self._current_weight = None
        self._btn_record.setEnabled(False)
        self._scale.clear_display()
        self._lbl_weight.setText("")

    def _on_finish_clicked(self) -> None:
        if self._on_finish_callback:
            self._on_finish_callback()

    def _clear_grid(self) -> None:
        for w in self._product_widgets:
            self._grid_layout.removeWidget(w)
            w.setParent(None)  # type: ignore[call-arg]
            w.deleteLater()
        self._product_widgets.clear()


# ─── UI: Records table ────────────────────────────────────────────────────────


class _SampleRecordsTable(_WidgetBase):  # type: ignore[misc]
    """Read-only table: Mẫu | n | x̄ | s."""

    _HEADERS = ["Mẫu", "Cỡ mẫu (n)", "Trung bình (x\u0304)", "Độ lệch chuẩn (s)"]

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
        hdr.setStretchLastSection(False)
        for col in (0, 1):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        for col in (2, 3):
            hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self._table)

    def add_record(self, rec: SampleRecord) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        self._set_cell(row, 0, str(rec.sample_no))
        self._set_cell(row, 1, str(rec.n))
        self._set_cell(row, 2, f"{rec.mean:.4f}")
        self._set_cell(row, 3, f"{rec.std:.4f}")
        self._table.scrollToBottom()

    def add_records_batch(self, records: list[SampleRecord]) -> None:
        """Add many records efficiently with UI updates suspended."""
        self._table.setUpdatesEnabled(False)
        try:
            start = self._table.rowCount()
            self._table.setRowCount(start + len(records))
            for i, rec in enumerate(records):
                row = start + i
                self._set_cell(row, 0, str(rec.sample_no))
                self._set_cell(row, 1, str(rec.n))
                self._set_cell(row, 2, f"{rec.mean:.4f}")
                self._set_cell(row, 3, f"{rec.std:.4f}")
        finally:
            self._table.setUpdatesEnabled(True)
        self._table.scrollToBottom()

    def populate(self, records: list[SampleRecord]) -> None:
        self._table.setUpdatesEnabled(False)
        try:
            self._table.setRowCount(len(records))
            for i, rec in enumerate(records):
                self._set_cell(i, 0, str(rec.sample_no))
                self._set_cell(i, 1, str(rec.n))
                self._set_cell(i, 2, f"{rec.mean:.4f}")
                self._set_cell(i, 3, f"{rec.std:.4f}")
        finally:
            self._table.setUpdatesEnabled(True)

    def _set_cell(self, row: int, col: int, text: str) -> None:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, col, item)


# ─── UI: Distribution chart (simulation view) ─────────────────────────────────


class _CLTDistributionCanvas(_WidgetBase):  # type: ignore[misc]
    """Two side-by-side charts: histogram vs Student-t | histogram vs Normal."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._figure = Figure(figsize=(12, 5), dpi=100)
            self._figure.patch.set_facecolor("#F8F9FA")
            self._ax_left, self._ax_right = self._figure.subplots(1, 2)
            self._canvas = FigureCanvas(self._figure)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self._canvas)
        else:  # pragma: no cover
            layout.addWidget(QLabel("(matplotlib không khả dụng)"))
            self._figure = None
            self._ax_left = None
            self._ax_right = None
            self._canvas = None

    @staticmethod
    def _student_t_pdf(t: float, df: int) -> float:
        """Student-t PDF computed without scipy (uses lgamma to avoid overflow)."""
        log_coeff = (
            math.lgamma((df + 1) / 2)
            - 0.5 * math.log(df * math.pi)
            - math.lgamma(df / 2)
        )
        return math.exp(log_coeff) * (1 + t ** 2 / df) ** (-(df + 1) / 2)

    @staticmethod
    def _normal_pdf(x: float, mu: float, sigma: float) -> float:
        """Normal PDF."""
        return (1 / (sigma * math.sqrt(2 * math.pi))) * math.exp(
            -0.5 * ((x - mu) / sigma) ** 2)

    def _decorate(self, ax: Any, title: str, n: int, m: int,
                  grand_mean: float) -> None:
        """Apply common axis decoration."""
        ax.axvline(grand_mean, color="#E65100", linewidth=1, linestyle=":",
                   alpha=0.8, label=f"x\u0304\u0304 = {grand_mean:.2f}", zorder=1)
        ax.set_xlabel("Trung bình mẫu (x\u0304)", fontsize=9, color="#555")
        ax.set_ylabel("Mật độ xác suất", fontsize=9, color="#555")
        ax.tick_params(labelsize=8, colors="#555")
        for spine in ax.spines.values():
            spine.set_edgecolor("#DDD")
        ax.grid(True, axis="y", linestyle="--", linewidth=0.5,
                color="#E0E0E0", alpha=0.7)
        ax.legend(fontsize=8, framealpha=0.9, loc="upper right")
        ax.set_title(
            title, fontsize=10, fontweight="bold", pad=8,
            bbox=dict(boxstyle="round,pad=0.3", fc="white",
                      ec="#BDBDBD", alpha=0.85))

    def render(self, engine: CLTEngine) -> None:
        if not _MPL or self._ax_left is None or self._ax_right is None:  # pragma: no cover
            return
        assert self._figure is not None and self._canvas is not None
        ax_l = self._ax_left
        ax_r = self._ax_right
        ax_l.clear()
        ax_r.clear()
        ax_l.set_facecolor("#FDFEFE")
        ax_r.set_facecolor("#FDFEFE")

        means = engine.sample_means
        if not means:
            for ax in (ax_l, ax_r):
                ax.text(0.5, 0.5, "Chưa có dữ liệu", ha="center", va="center",
                        transform=ax.transAxes, fontsize=12, color="#9E9E9E")
            self._canvas.draw()
            return

        n = engine.sample_size
        m = len(means)
        grand_mean = engine.grand_mean
        std_means = engine.std_of_means

        bin_count = max(5, min(30, int(math.sqrt(m)) + 1))
        x_min = min(means) - 3 * max(std_means, 0.1)
        x_max = max(means) + 3 * max(std_means, 0.1)
        xs = [x_min + (x_max - x_min) * i / 500 for i in range(501)]

        # ── Left chart: Histogram + Student-t ─────────────────────────────
        ax_l.hist(means, bins=bin_count, density=True, alpha=0.6,
                  color="#1976D2", edgecolor="white", linewidth=0.8,
                  label=f"Phân phối x\u0304 (m={m})", zorder=2)
        df = n - 1
        if std_means > 0:
            t_ys = []
            for x in xs:
                t_val = (x - grand_mean) / std_means
                pdf_t = self._student_t_pdf(t_val, df) / std_means
                t_ys.append(pdf_t)
            ax_l.plot(xs, t_ys, color="#C62828", linewidth=2, linestyle="--",
                      label=f"Student t(df={df})", zorder=3)
        self._decorate(ax_l, f"x\u0304 vs Student t — n={n}, m={m}",
                       n, m, grand_mean)

        # ── Right chart: Histogram + Normal ───────────────────────────────
        ax_r.hist(means, bins=bin_count, density=True, alpha=0.6,
                  color="#1976D2", edgecolor="white", linewidth=0.8,
                  label=f"Phân phối x\u0304 (m={m})", zorder=2)
        norm_mu = engine.norm_mean
        norm_sigma = engine.norm_std / math.sqrt(n)
        n_ys = [self._normal_pdf(x, norm_mu, norm_sigma) for x in xs]
        ax_r.plot(xs, n_ys, color="#7B1FA2", linewidth=2, linestyle="-.",
                  label=(f"N(μ={norm_mu:.1f}, "
                         f"σ/√n={norm_sigma:.2f})"),
                  zorder=3)
        self._decorate(ax_r, f"x\u0304 vs Phân phối chuẩn — n={n}, m={m}",
                       n, m, grand_mean)

        self._figure.tight_layout(pad=1.5)
        self._canvas.draw()


# ─── UI: Simulation view ──────────────────────────────────────────────────────


class _SimulationView(_WidgetBase):  # type: ignore[misc]
    """Full-page CLT analysis view — statistics + histogram + theoretical curves."""

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
        ttl = QLabel("📊  Mô phỏng Định lý Giới hạn Trung tâm")
        ttl.setStyleSheet(
            "font-size: 18px; font-weight: bold; color: #37474F; margin-left:8px;")
        top.addWidget(ttl, stretch=1)
        root.addLayout(top)

        # ── Stats bar ─────────────────────────────────────────────────────────
        stats_frame = QFrame()
        stats_frame.setFrameShape(QFrame.Shape.StyledPanel)
        stats_frame.setStyleSheet(
            "QFrame { background:#E3F2FD; border-radius:6px; border:1px solid #BBDEFB; }")
        stats_row = QHBoxLayout(stats_frame)
        stats_row.setContentsMargins(14, 8, 14, 8)
        stats_row.setSpacing(0)

        self._lbl_m = QLabel("—")
        self._lbl_n = QLabel("—")
        self._lbl_grand_mean = QLabel("—")
        self._lbl_std_means = QLabel("—")
        self._lbl_theoretical_se = QLabel("—")

        stat_style = ("font-size: 15px; font-weight: bold; color: #0D47A1;"
                      " padding: 0 16px; border-right: 1px solid #90CAF9;")
        last_style = ("font-size: 15px; font-weight: bold; color: #0D47A1;"
                      " padding: 0 16px;")
        labels_data = [
            (self._lbl_m, "Số mẫu (m): ", stat_style),
            (self._lbl_n, "Cỡ mẫu (n): ", stat_style),
            (self._lbl_grand_mean, "x\u0304\u0304 = ", stat_style),
            (self._lbl_std_means, "s(x\u0304) = ", stat_style),
            (self._lbl_theoretical_se, "σ/√n = ", last_style),
        ]
        for lbl, prefix, style in labels_data:
            pair = QHBoxLayout()
            pair.setSpacing(2)
            plbl = QLabel(prefix)
            plbl.setStyleSheet("font-size: 15px; color: #1565C0; padding: 0 0 0 16px;")
            lbl.setStyleSheet(style)
            pair.addWidget(plbl)
            pair.addWidget(lbl)
            stats_row.addLayout(pair)
        stats_row.addStretch()
        root.addWidget(stats_frame)

        # ── Chart ─────────────────────────────────────────────────────────────
        chart_group = QGroupBox(
            "Phân phối Trung bình mẫu — Đối chiếu Student t và Phân phối chuẩn"
        )
        chart_group.setStyleSheet("QGroupBox { font-weight:bold; font-size:15px; }")
        chart_layout = QVBoxLayout(chart_group)
        chart_layout.setContentsMargins(8, 14, 8, 8)
        self._dist_canvas = _CLTDistributionCanvas()
        chart_layout.addWidget(self._dist_canvas)
        root.addWidget(chart_group, stretch=1)

    # ── Public API ────────────────────────────────────────────────────────────

    def connect_back(self, slot: Any) -> None:
        self._btn_back.clicked.connect(slot)

    def refresh(self, engine: CLTEngine) -> None:
        m = engine.samples_done
        n = engine.sample_size
        self._lbl_m.setText(str(m))
        self._lbl_n.setText(str(n))
        self._lbl_grand_mean.setText(f"{engine.grand_mean:.4f}")
        self._lbl_std_means.setText(f"{engine.std_of_means:.4f}")
        theoretical_se = engine.pop_std / math.sqrt(n) if n > 0 else 0.0
        self._lbl_theoretical_se.setText(f"{theoretical_se:.4f}")

        self._dist_canvas.render(engine)


# ─── UI: Config dialog ────────────────────────────────────────────────────────


class _ConfigDialog(_DialogBase):  # type: ignore[misc]
    """Modal dialog for CLT simulation parameters."""

    def __init__(self, sample_size: int, num_samples: int,
                 pop_mean: float, pop_std: float,
                 norm_mean: float, norm_std: float,
                 parent: Any = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cấu hình mô phỏng CLT")
        self.setFixedWidth(420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 14)
        layout.setSpacing(14)

        # ── Sampling parameters ───────────────────────────────────────────────
        sampling_group = QGroupBox("Tham số lấy mẫu")
        sampling_form = QFormLayout(sampling_group)
        sampling_form.setSpacing(10)
        sampling_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.spin_sample_size = QSpinBox()
        self.spin_sample_size.setRange(2, MAX_SAMPLE_SIZE)
        self.spin_sample_size.setValue(sample_size)
        self.spin_sample_size.setSuffix(f"  (max {MAX_SAMPLE_SIZE})")
        self.spin_sample_size.setMinimumWidth(170)
        self.spin_sample_size.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        sampling_form.addRow("Cỡ mẫu (n):", self.spin_sample_size)

        self.spin_num_samples = QSpinBox()
        self.spin_num_samples.setRange(1, MAX_SAMPLES)
        self.spin_num_samples.setValue(num_samples)
        self.spin_num_samples.setSuffix("  mẫu")
        self.spin_num_samples.setMinimumWidth(170)
        self.spin_num_samples.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        sampling_form.addRow("Số mẫu (m):", self.spin_num_samples)

        layout.addWidget(sampling_group)

        # ── Population parameters ─────────────────────────────────────────────
        pop_group = QGroupBox("Quần thể (tạo dữ liệu)")
        pop_form = QFormLayout(pop_group)
        pop_form.setSpacing(10)
        pop_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.spin_pop_mean = QDoubleSpinBox()
        self.spin_pop_mean.setRange(0.01, 99999.0)
        self.spin_pop_mean.setDecimals(2)
        self.spin_pop_mean.setValue(pop_mean)
        self.spin_pop_mean.setSuffix("  g")
        self.spin_pop_mean.setMinimumWidth(170)
        self.spin_pop_mean.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        pop_form.addRow("Trung bình (μ):", self.spin_pop_mean)

        self.spin_pop_std = QDoubleSpinBox()
        self.spin_pop_std.setRange(0.01, 9999.0)
        self.spin_pop_std.setDecimals(2)
        self.spin_pop_std.setValue(pop_std)
        self.spin_pop_std.setSuffix("  g")
        self.spin_pop_std.setMinimumWidth(170)
        self.spin_pop_std.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        pop_form.addRow("Độ lệch chuẩn (σ):", self.spin_pop_std)

        layout.addWidget(pop_group)

        # ── Normal comparison parameters ──────────────────────────────────────
        norm_group = QGroupBox("Phân phối chuẩn đối chiếu")
        norm_form = QFormLayout(norm_group)
        norm_form.setSpacing(10)
        norm_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        self.spin_norm_mean = QDoubleSpinBox()
        self.spin_norm_mean.setRange(0.01, 99999.0)
        self.spin_norm_mean.setDecimals(2)
        self.spin_norm_mean.setValue(norm_mean)
        self.spin_norm_mean.setSuffix("  g")
        self.spin_norm_mean.setMinimumWidth(170)
        self.spin_norm_mean.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        norm_form.addRow("Trung bình (μ₀):", self.spin_norm_mean)

        self.spin_norm_std = QDoubleSpinBox()
        self.spin_norm_std.setRange(0.01, 9999.0)
        self.spin_norm_std.setDecimals(2)
        self.spin_norm_std.setValue(norm_std)
        self.spin_norm_std.setSuffix("  g")
        self.spin_norm_std.setMinimumWidth(170)
        self.spin_norm_std.setButtonSymbols(
            QAbstractSpinBox.ButtonSymbols.NoButtons)
        norm_form.addRow("Độ lệch chuẩn (σ₀):", self.spin_norm_std)

        layout.addWidget(norm_group)

        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        btns.accepted.connect(self.accept)
        btns.rejected.connect(self.reject)
        layout.addWidget(btns)


# ─── UI: Weighing page ────────────────────────────────────────────────────────


class _WeighingPage(_WidgetBase):  # type: ignore[misc]
    """Main CLT data collection page — conveyor + scale + records table."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 10)
        root.setSpacing(10)

        # ── Header row ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        title = QLabel("⚖  Cân trọng lượng sản phẩm — Định lý Giới hạn Trung tâm")
        title.setStyleSheet(
            "font-size: 19px; font-weight: bold; color: #37474F;")
        hdr.addWidget(title)
        hdr.addStretch()
        self._btn_simulate = QPushButton("📊  Mô phỏng →")
        self._btn_simulate.setMinimumWidth(145)
        self._btn_simulate.setMinimumHeight(36)
        self._btn_simulate.setEnabled(False)
        self._btn_simulate.setToolTip(
            "Hoàn thành đủ số mẫu để mở khóa mô phỏng")
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
            "Bạn đang cân trọng lượng sản phẩm trên dây chuyền sản xuất. "
            "Mỗi mẫu gồm n sản phẩm — hãy cân từng sản phẩm bằng cách kéo "
            "vào cân điện tử, ghi nhận kết quả, rồi tiếp tục cho đến khi đủ "
            "số mẫu đã cài đặt."
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

        # Config values
        self._cfg_sample_size: int = DEFAULT_SAMPLE_SIZE
        self._cfg_num_samples: int = DEFAULT_NUM_SAMPLES
        self._cfg_pop_mean: float = DEFAULT_POP_MEAN
        self._cfg_pop_std: float = DEFAULT_POP_STD
        self._cfg_norm_mean: float = DEFAULT_NORM_MEAN
        self._cfg_norm_std: float = DEFAULT_NORM_STD

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

        self._btn_manual = QPushButton("🔍  Cân thủ công")
        self._btn_manual.setMinimumWidth(145)
        self._btn_manual.setMinimumHeight(36)
        self._btn_manual.setStyleSheet(
            "QPushButton { background:#37474F; color:white; font-weight:bold;"
            " border-radius:6px; padding:4px 14px; }"
            "QPushButton:hover { background:#455A64; }"
            "QPushButton:disabled { background:#B0BEC5; color:#777; }"
        )
        ctrl_row.addWidget(self._btn_manual)

        self._btn_auto = QPushButton("⚡  Cân tự động")
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

        # ── Weighing frame ────────────────────────────────────────────────────
        weigh_box = QGroupBox("Cân sản phẩm")
        weigh_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        weigh_layout = QVBoxLayout(weigh_box)
        weigh_layout.setContentsMargins(6, 10, 6, 6)
        self._weighing_frame = _WeighingFrame()
        weigh_layout.addWidget(self._weighing_frame)
        root.addWidget(weigh_box)

        # ── Records table ─────────────────────────────────────────────────────
        rec_box = QGroupBox("Kết quả các mẫu")
        rec_box.setStyleSheet("QGroupBox { font-weight: bold; }")
        rec_layout = QVBoxLayout(rec_box)
        rec_layout.setContentsMargins(6, 10, 6, 6)
        self._records_table = _SampleRecordsTable()
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

    # ── State control ─────────────────────────────────────────────────────────

    def set_simulate_enabled(self, enabled: bool) -> None:
        self._btn_simulate.setEnabled(enabled)

    def set_manual_enabled(self, enabled: bool) -> None:
        self._btn_manual.setEnabled(enabled)

    def set_auto_enabled(self, enabled: bool) -> None:
        self._btn_auto.setEnabled(enabled)

    def lock_config(self) -> None:
        self._btn_config.setEnabled(False)

    def unlock_config(self) -> None:
        self._btn_config.setEnabled(True)

    def update_status(self, msg: str, ok: bool = True) -> None:
        color = "#2E7D32" if ok else "#C62828"
        self._lbl_status.setStyleSheet(
            f"color: {color}; font-size: 14px; font-weight: bold;")
        self._lbl_status.setText(msg)

    def get_sample_size(self) -> int:
        return self._cfg_sample_size

    def get_num_samples(self) -> int:
        return self._cfg_num_samples

    def get_pop_mean(self) -> float:
        return self._cfg_pop_mean

    def get_pop_std(self) -> float:
        return self._cfg_pop_std

    def get_norm_mean(self) -> float:
        return self._cfg_norm_mean

    def get_norm_std(self) -> float:
        return self._cfg_norm_std

    def sync_config(self, sample_size: int, num_samples: int,
                    pop_mean: float, pop_std: float,
                    norm_mean: float, norm_std: float) -> None:
        self._cfg_sample_size = sample_size
        self._cfg_num_samples = num_samples
        self._cfg_pop_mean = pop_mean
        self._cfg_pop_std = pop_std
        self._cfg_norm_mean = norm_mean
        self._cfg_norm_std = norm_std
        self._update_config_summary()

    def _open_config_dialog(self) -> None:
        dlg = _ConfigDialog(
            self._cfg_sample_size, self._cfg_num_samples,
            self._cfg_pop_mean, self._cfg_pop_std,
            self._cfg_norm_mean, self._cfg_norm_std, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._cfg_sample_size = dlg.spin_sample_size.value()
            self._cfg_num_samples = dlg.spin_num_samples.value()
            self._cfg_pop_mean = dlg.spin_pop_mean.value()
            self._cfg_pop_std = dlg.spin_pop_std.value()
            self._cfg_norm_mean = dlg.spin_norm_mean.value()
            self._cfg_norm_std = dlg.spin_norm_std.value()
            self._update_config_summary()

    def _update_config_summary(self) -> None:
        self._lbl_config_summary.setText(
            f"n={self._cfg_sample_size}, m={self._cfg_num_samples}, "
            f"μ={self._cfg_pop_mean:.1f}, σ={self._cfg_pop_std:.1f}, "
            f"μ₀={self._cfg_norm_mean:.1f}, σ₀={self._cfg_norm_std:.1f}"
        )


# ─── Module ───────────────────────────────────────────────────────────────────


class CentralLimitTheoremModule(BaseModule):
    """IIMP module — Định lý Giới hạn Trung tâm v1.0.0.

    Simulates the Central Limit Theorem through product weighing:
    - Manual weighing: drag products onto a digital scale
    - Auto weighing: auto-generate all remaining samples
    - Simulation view: histogram of sample means vs Student-t and Normal curves
    """

    MODULE_ID = "central_limit_theorem"
    MODULE_NAME = "Định lý Giới hạn Trung tâm"
    MODULE_VERSION = "1.0.0"

    @property
    def module_id(self) -> str:
        return self.MODULE_ID

    @property
    def module_name(self) -> str:
        return self.MODULE_NAME

    @property
    def module_version(self) -> str:
        return self.MODULE_VERSION

    def __init__(self, manifest: dict, context: Any) -> None:
        super().__init__(manifest=manifest, context=context)
        self._engine = CLTEngine()
        self._widget: Any = None
        self._stack: Any = None
        self._weigh_page: Any = None
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
                pass

    def on_activate(self) -> None:
        if self._weigh_page is not None:
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
        root.setObjectName("clt_root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)

        stack = QStackedWidget()
        self._stack = stack

        # Page 0 — weighing
        weigh_page = _WeighingPage()
        self._weigh_page = weigh_page
        weigh_page.connect_manual(self._on_manual)
        weigh_page.connect_auto(self._on_auto)
        weigh_page.connect_reset(self._on_reset)
        weigh_page.connect_simulate(self._on_show_simulation)
        weigh_page._weighing_frame.set_record_callback(self._on_weight_recorded)
        weigh_page._weighing_frame.set_finish_callback(self._on_sample_finished)
        stack.addWidget(weigh_page)

        # Page 1 — simulation
        sim_view = _SimulationView()
        self._sim_view = sim_view
        sim_view.connect_back(self._on_back)
        stack.addWidget(sim_view)

        layout.addWidget(stack)
        self._widget = root

        self._refresh_page()
        return root

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_manual(self) -> None:
        """Start manual weighing for the next sample."""
        if self._weigh_page is None:  # pragma: no cover
            return
        if self._engine.samples_done == 0:
            self._engine.configure(
                self._weigh_page.get_sample_size(),
                self._weigh_page.get_num_samples(),
                self._weigh_page.get_pop_mean(),
                self._weigh_page.get_pop_std(),
                self._weigh_page.get_norm_mean(),
                self._weigh_page.get_norm_std(),
            )
            self._weigh_page.lock_config()

        if self._engine.is_complete:
            return

        # Generate all products for this sample
        n = self._engine.sample_size
        weights = [self._engine.generate_product() for _ in range(n)]
        # Reset current_weights — products are generated but not yet placed
        self._engine.current_weights = []
        self._engine._products_generated = n

        sample_no = self._engine.samples_done + 1
        self._weigh_page._weighing_frame.load_products(
            weights, sample_no, self._engine.num_samples
        )
        self._weigh_page.set_manual_enabled(False)
        self._weigh_page.set_auto_enabled(False)
        self._weigh_page.update_status(
            f"Mẫu {sample_no}/{self._engine.num_samples} — "
            f"Kéo sản phẩm vào cân"
        )

    def _on_weight_recorded(self, weight: float) -> None:
        """Called when a single product weight is recorded."""
        if self._weigh_page is None:  # pragma: no cover
            return
        self._engine.record_weight(weight)
        weighed = self._engine.products_weighed_this_round
        total = self._engine.sample_size
        sample_no = self._engine.samples_done + 1
        self._weigh_page._weighing_frame.update_progress(
            weighed, total, sample_no, self._engine.num_samples
        )

    def _on_sample_finished(self) -> None:
        """Called when user clicks 'Hoàn thành mẫu'."""
        if self._weigh_page is None:  # pragma: no cover
            return
        if self._engine.products_weighed_this_round < self._engine.sample_size:
            return

        rec = self._engine.finish_sample()
        self._weigh_page._records_table.add_record(rec)

        if self._engine.is_complete:
            self._weigh_page._weighing_frame.clear(
                "Hoàn thành! Nhấn  'Mô phỏng →'  để xem kết quả.")
            self._refresh_page()
        else:
            remaining = self._engine.num_samples - self._engine.samples_done
            self._weigh_page._weighing_frame.clear(
                f"Đã hoàn thành mẫu {rec.sample_no}. Còn {remaining} mẫu nữa."
            )
            self._weigh_page.set_manual_enabled(True)
            self._weigh_page.set_auto_enabled(True)
            self._weigh_page.update_status(
                f"Đã cân {self._engine.samples_done}/{self._engine.num_samples} mẫu"
            )

    def _on_auto(self) -> None:
        """Auto-fill all remaining samples."""
        if self._weigh_page is None:  # pragma: no cover
            return
        if self._engine.samples_done == 0:
            self._engine.configure(
                self._weigh_page.get_sample_size(),
                self._weigh_page.get_num_samples(),
                self._weigh_page.get_pop_mean(),
                self._weigh_page.get_pop_std(),
                self._weigh_page.get_norm_mean(),
                self._weigh_page.get_norm_std(),
            )
            self._weigh_page.lock_config()

        new_recs = self._engine.auto_complete()
        self._weigh_page._records_table.add_records_batch(new_recs)

        self._weigh_page._weighing_frame.clear("Cân tự động hoàn tất.")
        self._refresh_page()

    def _on_reset(self) -> None:
        if self._weigh_page is None:  # pragma: no cover
            return
        self._engine.reset()
        self._weigh_page._records_table.populate([])
        self._weigh_page._weighing_frame.clear()
        self._weigh_page.unlock_config()
        self._refresh_page()

    def _on_show_simulation(self) -> None:
        if not self._engine.is_complete:
            return
        if self._sim_view is not None:
            self._sim_view.refresh(self._engine)
        if self._stack is not None:
            self._stack.setCurrentIndex(1)

    def _on_back(self) -> None:
        if self._stack is not None:
            self._stack.setCurrentIndex(0)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _refresh_page(self) -> None:
        if self._weigh_page is None:  # pragma: no cover
            return

        complete = self._engine.is_complete
        pending = self._engine.is_pending
        done = self._engine.samples_done
        total = self._engine.num_samples

        self._weigh_page.set_simulate_enabled(complete)
        self._weigh_page.set_manual_enabled(not complete and not pending)
        self._weigh_page.set_auto_enabled(not complete and not pending)

        if complete:
            self._weigh_page.update_status(
                f"✔ Hoàn thành {done}/{total} mẫu — Sẵn sàng mô phỏng!")
        elif done > 0:
            self._weigh_page.update_status(
                f"Đã cân {done}/{total} mẫu")
            self._weigh_page.lock_config()
        else:
            self._weigh_page.update_status("Sẵn sàng")
            self._weigh_page.unlock_config()

        self._weigh_page.sync_config(
            self._engine.sample_size, self._engine.num_samples,
            self._engine.pop_mean, self._engine.pop_std,
            self._engine.norm_mean, self._engine.norm_std,
        )
        self._weigh_page._records_table.populate(self._engine.records)
