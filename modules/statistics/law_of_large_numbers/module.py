"""Law of Large Numbers — Tung Đồng Xu v1.0.0

Mô phỏng luật số lớn qua thí nghiệm tung đồng xu:
  - Mỗi lần nhấn nút "Tung đồng xu" = 1 tương tác
  - Mỗi tương tác thực hiện x lần tung (x do người dùng cài đặt, mặc định 1)
  - Biểu đồ cập nhật tức thì sau mỗi tương tác, thể hiện tần số tương đối
  - Bảng dữ liệu bên dưới biểu đồ để theo dõi từng lần tung
"""
from __future__ import annotations

import io
import math
import random
from typing import Any

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QFont, QPainter
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QPushButton,
        QRadioButton,
        QScrollArea,
        QSpinBox,
        QSizePolicy,
        QTableWidget,
        QTableWidgetItem,
        QVBoxLayout,
        QWidget,
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

_CanvasBase = QWidget if _QT else object  # type: ignore[misc]
_ModuleWidgetBase = QWidget if _QT else object  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Pure-Python simulation engine (no Qt / matplotlib dependency)
# ---------------------------------------------------------------------------

class LLNCoinEngine:
    """Stateful coin-flip engine — pure Python, fully testable without Qt.

    Each :meth:`toss` call simulates *n* fair coin flips and appends one
    record to :attr:`batches`.  The engine never depends on the UI layer.
    """

    def __init__(self) -> None:
        self.observed_face: str = 'heads'  # 'heads' | 'tails'
        self.cum_tosses: int = 0
        self.cum_heads: int = 0
        # Each entry: (batch_no, tosses_in_batch, hits_in_batch,
        #              cum_tosses, cum_hits, rel_freq)
        self.batches: list[tuple[int, int, int, int, int, float]] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def toss(self, n: int) -> tuple[int, int, float]:
        """Flip *n* coins, update state, append a batch record.

        Returns:
            (heads_in_batch, cumulative_tosses, relative_frequency)
        """
        if n < 1:
            raise ValueError(f"n must be >= 1, got {n}")
        raw_heads = sum(1 for _ in range(n) if random.random() < 0.5)
        hits = raw_heads if self.observed_face == 'heads' else (n - raw_heads)
        self.cum_tosses += n
        self.cum_heads += hits
        rel_freq = self.cum_heads / self.cum_tosses
        batch_no = len(self.batches) + 1
        self.batches.append((batch_no, n, hits, self.cum_tosses, self.cum_heads, rel_freq))
        return hits, self.cum_tosses, rel_freq

    def reset(self) -> None:
        """Clear all accumulated data."""
        self.cum_tosses = 0
        self.cum_heads = 0
        self.batches.clear()

    @property
    def theoretical_prob(self) -> float:
        """Always 0.5 for a fair coin regardless of which face is observed."""
        return 0.5

    def set_observed_face(self, face: str) -> None:
        """Change the observed face and reset accumulated data."""
        if face not in ('heads', 'tails'):
            raise ValueError(f"face must be 'heads' or 'tails', got {face!r}")
        self.observed_face = face
        self.reset()

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "observed_face": self.observed_face,
            "cum_tosses": self.cum_tosses,
            "cum_heads": self.cum_heads,
            "batches": list(self.batches),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.observed_face = state.get("observed_face", "heads")
        self.cum_tosses = int(state.get("cum_tosses", 0))
        self.cum_heads = int(state.get("cum_heads", 0))
        self.batches = [tuple(row) for row in state.get("batches", [])]  # type: ignore[misc]

    # ── Derived series for plotting ───────────────────────────────────────────

    @property
    def x_series(self) -> list[int]:
        """Cumulative toss counts for each batch."""
        return [b[3] for b in self.batches]

    @property
    def y_series(self) -> list[float]:
        """Relative frequencies for each batch."""
        return [b[5] for b in self.batches]


# ---------------------------------------------------------------------------
# Matplotlib canvas
# ---------------------------------------------------------------------------

class _LLNCanvas(_CanvasBase):  # type: ignore[misc]
    """Embedded matplotlib figure that plots relative frequency vs. toss count."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _MPL:
            self._figure = Figure(figsize=(7, 3.2), dpi=100)
            self._figure.patch.set_facecolor("#F8F9FA")
            self._ax = self._figure.add_subplot(111)
            self._mpl_canvas = FigureCanvas(self._figure)
            self._mpl_canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._mpl_canvas)
        else:
            layout.addWidget(QLabel("(matplotlib không khả dụng)"))
            self._figure = None
            self._ax = None
            self._mpl_canvas = None

    def _decorate(self, ax: Any) -> None:
        ax.set_facecolor("#FDFEFE")
        ax.set_xlabel("Số lần tung tích lũy", fontsize=10, color="#555")
        ax.tick_params(labelsize=9, colors="#555")
        for spine in ax.spines.values():
            spine.set_edgecolor("#DDD")
        ax.grid(True, linestyle="--", linewidth=0.5, color="#E0E0E0", alpha=0.8)

    def render(self, x: list[int], y: list[float],
               theoretical: float = 0.5, face_label: str = "ngửa") -> None:
        """Redraw the frequency curve."""
        if not _MPL or self._ax is None:  # pragma: no cover
            return
        ax = self._ax
        ax.clear()
        self._decorate(ax)
        ax.set_ylabel(f"Tần số tương đối ({face_label})", fontsize=10, color="#555")

        # Theoretical reference line
        ax.axhline(theoretical, color="#2ECC71", linestyle="--", lw=1.5,
                   label=f"Lý thuyết p = {theoretical:.4f}", zorder=2)

        if x:
            ax.plot(x, y, color="#2980B9", lw=1.8, zorder=3,
                    label=f"Tần số thực tế (n={x[-1]})")
            # Highlight last point
            ax.scatter([x[-1]], [y[-1]], color="#E74C3C", s=50, zorder=4)
            # Annotation for last value
            ax.annotate(
                f"{y[-1]:.4f}",
                xy=(x[-1], y[-1]),
                xytext=(0, 10), textcoords="offset points",
                ha="center", fontsize=9, color="#E74C3C",
                arrowprops=dict(arrowstyle="->", color="#E74C3C", lw=0.8),
            )

        ax.set_ylim(0.0, 1.0)
        ax.set_xlim(left=0)
        ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
        ax.set_title(f"Tần số tương đối mặt {face_label} theo số lần tung",
                     fontsize=11, fontweight="bold", pad=8,
                     bbox=dict(boxstyle="round,pad=0.3", fc="white",
                               ec="#BDC3C7", alpha=0.85))
        self._figure.tight_layout(pad=1.2)
        self._mpl_canvas.draw()

    def get_figure_bytes(self) -> bytes:
        if not _MPL or self._figure is None:  # pragma: no cover
            return b""
        buf = io.BytesIO()
        self._figure.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Animated coin widget
# ---------------------------------------------------------------------------

class _CoinWidget(_ModuleWidgetBase):  # type: ignore[misc]
    """Gold coin that spins (X-flip illusion) and bounces while toss animation runs.

    Always visible: static resting coin when idle, animated during tosses.
    """

    _D = 52       # coin diameter, px
    _BOUNCE = 14  # max vertical bounce amplitude, px

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self.setFixedSize(100, self._D + self._BOUNCE * 2 + 10)
        self._angle: float = 0.0   # spin angle, degrees
        self._phase: float = 0.0   # bounce phase, radians
        self._running: bool = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)  # ~60 fps
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        """Begin spinning/bouncing animation."""
        self._running = True
        self._timer.start()

    def stop(self) -> None:
        """Freeze coin back to resting state."""
        self._running = False
        self._timer.stop()
        self._angle = 0.0
        self._phase = 0.0
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 9.0) % 360.0
        self._phase = (self._phase + 0.13) % (2.0 * math.pi)
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        if not _QT:  # pragma: no cover
            return
        r = self._D // 2
        cx = self.width() // 2
        cy = self.height() // 2

        bounce = int(math.sin(self._phase) * self._BOUNCE) if self._running else 0
        sx = math.cos(math.radians(self._angle)) if self._running else 1.0
        heads = sx >= 0.0

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Shadow (no X-flip, just squash + bounce)
        painter.save()
        painter.translate(cx + 3, cy + bounce + r + 4)
        painter.scale(abs(sx) * 0.8 + 0.2, 0.25)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 35))
        painter.drawEllipse(-r, -r, self._D, self._D)
        painter.restore()

        # Coin body (X-flip scale for spin illusion)
        painter.save()
        painter.translate(cx, cy + bounce)
        painter.scale(sx, 1.0)

        rim_c = QColor("#B8860B") if heads else QColor("#8B6914")
        face_c = QColor("#FFD700") if heads else QColor("#D4A017")

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(rim_c)
        painter.drawEllipse(-r, -r, self._D, self._D)

        m = 3
        painter.setBrush(face_c)
        painter.drawEllipse(-r + m, -r + m, self._D - 2 * m, self._D - 2 * m)

        # Gloss highlight
        inner = self._D - 2 * m
        painter.setBrush(QColor(255, 255, 255, 75))
        painter.drawEllipse(-r + m + 5, -r + m + 3, inner // 2 - 2, inner // 3 - 1)

        painter.restore()

        # Label — drawn in widget coords (no X-flip) so text is always upright
        label = "N" if heads else "S"
        painter.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        painter.setPen(QColor("#7B5800"))
        painter.drawText(cx - r, cy + bounce - r, self._D, self._D,
                         int(Qt.AlignmentFlag.AlignCenter), label)

        painter.end()


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class LawOfLargeNumbersModule(BaseModule):
    """IIMP module — Luật Số Lớn (Tung Đồng Xu) v1.0.0.

    Người dùng nhấn "Tung đồng xu" để thực hiện x lần tung liên tiếp,
    biểu đồ và bảng dữ liệu cập nhật tức thì, minh hoạ sự hội tụ của
    tần số tương đối về xác suất lý thuyết 0.5.
    """

    MODULE_ID = "law_of_large_numbers"
    MODULE_NAME = "Luật Số Lớn — Tung Đồng Xu"
    MODULE_VERSION = "1.0.0"

    _TABLE_HEADERS = ["#", "Lần tung", "Trúng?", "Tổng tung", "Tổng trúng", "Tần số tương đối"]
    _TABLE_COL_WIDTHS = [40, 80, 60, 90, 90, 130]
    _MAX_TABLE_ROWS = 1000  # cap rows shown in table to keep UI responsive

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

    def __init__(self, manifest: dict, context: ModuleContext) -> None:
        super().__init__(manifest=manifest, context=context)
        self._engine = LLNCoinEngine()
        self._widget: Any = None
        self._canvas: "_LLNCanvas | None" = None
        self._table: Any = None
        self._spin_tosses: Any = None
        self._btn_toss: Any = None
        self._lbl_stats: Any = None
        self._coin_widget: Any = None
        self._rb_heads: Any = None
        self._rb_tails: Any = None
        self._lbl_prob_info: Any = None
        # Animation state
        self._anim_timer: Any = None
        self._anim_remaining: int = 0
        self._anim_chunk: int = 1

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        saved = self.context.settings_service.get_module_setting(
            self.MODULE_ID, "state"
        )
        if saved and isinstance(saved, dict):
            self._engine.restore_state(saved)

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        self._stop_animation()
        self._persist_state()

    def on_unload(self) -> None:
        self._stop_animation()
        self._persist_state()

    def _persist_state(self) -> None:
        self.context.settings_service.set_module_setting(
            self.MODULE_ID, "state", self._engine.get_state()
        )

    # ── View ──────────────────────────────────────────────────────────────────

    def build_view(self) -> Any:
        if not _QT:  # pragma: no cover
            return None

        root = QWidget()
        root.setObjectName("lln_root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        outer.addWidget(self._build_controls())
        _coin = _CoinWidget(root)
        self._coin_widget = _coin
        outer.addWidget(_coin, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(self._build_face_selector())
        outer.addWidget(self._build_chart(), stretch=3)
        outer.addWidget(self._build_table(), stretch=2)

        self._widget = root
        self._refresh_all()
        return root

    # ── Controls panel ────────────────────────────────────────────────────────

    def _build_controls(self) -> Any:
        box = QGroupBox("Điều khiển")
        row = QHBoxLayout(box)
        row.setSpacing(12)

        row.addWidget(QLabel("Số lần tung mỗi tương tác:"))

        spin = QSpinBox()
        spin.setRange(1, 100_000)
        spin.setValue(1)
        spin.setSuffix(" lần")
        spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        spin.setMinimumWidth(90)
        spin.setToolTip("Cài đặt số lần tung đồng xu cho mỗi lần nhấn nút (1 – 100 000)")
        self._spin_tosses = spin
        row.addWidget(spin)

        row.addSpacing(16)

        btn_toss = QPushButton("🪙  Tung đồng xu")
        btn_toss.setMinimumWidth(150)
        btn_toss.setMinimumHeight(36)
        btn_toss.setStyleSheet(
            "QPushButton { background-color: #2980B9; color: white; font-weight: bold;"
            " border-radius: 6px; padding: 4px 16px; }"
            "QPushButton:hover { background-color: #3498DB; }"
            "QPushButton:pressed { background-color: #1F618D; }"
        )
        btn_toss.clicked.connect(self._on_toss)
        self._btn_toss = btn_toss
        row.addWidget(btn_toss)

        btn_reset = QPushButton("↺  Đặt lại")
        btn_reset.setMinimumHeight(36)
        btn_reset.setStyleSheet(
            "QPushButton { background-color: #95A5A6; color: white; font-weight: bold;"
            " border-radius: 6px; padding: 4px 14px; }"
            "QPushButton:hover { background-color: #BDC3C7; }"
        )
        btn_reset.clicked.connect(self._on_reset)
        row.addWidget(btn_reset)

        row.addStretch()

        lbl = QLabel("Tổng: 0 lần | Ngửa: 0 | Tần số: —")
        lbl.setStyleSheet("color: #2C3E50; font-size: 14px;")
        self._lbl_stats = lbl
        row.addWidget(lbl)

        return box

    # ── Face selector panel ───────────────────────────────────────────────────

    def _build_face_selector(self) -> Any:
        box = QGroupBox("Chọn mặt quan sát")
        row = QHBoxLayout(box)
        row.setSpacing(16)

        row.addWidget(QLabel("Mặt quan sát:"))

        rb_heads = QRadioButton("🪙 Ngửa (N)")
        rb_tails = QRadioButton("🪙 Sấp (S)")

        # Reflect current engine state (may have been restored from saved session)
        if self._engine.observed_face == 'tails':
            rb_tails.setChecked(True)
        else:
            rb_heads.setChecked(True)

        rb_heads.toggled.connect(self._on_face_changed)
        rb_tails.toggled.connect(self._on_face_changed)

        self._rb_heads = rb_heads
        self._rb_tails = rb_tails

        row.addWidget(rb_heads)
        row.addWidget(rb_tails)
        row.addStretch()

        lbl = QLabel("Xác suất lý thuyết: p = 1/2 = 0.5000")
        lbl.setStyleSheet("color: #27AE60; font-size: 14px; font-weight: bold;")
        self._lbl_prob_info = lbl
        row.addWidget(lbl)

        return box

    # ── Chart panel ───────────────────────────────────────────────────────────

    def _build_chart(self) -> Any:
        box = QGroupBox("Biểu đồ tần số tương đối")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(6, 6, 6, 6)
        if _MPL:
            canvas = _LLNCanvas(box)
            layout.addWidget(canvas)
            self._canvas = canvas
        else:
            layout.addWidget(QLabel("(matplotlib không khả dụng)"))
        return box

    # ── Table panel ───────────────────────────────────────────────────────────

    def _build_table(self) -> Any:
        box = QGroupBox("Dữ liệu")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(4, 6, 4, 4)

        table = QTableWidget(0, len(self._TABLE_HEADERS))
        table.setHorizontalHeaderLabels(self._TABLE_HEADERS)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setStretchLastSection(True)
        table.setStyleSheet(
            "QTableWidget { gridline-color: #DDE2E8; font-size: 14px; }"
            "QHeaderView::section { background-color: #2C3E50; color: #FFF;"
            " padding: 8px; font-weight: bold; font-size: 15px; }"
        )

        hdr = table.horizontalHeader()
        for col, w in enumerate(self._TABLE_COL_WIDTHS):
            table.setColumnWidth(col, w)
            if col < len(self._TABLE_COL_WIDTHS) - 1:
                hdr.setSectionResizeMode(col, QHeaderView.ResizeMode.Fixed)

        self._table = table
        layout.addWidget(table)
        return box

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_toss(self) -> None:
        if self._anim_remaining > 0:
            return  # animation already running
        n = self._spin_tosses.value() if self._spin_tosses else 1
        self._start_animation(n)

    def _on_reset(self) -> None:
        self._stop_animation()
        self._engine.reset()
        self._refresh_all()
    def _on_face_changed(self) -> None:
        if self._rb_heads is None or self._rb_tails is None:
            return
        face = 'heads' if self._rb_heads.isChecked() else 'tails'
        if face == self._engine.observed_face:
            return  # guard against double-fire (toggled fires for both off and on)
        self._stop_animation()
        self._engine.set_observed_face(face)
        self._refresh_all()
    # ── Animation ─────────────────────────────────────────────────────────────

    def _start_animation(self, n: int) -> None:
        """Begin sequential single-toss animation over *n* steps."""
        self._anim_remaining = n
        # Scale chunk so total visual updates ≤ 100 (keeps UI fluid for large n)
        self._anim_chunk = max(1, n // 100)
        if self._btn_toss is not None:
            self._btn_toss.setEnabled(False)
            self._btn_toss.setText("⏳  Đang tung...")
        if self._coin_widget is not None:
            self._coin_widget.start()
        if _QT:
            self._anim_timer = QTimer(self._widget)
            self._anim_timer.setInterval(30)
            self._anim_timer.timeout.connect(self._anim_step)
            self._anim_timer.start()
        else:  # pragma: no cover
            self._flush_animation()

    def _anim_step(self) -> None:
        """Process one timer tick: toss *chunk* coins then refresh display."""
        if self._anim_remaining <= 0:
            self._stop_animation()
            return
        chunk = min(self._anim_chunk, self._anim_remaining)
        for _ in range(chunk):
            self._engine.toss(1)
        self._anim_remaining -= chunk
        self._refresh_all()
        if self._anim_remaining <= 0:
            self._stop_animation()

    def _stop_animation(self) -> None:
        """Stop animation timer and restore button state."""
        if self._anim_timer is not None:
            self._anim_timer.stop()
            self._anim_timer = None
        self._anim_remaining = 0
        if self._btn_toss is not None:
            self._btn_toss.setEnabled(True)
            self._btn_toss.setText("🪙  Tung đồng xu")
        if self._coin_widget is not None:
            self._coin_widget.stop()

    def _flush_animation(self) -> None:
        """Drain all remaining animation steps synchronously.

        Intended for use in tests and non-Qt environments.
        """
        while self._anim_remaining > 0:
            self._anim_step()

    # ── Refresh helpers ───────────────────────────────────────────────────────

    def _refresh_all(self) -> None:
        self._refresh_chart()
        self._refresh_table()
        self._refresh_stats()

    def _refresh_chart(self) -> None:
        if self._canvas is None:
            return
        face_label = "ngửa" if self._engine.observed_face == 'heads' else "sấp"
        self._canvas.render(
            self._engine.x_series,
            self._engine.y_series,
            self._engine.theoretical_prob,
            face_label,
        )

    def _refresh_table(self) -> None:
        if self._table is None:
            return
        batches = self._engine.batches
        # Cap displayed rows to keep UI responsive with large n
        display = batches[-self._MAX_TABLE_ROWS:] if len(batches) > self._MAX_TABLE_ROWS else batches
        self._table.setRowCount(len(display))
        for row_idx, (batch_no, n, heads, cum_t, cum_h, freq) in enumerate(reversed(display)):
            values = [
                str(batch_no),
                str(n),
                str(heads),
                str(cum_t),
                str(cum_h),
                f"{freq:.6f}",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 5:  # frequency column — colour-code proximity to 0.5
                    diff = abs(freq - 0.5)
                    if diff < 0.01:
                        item.setForeground(QColor("#27AE60"))
                    elif diff < 0.05:
                        item.setForeground(QColor("#F39C12"))
                    else:
                        item.setForeground(QColor("#E74C3C"))
                self._table.setItem(row_idx, col, item)

    def _refresh_stats(self) -> None:
        if self._lbl_stats is None:
            return
        t = self._engine.cum_tosses
        h = self._engine.cum_heads
        face_label = "Ngửa" if self._engine.observed_face == 'heads' else "Sấp"
        if t == 0:
            self._lbl_stats.setText(f"Tổng: 0 lần | {face_label}: 0 | Tần số: —")
        else:
            freq = h / t
            self._lbl_stats.setText(
                f"Tổng: {t:,} lần | {face_label}: {h:,} | Tần số: {freq:.6f}"
            )

    # ── State / settings (BaseModule contract) ────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return self._engine.get_state()

    def restore_state(self, state: dict[str, Any]) -> None:
        self._engine.restore_state(state)
        if self._rb_heads is not None and self._rb_tails is not None:
            self._rb_heads.blockSignals(True)
            self._rb_tails.blockSignals(True)
            if self._engine.observed_face == 'tails':
                self._rb_tails.setChecked(True)
            else:
                self._rb_heads.setChecked(True)
            self._rb_heads.blockSignals(False)
            self._rb_tails.blockSignals(False)
        self._refresh_all()

    # ── Export ────────────────────────────────────────────────────────────────

    def export(self) -> None:
        if self._canvas is None:
            return
        data = self._canvas.get_figure_bytes()
        if data:
            self.context.export_service.write_bytes(
                filename=f"lln_coin_{self._engine.cum_tosses}_tosses.png",
                data=data,
            )
