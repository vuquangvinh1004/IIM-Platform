"""Law of Large Numbers — Tung Xúc Xắc v1.0.0

Mô phỏng luật số lớn qua thí nghiệm tung xúc xắc:
  - Người dùng chọn một hoặc nhiều mặt muốn quan sát (1–6 chấm)
  - Xác suất lý thuyết = số mặt được chọn / 6
  - Mỗi lần nhấn nút thực hiện n lần tung riêng lẻ (animation tuần tự)
  - Biểu đồ & bảng cập nhật từng bước, minh hoạ sự hội tụ
"""
from __future__ import annotations

import io
import math
import random
from typing import Any

try:
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtGui import QColor, QFont, QPainter, QPen
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
        QButtonGroup,
        QCheckBox,
        QGroupBox,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QPushButton,
        QSizePolicy,
        QSpinBox,
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

_CanvasBase = QWidget if _QT else object        # type: ignore[misc]
_ModuleWidgetBase = QWidget if _QT else object  # type: ignore[misc]

# Dot positions for each face (normalized 0–1 inside the die square)
_DOT_POSITIONS: dict[int, list[tuple[float, float]]] = {
    1: [(0.5, 0.5)],
    2: [(0.25, 0.25), (0.75, 0.75)],
    3: [(0.25, 0.25), (0.5, 0.5), (0.75, 0.75)],
    4: [(0.25, 0.25), (0.75, 0.25), (0.25, 0.75), (0.75, 0.75)],
    5: [(0.25, 0.25), (0.75, 0.25), (0.5, 0.5), (0.25, 0.75), (0.75, 0.75)],
    6: [(0.25, 0.2), (0.75, 0.2), (0.25, 0.5), (0.75, 0.5), (0.25, 0.8), (0.75, 0.8)],
}


# ---------------------------------------------------------------------------
# Pure-Python simulation engine
# ---------------------------------------------------------------------------

class LLNDiceEngine:
    """Stateful dice-roll engine — pure Python, fully testable without Qt.

    Each :meth:`roll` simulates one fair 6-sided die.
    A roll counts as a "hit" when the result is in :attr:`observed_faces`.
    """

    def __init__(self, observed_faces: list[int] | None = None) -> None:
        self.observed_faces: list[int] = sorted(set(observed_faces or [1]))
        self.cum_rolls: int = 0
        self.cum_hits: int = 0
        # Each entry: (roll_no, face, hit, cum_rolls, cum_hits, rel_freq)
        self.rolls: list[tuple[int, int, bool, int, int, float]] = []

    # ── Public API ────────────────────────────────────────────────────────────

    @property
    def theoretical_prob(self) -> float:
        """Theoretical probability = |observed| / 6."""
        return len(self.observed_faces) / 6

    def roll(self) -> tuple[int, bool, int, float]:
        """Simulate one die roll.

        Returns:
            (face, hit, cumulative_rolls, relative_frequency)
        """
        face = random.randint(1, 6)
        hit = face in self.observed_faces
        self.cum_rolls += 1
        if hit:
            self.cum_hits += 1
        rel_freq = self.cum_hits / self.cum_rolls
        roll_no = len(self.rolls) + 1
        self.rolls.append((roll_no, face, hit, self.cum_rolls, self.cum_hits, rel_freq))
        return face, hit, self.cum_rolls, rel_freq

    def reset(self) -> None:
        """Clear all accumulated data but keep observed_faces."""
        self.cum_rolls = 0
        self.cum_hits = 0
        self.rolls.clear()

    def set_observed_faces(self, faces: list[int]) -> None:
        """Change observed faces and reset data."""
        self.observed_faces = sorted(set(faces))
        self.reset()

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "observed_faces": list(self.observed_faces),
            "cum_rolls": self.cum_rolls,
            "cum_hits": self.cum_hits,
            "rolls": [list(r) for r in self.rolls],
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self.observed_faces = list(state.get("observed_faces", [1]))
        self.cum_rolls = int(state.get("cum_rolls", 0))
        self.cum_hits = int(state.get("cum_hits", 0))
        self.rolls = [tuple(r) for r in state.get("rolls", [])]  # type: ignore[misc]

    # ── Derived series ────────────────────────────────────────────────────────

    @property
    def x_series(self) -> list[int]:
        return [r[3] for r in self.rolls]

    @property
    def y_series(self) -> list[float]:
        return [r[5] for r in self.rolls]

    @property
    def last_face(self) -> int | None:
        return self.rolls[-1][1] if self.rolls else None


# ---------------------------------------------------------------------------
# Matplotlib canvas
# ---------------------------------------------------------------------------

class _DiceCanvas(_CanvasBase):  # type: ignore[misc]
    """Embedded matplotlib figure: relative frequency vs. roll count."""

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
        ax.set_ylabel("Tần số tương đối", fontsize=10, color="#555")
        ax.tick_params(labelsize=9, colors="#555")
        for spine in ax.spines.values():
            spine.set_edgecolor("#DDD")
        ax.grid(True, linestyle="--", linewidth=0.5, color="#E0E0E0", alpha=0.8)

    def render(self, x: list[int], y: list[float],
               theoretical: float, face_label: str) -> None:
        if not _MPL or self._ax is None:  # pragma: no cover
            return
        ax = self._ax
        ax.clear()
        self._decorate(ax)

        # Theoretical reference line
        ax.axhline(theoretical, color="#2ECC71", linestyle="--", lw=1.5,
                   label=f"Lý thuyết p = {theoretical:.4f}", zorder=2)

        if x:
            ax.plot(x, y, color="#E74C3C", lw=1.8, zorder=3,
                    label=f"Tần số thực tế (n={x[-1]})")
            ax.scatter([x[-1]], [y[-1]], color="#C0392B", s=50, zorder=4)
            ax.annotate(
                f"{y[-1]:.4f}",
                xy=(x[-1], y[-1]),
                xytext=(0, 10), textcoords="offset points",
                ha="center", fontsize=9, color="#C0392B",
                arrowprops=dict(arrowstyle="->", color="#C0392B", lw=0.8),
            )

        ax.set_ylim(0.0, 1.0)
        ax.set_xlim(left=0)
        ax.legend(loc="upper right", fontsize=9, framealpha=0.9)
        ax.set_title(
            f"Tần số tương đối mặt {face_label} theo số lần tung",
            fontsize=11, fontweight="bold", pad=8,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#BDC3C7", alpha=0.85),
        )
        self._figure.tight_layout(pad=1.2)
        self._mpl_canvas.draw()

    def get_figure_bytes(self) -> bytes:
        if not _MPL or self._figure is None:  # pragma: no cover
            return b""
        buf = io.BytesIO()
        self._figure.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Animated dice widget
# ---------------------------------------------------------------------------

class _DiceWidget(_ModuleWidgetBase):  # type: ignore[misc]
    """Painted die face that tumbles while rolling and shows current result at rest."""

    _S = 58       # die size, px
    _BOUNCE = 12  # max vertical bounce amplitude, px

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        total_h = self._S + self._BOUNCE * 2 + 10
        self.setFixedSize(self._S + 40, total_h)
        self._face: int = 1           # displayed face (1-6)
        self._angle: float = 0.0      # spin angle deg (for 3-D tilt illusion)
        self._phase: float = 0.0      # bounce phase rad
        self._running: bool = False
        self._timer = QTimer(self)
        self._timer.setInterval(16)
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        self._running = True
        self._timer.start()

    def stop(self, final_face: int = 1) -> None:
        self._running = False
        self._timer.stop()
        self._face = final_face
        self._angle = 0.0
        self._phase = 0.0
        self.update()

    def _tick(self) -> None:
        self._angle = (self._angle + 9.0) % 360.0
        self._phase = (self._phase + 0.14) % (2.0 * math.pi)
        # Randomly cycle face while spinning for visual effect
        if int(self._angle) % 60 == 0:
            self._face = random.randint(1, 6)
        self.update()

    def paintEvent(self, event: Any) -> None:  # noqa: N802
        if not _QT:  # pragma: no cover
            return
        s = self._S
        cx = self.width() // 2
        cy = self.height() // 2

        bounce = int(math.sin(self._phase) * self._BOUNCE) if self._running else 0
        sx = math.cos(math.radians(self._angle)) if self._running else 1.0

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Shadow
        painter.save()
        painter.translate(cx + 4, cy + bounce + s // 2 + 5)
        painter.scale(abs(sx) * 0.85 + 0.15, 0.2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(0, 0, 0, 40))
        painter.drawEllipse(-s // 2, -s // 4, s, s // 2)
        painter.restore()

        # Die body (X-flip for spin illusion)
        painter.save()
        painter.translate(cx, cy + bounce)
        painter.scale(sx, 1.0)

        radius = 9
        die_color = QColor("#F0F4FF") if sx >= 0 else QColor("#D0D8F0")
        border_color = QColor("#3A5080")

        pen = QPen(border_color, 2)
        painter.setPen(pen)
        painter.setBrush(die_color)
        painter.drawRoundedRect(-s // 2, -s // 2, s, s, radius, radius)

        # Dots
        face = max(1, min(6, self._face))
        for (nx, ny) in _DOT_POSITIONS[face]:
            dx = int(-s // 2 + nx * s)
            dy = int(-s // 2 + ny * s)
            dr = 5
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2C3E50"))
            painter.drawEllipse(dx - dr, dy - dr, dr * 2, dr * 2)

        painter.restore()
        painter.end()


# ---------------------------------------------------------------------------
# Face selector widget — 6 checkboxes with drawn die faces
# ---------------------------------------------------------------------------

class _FaceSelectorWidget(_ModuleWidgetBase):  # type: ignore[misc]
    """Row of 6 checkboxes labelled with die face mini-icons."""

    def __init__(self, parent: Any = None) -> None:
        if not _QT:  # pragma: no cover
            return
        super().__init__(parent)
        self._checks: list[Any] = []
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(QLabel("Quan sát mặt:"))

        for face in range(1, 7):
            cb = QCheckBox(f"⚅"[0] + str(face) if False else f" {face} chấm")
            cb.setText(f"{face} chấm")
            cb.setToolTip(f"Quan sát mặt {face} chấm")
            if face == 1:
                cb.setChecked(True)
            self._checks.append(cb)
            layout.addWidget(cb)

        layout.addStretch()

    def get_selected(self) -> list[int]:
        """Return sorted list of selected faces (1-indexed, at least one)."""
        selected = [i + 1 for i, cb in enumerate(self._checks) if cb.isChecked()]
        return selected if selected else [1]

    def set_selected(self, faces: list[int]) -> None:
        face_set = set(faces)
        for i, cb in enumerate(self._checks):
            cb.setChecked((i + 1) in face_set)

    def connect_changed(self, slot: Any) -> None:
        for cb in self._checks:
            cb.stateChanged.connect(slot)


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------

class LLNDiceModule(BaseModule):
    """IIMP module — Luật Số Lớn (Tung Xúc Xắc) v1.0.0."""

    MODULE_ID = "law_of_large_numbers_dice"
    MODULE_NAME = "Luật Số Lớn — Tung Xúc Xắc"
    MODULE_VERSION = "1.0.0"

    _TABLE_HEADERS = ["#", "Mặt tung", "Trúng?", "Tổng tung", "Tổng trúng", "Tần số tương đối"]
    _TABLE_COL_WIDTHS = [40, 80, 60, 90, 90, 140]
    _MAX_TABLE_ROWS = 1000

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
        self._engine = LLNDiceEngine(observed_faces=[1])
        self._widget: Any = None
        self._canvas: "_DiceCanvas | None" = None
        self._table: Any = None
        self._spin_rolls: Any = None
        self._btn_roll: Any = None
        self._lbl_stats: Any = None
        self._face_selector: Any = None
        self._dice_widget: Any = None
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
        root.setObjectName("lln_dice_root")
        outer = QVBoxLayout(root)
        outer.setContentsMargins(14, 14, 14, 14)
        outer.setSpacing(10)

        outer.addWidget(self._build_controls())
        dice = _DiceWidget(root)
        self._dice_widget = dice
        outer.addWidget(dice, 0, Qt.AlignmentFlag.AlignHCenter)
        outer.addWidget(self._build_face_selector())
        outer.addWidget(self._build_chart(), stretch=3)
        outer.addWidget(self._build_table(), stretch=2)

        self._widget = root
        self._refresh_all()
        return root

    # ── Face selector panel ──────────────────────────────────────────────────────────────────────────────────────

    def _build_face_selector(self) -> Any:
        box = QGroupBox("Chọn mặt quan sát")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(8, 8, 8, 8)

        sel = _FaceSelectorWidget(box)
        sel.set_selected(self._engine.observed_faces)
        sel.connect_changed(self._on_faces_changed)
        self._face_selector = sel
        layout.addWidget(sel)

        info = QLabel()
        info.setStyleSheet("color: #2980B9; font-size: 13px;")
        self._lbl_prob_info = info
        layout.addWidget(info)
        self._update_prob_label()

        return box

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
        spin.setToolTip("Số lần tung xúc xắc mỗi lần nhấn nút (1 – 100 000)")
        self._spin_rolls = spin
        row.addWidget(spin)

        row.addSpacing(16)

        btn_roll = QPushButton("🎲  Tung xúc xắc")
        btn_roll.setMinimumWidth(155)
        btn_roll.setMinimumHeight(36)
        btn_roll.setStyleSheet(
            "QPushButton { background-color: #C0392B; color: white; font-weight: bold;"
            " border-radius: 6px; padding: 4px 16px; }"
            "QPushButton:hover { background-color: #E74C3C; }"
            "QPushButton:pressed { background-color: #922B21; }"
        )
        btn_roll.clicked.connect(self._on_roll)
        self._btn_roll = btn_roll
        row.addWidget(btn_roll)

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

        lbl = QLabel("Tổng: 0 lần | Trúng: 0 | Tần số: —")
        lbl.setStyleSheet("color: #2C3E50; font-size: 14px;")
        self._lbl_stats = lbl
        row.addWidget(lbl)

        return box

    # ── Chart panel ───────────────────────────────────────────────────────────

    def _build_chart(self) -> Any:
        box = QGroupBox("Biểu đồ tần số tương đối")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(6, 6, 6, 6)
        if _MPL:
            canvas = _DiceCanvas(box)
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

    def _on_roll(self) -> None:
        if self._anim_remaining > 0:
            return
        n = self._spin_rolls.value() if self._spin_rolls else 1
        self._start_animation(n)

    def _on_reset(self) -> None:
        self._stop_animation()
        self._engine.reset()
        self._refresh_all()

    def _on_faces_changed(self) -> None:
        """Called when user checks/unchecks a face checkbox."""
        if self._face_selector is None:
            return
        new_faces = self._face_selector.get_selected()
        self._engine.set_observed_faces(new_faces)
        self._update_prob_label()
        self._refresh_all()

    # ── Animation ─────────────────────────────────────────────────────────────

    def _start_animation(self, n: int) -> None:
        self._anim_remaining = n
        self._anim_chunk = max(1, n // 100)
        if self._btn_roll is not None:
            self._btn_roll.setEnabled(False)
            self._btn_roll.setText("⏳  Đang tung...")
        if self._dice_widget is not None:
            self._dice_widget.start()
        if _QT:
            self._anim_timer = QTimer(self._widget)
            self._anim_timer.setInterval(30)
            self._anim_timer.timeout.connect(self._anim_step)
            self._anim_timer.start()
        else:  # pragma: no cover
            self._flush_animation()

    def _anim_step(self) -> None:
        if self._anim_remaining <= 0:
            self._stop_animation()
            return
        chunk = min(self._anim_chunk, self._anim_remaining)
        for _ in range(chunk):
            self._engine.roll()
        self._anim_remaining -= chunk
        self._refresh_all()
        if self._anim_remaining <= 0:
            self._stop_animation()

    def _stop_animation(self) -> None:
        if self._anim_timer is not None:
            self._anim_timer.stop()
            self._anim_timer = None
        self._anim_remaining = 0
        if self._btn_roll is not None:
            self._btn_roll.setEnabled(True)
            self._btn_roll.setText("🎲  Tung xúc xắc")
        if self._dice_widget is not None:
            last = self._engine.last_face or 1
            self._dice_widget.stop(last)

    def _flush_animation(self) -> None:
        """Drain all remaining animation steps synchronously (tests / non-Qt)."""
        while self._anim_remaining > 0:
            self._anim_step()

    # ── Refresh helpers ───────────────────────────────────────────────────────

    def _refresh_all(self) -> None:
        self._refresh_chart()
        self._refresh_table()
        self._refresh_stats()

    def _face_label(self) -> str:
        faces = self._engine.observed_faces
        return ", ".join(str(f) for f in faces)

    def _refresh_chart(self) -> None:
        if self._canvas is None:
            return
        self._canvas.render(
            self._engine.x_series,
            self._engine.y_series,
            self._engine.theoretical_prob,
            self._face_label(),
        )

    def _refresh_table(self) -> None:
        if self._table is None:
            return
        rolls = self._engine.rolls
        display = (
            rolls[-self._MAX_TABLE_ROWS:] if len(rolls) > self._MAX_TABLE_ROWS else rolls
        )
        self._table.setRowCount(len(display))
        for row_idx, (roll_no, face, hit, cum_t, cum_h, freq) in enumerate(reversed(display)):
            values = [
                str(roll_no),
                str(face),
                "✔" if hit else "✘",
                str(cum_t),
                str(cum_h),
                f"{freq:.6f}",
            ]
            for col, val in enumerate(values):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if col == 2:  # hit column
                    item.setForeground(
                        QColor("#27AE60") if hit else QColor("#E74C3C")
                    )
                if col == 5:  # frequency column
                    diff = abs(freq - self._engine.theoretical_prob)
                    tol = self._engine.theoretical_prob * 0.05
                    if diff < tol:
                        item.setForeground(QColor("#27AE60"))
                    elif diff < tol * 3:
                        item.setForeground(QColor("#F39C12"))
                    else:
                        item.setForeground(QColor("#E74C3C"))
                self._table.setItem(row_idx, col, item)

    def _refresh_stats(self) -> None:
        if self._lbl_stats is None:
            return
        t = self._engine.cum_rolls
        h = self._engine.cum_hits
        if t == 0:
            self._lbl_stats.setText("Tổng: 0 lần | Trúng: 0 | Tần số: —")
        else:
            freq = h / t
            self._lbl_stats.setText(
                f"Tổng: {t:,} lần | Trúng: {h:,} | Tần số: {freq:.6f}"
            )

    def _update_prob_label(self) -> None:
        if not hasattr(self, "_lbl_prob_info") or self._lbl_prob_info is None:
            return
        k = len(self._engine.observed_faces)
        p = self._engine.theoretical_prob
        faces_str = ", ".join(str(f) for f in self._engine.observed_faces)
        self._lbl_prob_info.setText(
            f"Mặt quan sát: [{faces_str}]  —  "
            f"Xác suất lý thuyết: {k}/6 = {p:.4f}"
        )

    # ── State / settings (BaseModule contract) ────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return self._engine.get_state()

    def restore_state(self, state: dict[str, Any]) -> None:
        self._engine.restore_state(state)
        if self._face_selector is not None:
            self._face_selector.set_selected(self._engine.observed_faces)
        self._update_prob_label()
        self._refresh_all()

    # ── Export ────────────────────────────────────────────────────────────────

    def export(self) -> None:
        if self._canvas is None:
            return
        data = self._canvas.get_figure_bytes()
        if data:
            self.context.export_service.write_bytes(
                filename=f"lln_dice_{self._engine.cum_rolls}_rolls.png",
                data=data,
            )
