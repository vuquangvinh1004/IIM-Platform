"""PSO Explorer — Particle Swarm Optimization v1.0.0

Split-panel layout:
  Left  (fixed width)  : controls, run/stop buttons, result summary
  Right (expanding)    : QTabWidget
      Tab 0 — Không gian 2D : particle scatter + contour background (dim=2 only)
      Tab 1 — Đồ thị hội tụ : gbest fitness vs iteration number

Threading strategy:
  - PSO simulation runs in SimulationWorker (QThread) to avoid blocking the UI.
  - Worker emits iteration_done(iter, gbest_f, gbest_pos, positions) after each
    step. The UI slot updates the convergence chart every iteration and refreshes
    the particle scatter every _REDRAW_EVERY iterations to stay responsive.
  - on_unload() calls worker.request_stop() + worker.wait() to ensure clean
    teardown before the module is unloaded.
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QComboBox,
        QDoubleSpinBox,
        QAbstractSpinBox,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QProgressBar,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpinBox,
        QTabWidget,
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
from modules.logistics.particle_swarm_optimization.core.objective_functions import (
    get_function,
    list_functions,
)
from modules.logistics.particle_swarm_optimization.models.config import PSOConfig
from modules.logistics.particle_swarm_optimization.models.state import (
    STATE_VERSION,
    default_state,
)

try:
    from shiboken6 import isValid as _qt_is_valid
except ImportError:  # pragma: no cover
    def _qt_is_valid(_obj: object) -> bool:
        return True

_WidgetBase = QWidget if _QT else object  # type: ignore[misc,assignment]

# ── UI tuning constants ───────────────────────────────────────────────────────
_REDRAW_EVERY: int = 5          # update particle scatter every N iters (animation mode only)
_CTRL_WIDTH: int = 300          # fixed width of the left control panel (px)
_MONO_STYLE: str = "font-size: 11px; font-family: monospace;"
_MAX_TRAJ_FRAMES: int = 500     # max stored trajectory frames (memory cap)
_DEFAULT_DELAY_MS: int = 50     # default per-iteration delay in animation/trail modes


# ─── Canvas: 2D particle scatter ─────────────────────────────────────────────


class _ParticleCanvas(_WidgetBase):  # type: ignore[valid-type]
    """Matplotlib canvas: contour background + particle scatter + gBest marker.

    Call setup() once before a run. Call update_particles() from the
    iteration_done slot to refresh the display.
    """

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._fig = Figure(figsize=(7, 6), dpi=100)
            self._ax = self._fig.add_subplot(111)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
            self._scatter = None
            self._gbest_marker = None
            self._trail_artists: list = []
            self._ready = False
        else:
            layout.addWidget(
                QLabel("⚠ matplotlib chưa được cài. Chạy: pip install matplotlib")
            )

    def setup(self, obj_key: str, lb: float, ub: float, resolution: int = 80) -> None:
        """Pre-render contour background for the given function and bounds.

        Must be called on the UI thread (manipulates Qt widgets).
        """
        if not _MPL:
            return
        self._ax.clear()
        # Draw contour of the objective function as background
        try:
            func = get_function(obj_key)
            xs = np.linspace(lb, ub, resolution)
            ys = np.linspace(lb, ub, resolution)
            XX, YY = np.meshgrid(xs, ys)
            ZZ = np.vectorize(lambda xi, yi: func.evaluate(np.array([xi, yi])))(XX, YY)
            self._ax.contourf(XX, YY, ZZ, levels=20, cmap="Blues_r", alpha=0.45)
            self._ax.contour(
                XX, YY, ZZ, levels=20, colors="white", linewidths=0.3, alpha=0.35
            )
        except Exception:
            pass  # blank background is acceptable

        self._ax.set_xlim(lb, ub)
        self._ax.set_ylim(lb, ub)
        self._ax.set_xlabel("x₁", fontsize=9)
        self._ax.set_ylabel("x₂", fontsize=9)
        self._ax.set_title("Không gian tìm kiếm 2D", fontsize=10)
        self._fig.tight_layout(pad=1.0)
        self._canvas.draw()
        self._scatter = None
        self._gbest_marker = None
        self._trail_artists = []
        self._ready = True

    def update_particles(
        self,
        positions: list[list[float]],
        gbest: list[float],
        iteration: int,
    ) -> None:
        """Refresh scatter in animation mode (no trail). Backward-compatible wrapper."""
        self.update_with_trails(positions, gbest, iteration, [], "animation", 10, 0)

    def update_with_trails(
        self,
        positions: list[list[float]],
        gbest: list[float],
        iteration: int,
        trajectories: list[list[list[float]]],
        mode: str,
        tail_len: int,
        n_display: int,
    ) -> None:
        """Refresh scatter + optional trajectory trails.

        Args:
            positions    : current particle positions (list of [x, y])
            gbest        : current global best position [x, y]
            iteration    : iteration number for axes title
            trajectories : accumulated frames list[frame_idx][particle_idx][coord]
            mode         : "animation" | "full_trail" | "short_tail"
            tail_len     : frames to show in short_tail mode (min 2)
            n_display    : max particles to draw trail/scatter for (0 = all)
        """
        if not _MPL or not self._ready:
            return

        # ── Remove old dynamic artists ─────────────────────────────────────
        for artist in self._trail_artists:
            try:
                artist.remove()
            except Exception:
                pass
        self._trail_artists = []
        if self._scatter is not None:
            self._scatter.remove()
            self._scatter = None
        if self._gbest_marker is not None:
            self._gbest_marker.remove()
            self._gbest_marker = None

        n_particles = len(positions)
        n_show = n_particles if n_display <= 0 else min(n_display, n_particles)

        # ── Draw trajectory trails ─────────────────────────────────────────
        if mode in ("full_trail", "short_tail") and len(trajectories) >= 2:
            import matplotlib.cm as _mpl_cm  # noqa: PLC0415

            if mode == "full_trail":
                frames = (
                    trajectories[-_MAX_TRAJ_FRAMES:]
                    if len(trajectories) > _MAX_TRAJ_FRAMES
                    else trajectories
                )
                trail_alpha = 0.15
            else:  # short_tail
                frames = (
                    trajectories[-max(2, tail_len):]
                    if len(trajectories) > max(2, tail_len)
                    else trajectories
                )
                trail_alpha = 0.50

            palette = [_mpl_cm.tab10(i % 10) for i in range(n_show)]
            for i in range(n_show):
                try:
                    xs = [frame[i][0] for frame in frames]
                    ys = [frame[i][1] for frame in frames]
                except IndexError:
                    continue
                color = palette[i]
                (line,) = self._ax.plot(
                    xs, ys,
                    color=color, alpha=trail_alpha, lw=0.9, zorder=3,
                    solid_capstyle="round",
                )
                self._trail_artists.append(line)
                # Small dot at most-recent trail tip
                head = self._ax.scatter(
                    [xs[-1]], [ys[-1]],
                    c=[color], s=8, alpha=0.75, zorder=4, linewidths=0,
                )
                self._trail_artists.append(head)

        # ── Draw current particle scatter ──────────────────────────────────
        pts = np.array(positions[:n_show])
        self._scatter = self._ax.scatter(
            pts[:, 0], pts[:, 1],
            c="#F39C12", s=18, alpha=0.80, zorder=5, linewidths=0,
        )
        # Remaining (capped) particles as faded background dots
        if n_show < n_particles:
            pts_rest = np.array(positions[n_show:])
            dim_scatter = self._ax.scatter(
                pts_rest[:, 0], pts_rest[:, 1],
                c="#BDC3C7", s=8, alpha=0.30, zorder=4, linewidths=0,
            )
            self._trail_artists.append(dim_scatter)

        # ── Draw gBest marker ──────────────────────────────────────────────
        self._gbest_marker = self._ax.scatter(
            [gbest[0]], [gbest[1]],
            c="#E74C3C", s=140, marker="*", zorder=6, linewidths=0,
        )
        self._ax.set_title(f"Không gian 2D — Vòng lặp {iteration}", fontsize=10)
        self._canvas.draw_idle()

    def get_figure_bytes(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        return buf.getvalue()


# ─── Canvas: convergence chart ────────────────────────────────────────────────


class _ConvergenceCanvas(_WidgetBase):  # type: ignore[valid-type]
    """Matplotlib canvas: gbest_fitness vs iteration number."""

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._fig = Figure(figsize=(7, 5), dpi=100)
            self._ax = self._fig.add_subplot(111)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
            self._history: list[float] = []
        else:
            layout.addWidget(
                QLabel("⚠ matplotlib chưa được cài. Chạy: pip install matplotlib")
            )

    def reset(self) -> None:
        """Clear chart and history."""
        if not _MPL:
            return
        self._history = []
        self._ax.clear()
        self._ax.set_xlabel("Vòng lặp", fontsize=9)
        self._ax.set_ylabel("gBest Fitness", fontsize=9)
        self._ax.set_title("Đồ thị hội tụ PSO", fontsize=10)
        self._ax.grid(True, alpha=0.3)
        self._canvas.draw()

    def append(self, fitness: float) -> None:
        """Append one data point and redraw (uses draw_idle for efficiency)."""
        if not _MPL:
            return
        self._history.append(fitness)
        self._redraw()

    def set_history(self, history: list[float]) -> None:
        """Bulk-replace history (used when restoring session state)."""
        if not _MPL:
            return
        self._history = list(history)
        self._redraw()

    def _redraw(self) -> None:
        self._ax.clear()
        if self._history:
            x = list(range(len(self._history)))
            self._ax.plot(x, self._history, color="#2471A3", lw=1.6)
            self._ax.fill_between(x, self._history, alpha=0.10, color="#2471A3")
            self._ax.set_title(
                f"Đồ thị hội tụ PSO  —  gBest = {self._history[-1]:.6g}",
                fontsize=10,
            )
        else:
            self._ax.set_title("Đồ thị hội tụ PSO", fontsize=10)
        self._ax.set_xlabel("Vòng lặp", fontsize=9)
        self._ax.set_ylabel("gBest Fitness", fontsize=9)
        self._ax.grid(True, alpha=0.3)
        self._fig.tight_layout(pad=1.0)
        self._canvas.draw_idle()

    def get_figure_bytes(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
        return buf.getvalue()


# ─── Main view widget ─────────────────────────────────────────────────────────


class _PSOView(_WidgetBase):  # type: ignore[valid-type]
    """Root QWidget for the PSO module — built in build_view()."""

    def __init__(self, module: "ParticleSwarmOptimizationModule") -> None:
        super().__init__()
        if not _QT:
            return
        self._module = module
        self._worker = None
        self._sim_running: bool = False
        self._total_iters: int = 100
        self._last_all_positions: list[list[float]] = []   # last frame from worker
        self._last_result: dict | None = None
        self._particle_canvas: _ParticleCanvas | None = None
        self._convergence_canvas: _ConvergenceCanvas | None = None
        # Trajectory state
        self._trajectories: list[list[list[float]]] = []  # [frame_t][particle_i][coord]
        self._view_mode: str = "animation"                # "animation"|"full_trail"|"short_tail"
        self._build_ui()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        # ── Left: scrollable control panel ───────────────────────────────────
        ctrl_scroll = QScrollArea()
        ctrl_scroll.setWidgetResizable(True)
        ctrl_scroll.setFixedWidth(_CTRL_WIDTH)
        ctrl_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        ctrl_scroll.setFrameShape(QFrame.Shape.NoFrame)

        ctrl_inner = QWidget()
        ctrl_layout = QVBoxLayout(ctrl_inner)
        ctrl_layout.setContentsMargins(4, 4, 4, 4)
        ctrl_layout.setSpacing(6)
        ctrl_scroll.setWidget(ctrl_inner)

        # Helper: labelled row
        def _lrow(lbl_text: str, widget: QWidget, lbl_w: int = 120) -> QHBoxLayout:
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            lbl = QLabel(lbl_text)
            lbl.setMinimumWidth(lbl_w)
            row.addWidget(lbl)
            row.addWidget(widget, stretch=1)
            return row

        # ── Group: Function & Search space ───────────────────────────────────
        grp_func = QGroupBox("Hàm & Không gian tìm kiếm")
        g1 = QVBoxLayout(grp_func)
        g1.setSpacing(4)

        self._combo_func = QComboBox()
        for key, label in list_functions():
            self._combo_func.addItem(label, key)
        g1.addWidget(QLabel("Hàm mục tiêu:"))
        g1.addWidget(self._combo_func)

        self._spin_dim = QSpinBox()
        self._spin_dim.setRange(1, 30)
        self._spin_dim.setValue(2)
        self._spin_dim.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g1.addLayout(_lrow("Số chiều:", self._spin_dim))

        self._spin_lb = QDoubleSpinBox()
        self._spin_lb.setRange(-1000.0, 0.0)
        self._spin_lb.setValue(-5.12)
        self._spin_lb.setDecimals(3)
        self._spin_lb.setSingleStep(0.5)
        self._spin_lb.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g1.addLayout(_lrow("Cận dưới:", self._spin_lb))

        self._spin_ub = QDoubleSpinBox()
        self._spin_ub.setRange(0.0, 1000.0)
        self._spin_ub.setValue(5.12)
        self._spin_ub.setDecimals(3)
        self._spin_ub.setSingleStep(0.5)
        self._spin_ub.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g1.addLayout(_lrow("Cận trên:", self._spin_ub))

        ctrl_layout.addWidget(grp_func)

        # ── Group: PSO parameters ─────────────────────────────────────────────
        grp_pso = QGroupBox("Tham số PSO")
        g2 = QVBoxLayout(grp_pso)
        g2.setSpacing(4)

        self._spin_n = QSpinBox()
        self._spin_n.setRange(5, 500)
        self._spin_n.setValue(30)
        self._spin_n.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g2.addLayout(_lrow("Số hạt:", self._spin_n))

        self._spin_iter = QSpinBox()
        self._spin_iter.setRange(10, 5000)
        self._spin_iter.setValue(100)
        self._spin_iter.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g2.addLayout(_lrow("Số vòng lặp:", self._spin_iter))

        self._spin_w_start = QDoubleSpinBox()
        self._spin_w_start.setRange(0.0, 2.0)
        self._spin_w_start.setValue(0.9)
        self._spin_w_start.setSingleStep(0.05)
        self._spin_w_start.setDecimals(2)
        self._spin_w_start.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g2.addLayout(_lrow("w_start:", self._spin_w_start))

        self._spin_w_end = QDoubleSpinBox()
        self._spin_w_end.setRange(0.0, 2.0)
        self._spin_w_end.setValue(0.4)
        self._spin_w_end.setSingleStep(0.05)
        self._spin_w_end.setDecimals(2)
        self._spin_w_end.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g2.addLayout(_lrow("w_end:", self._spin_w_end))

        self._spin_c1 = QDoubleSpinBox()
        self._spin_c1.setRange(0.0, 4.0)
        self._spin_c1.setValue(1.5)
        self._spin_c1.setSingleStep(0.1)
        self._spin_c1.setDecimals(2)
        self._spin_c1.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g2.addLayout(_lrow("c₁ (cá nhân):", self._spin_c1))

        self._spin_c2 = QDoubleSpinBox()
        self._spin_c2.setRange(0.0, 4.0)
        self._spin_c2.setValue(1.5)
        self._spin_c2.setSingleStep(0.1)
        self._spin_c2.setDecimals(2)
        self._spin_c2.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        g2.addLayout(_lrow("c₂ (xã hội):", self._spin_c2))

        self._spin_vmax = QDoubleSpinBox()
        self._spin_vmax.setRange(0.01, 1.0)
        self._spin_vmax.setValue(0.20)
        self._spin_vmax.setSingleStep(0.05)
        self._spin_vmax.setDecimals(2)
        self._spin_vmax.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_vmax.setToolTip("Vmax = tỷ lệ × (cận trên − cận dưới)")
        g2.addLayout(_lrow("Vmax (tỷ lệ):", self._spin_vmax))

        self._combo_topo = QComboBox()
        self._combo_topo.addItem("Star (toàn cục)", "star")
        self._combo_topo.addItem("Ring (láng giềng)", "ring")
        g2.addLayout(_lrow("Topology:", self._combo_topo))

        self._combo_boundary = QComboBox()
        self._combo_boundary.addItem("Clipping (cắt biên)", "clip")
        self._combo_boundary.addItem("Reflection (phản xạ)", "reflect")
        g2.addLayout(_lrow("Xử lý biên:", self._combo_boundary))

        self._spin_seed = QSpinBox()
        self._spin_seed.setRange(0, 99999)
        self._spin_seed.setValue(42)
        self._spin_seed.setSpecialValueText("ngẫu nhiên")
        self._spin_seed.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_seed.setToolTip("0 = seed ngẫu nhiên mỗi lần chạy")
        g2.addLayout(_lrow("Seed:", self._spin_seed))

        ctrl_layout.addWidget(grp_pso)

        # ── Group: Display and Speed ──────────────────────────────────────────
        grp_display = QGroupBox("Hiển thị & Tốc độ")
        g4 = QVBoxLayout(grp_display)
        g4.setSpacing(4)

        self._spin_delay = QSpinBox()
        self._spin_delay.setRange(0, 2000)
        self._spin_delay.setValue(_DEFAULT_DELAY_MS)
        self._spin_delay.setSingleStep(10)
        self._spin_delay.setSuffix(" ms")
        self._spin_delay.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_delay.setToolTip("Thời gian chờ giữa các bước (0 = nhanh nhất)")
        g4.addLayout(_lrow("Trễ/bước:", self._spin_delay))

        g4.addWidget(QLabel("Chế độ xem:"))

        _mode_style = (
            "QPushButton{padding:4px 6px;border-radius:3px;"
            "border:1px solid #BDC3C7;text-align:left;}"
            "QPushButton:checked{background:#2471A3;color:white;"
            "border-color:#1A5276;font-weight:bold;}"
            "QPushButton:hover:!checked{background:#D6EAF8;}"
        )
        self._btn_mode_anim = QPushButton("▶  Animation")
        self._btn_mode_anim.setCheckable(True)
        self._btn_mode_anim.setChecked(True)
        self._btn_mode_anim.setToolTip("Hiện vị trí hạt theo từng bước (không quỹ đạo)")
        self._btn_mode_anim.setStyleSheet(_mode_style)

        self._btn_mode_full = QPushButton("↝  Quỹ đạo đầy đủ")
        self._btn_mode_full.setCheckable(True)
        self._btn_mode_full.setChecked(False)
        self._btn_mode_full.setToolTip("Hiện toàn bộ đường đi từ đầu đến hiện tại")
        self._btn_mode_full.setStyleSheet(_mode_style)

        self._btn_mode_tail = QPushButton("〰  Đuôi chuyển động")
        self._btn_mode_tail.setCheckable(True)
        self._btn_mode_tail.setChecked(False)
        self._btn_mode_tail.setToolTip(
            "Hiện đuôi ngắn (y bước gần nhất) của mỗi hạt"
        )
        self._btn_mode_tail.setStyleSheet(_mode_style)

        for _b in (self._btn_mode_anim, self._btn_mode_full, self._btn_mode_tail):
            g4.addWidget(_b)

        self._spin_n_display = QSpinBox()
        self._spin_n_display.setRange(0, 500)
        self._spin_n_display.setValue(0)
        self._spin_n_display.setSpecialValueText("Tất cả")
        self._spin_n_display.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_n_display.setToolTip(
            "Hiện quỹ đạo / scatter cho x hạt đầu (0 = tất cả)"
        )
        g4.addLayout(_lrow("Số hạt hiển thị:", self._spin_n_display))

        self._spin_tail_len = QSpinBox()
        self._spin_tail_len.setRange(2, 200)
        self._spin_tail_len.setValue(10)
        self._spin_tail_len.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_tail_len.setToolTip(
            "Số bước gần nhất hiển thị trong chế độ Đuôi chuyển động"
        )
        self._spin_tail_len.setEnabled(False)
        g4.addLayout(_lrow("Độ dài đuôi:", self._spin_tail_len))

        ctrl_layout.addWidget(grp_display)

        # ── Run / Stop buttons ────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(9, 0, 9, 0)
        self._btn_run = QPushButton("▶  Chạy")
        self._btn_run.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_run.setStyleSheet(
            "QPushButton{background:#2471A3;color:white;font-weight:bold;"
            "padding:5px 8px;border-radius:4px;}"
            "QPushButton:hover{background:#1A5276;}"
            "QPushButton:disabled{background:#BDC3C7;color:#7F8C8D;}"
        )
        self._btn_stop = QPushButton("■  Dừng")
        self._btn_stop.setEnabled(False)
        self._btn_stop.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn_stop.setStyleSheet(
            "QPushButton{background:#C0392B;color:white;font-weight:bold;"
            "padding:5px 8px;border-radius:4px;}"
            "QPushButton:disabled{background:#BDC3C7;color:#7F8C8D;}"
        )
        btn_row.addWidget(self._btn_run)
        btn_row.addWidget(self._btn_stop)
        ctrl_layout.addLayout(btn_row)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        self._progress.setValue(0)
        self._progress.setTextVisible(True)
        ctrl_layout.addWidget(self._progress)

        # ── Export buttons ────────────────────────────────────────────────────
        _export_btn_style = (
            "QPushButton{padding:4px 6px;border-radius:3px;"
            "border:1px solid #BDC3C7;text-align:left;}"
            "QPushButton:hover:!disabled{background:#D6EAF8;}"
            "QPushButton:disabled{color:#95A5A6;border-color:#D5D8DC;}"
        )
        grp_export = QGroupBox("Xuất hình ảnh")
        g_exp = QVBoxLayout(grp_export)
        g_exp.setSpacing(4)

        self._btn_export_scatter = QPushButton("📷  Xuất scatter 2D")
        self._btn_export_scatter.setEnabled(False)
        self._btn_export_scatter.setStyleSheet(_export_btn_style)
        g_exp.addWidget(self._btn_export_scatter)

        self._btn_export_convergence = QPushButton("📷  Xuất đồ thị hội tụ")
        self._btn_export_convergence.setEnabled(False)
        self._btn_export_convergence.setStyleSheet(_export_btn_style)
        g_exp.addWidget(self._btn_export_convergence)

        ctrl_layout.addWidget(grp_export)

        # ── Result panel ──────────────────────────────────────────────────────
        grp_result = QGroupBox("Kết quả")
        g3 = QVBoxLayout(grp_result)
        g3.setSpacing(3)

        self._lbl_fitness = QLabel("gBest fitness: —")
        self._lbl_fitness.setStyleSheet(_MONO_STYLE)
        self._lbl_fitness.setWordWrap(True)

        self._lbl_pos = QLabel("gBest vị trí: —")
        self._lbl_pos.setStyleSheet(_MONO_STYLE)
        self._lbl_pos.setWordWrap(True)

        self._lbl_iters = QLabel("Vòng lặp: —")
        self._lbl_iters.setStyleSheet(_MONO_STYLE)

        self._lbl_status = QLabel("Trạng thái: Chờ")
        self._lbl_status.setStyleSheet(_MONO_STYLE + " color:#7F8C8D;")

        for w in (self._lbl_fitness, self._lbl_pos, self._lbl_iters, self._lbl_status):
            g3.addWidget(w)

        ctrl_layout.addWidget(grp_result)
        ctrl_layout.addStretch()

        root_layout.addWidget(ctrl_scroll)

        # ── Right: tabs ───────────────────────────────────────────────────────
        self._tabs = QTabWidget()
        self._tabs.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        self._particle_canvas = _ParticleCanvas()
        self._tabs.addTab(self._particle_canvas, "Không gian 2D")

        self._convergence_canvas = _ConvergenceCanvas()
        self._convergence_canvas.reset()
        self._tabs.addTab(self._convergence_canvas, "Đồ thị hội tụ")

        root_layout.addWidget(self._tabs, stretch=1)

        # ── Wire signals ──────────────────────────────────────────────────────
        self._btn_run.clicked.connect(self._on_run)
        self._btn_stop.clicked.connect(self._on_stop)
        self._btn_export_scatter.clicked.connect(self._on_export_scatter)
        self._btn_export_convergence.clicked.connect(self._on_export_convergence)
        self._combo_func.currentIndexChanged.connect(self._on_func_changed)
        self._spin_dim.valueChanged.connect(self._on_dim_changed)
        self._btn_mode_anim.clicked.connect(lambda: self._set_view_mode("animation"))
        self._btn_mode_full.clicked.connect(lambda: self._set_view_mode("full_trail"))
        self._btn_mode_tail.clicked.connect(lambda: self._set_view_mode("short_tail"))

        # Apply initial state from function suggestion
        self._on_func_changed()

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_func_changed(self) -> None:
        """Suggest appropriate bounds when the objective function changes."""
        obj_key = self._combo_func.currentData()
        try:
            func = get_function(obj_key)
            lb, ub = func.suggested_bounds
            self._spin_lb.setValue(lb)
            self._spin_ub.setValue(ub)
        except Exception:
            pass

    def _on_dim_changed(self, value: int) -> None:
        if hasattr(self, "_tabs"):
            label = "Không gian 2D" if value == 2 else "Không gian 2D  (chỉ khi dim=2)"
            self._tabs.setTabText(0, label)

    def _set_view_mode(self, mode: str) -> None:
        """Switch view mode and sync button checked states."""
        self._view_mode = mode
        self._btn_mode_anim.setChecked(mode == "animation")
        self._btn_mode_full.setChecked(mode == "full_trail")
        self._btn_mode_tail.setChecked(mode == "short_tail")
        self._spin_tail_len.setEnabled(mode == "short_tail")

    def _build_config(self) -> PSOConfig:
        """Read UI controls and return a PSOConfig."""
        seed_val = self._spin_seed.value()
        return PSOConfig(
            n_particles=self._spin_n.value(),
            n_dimensions=self._spin_dim.value(),
            n_iterations=self._spin_iter.value(),
            lower_bound=self._spin_lb.value(),
            upper_bound=self._spin_ub.value(),
            w_start=self._spin_w_start.value(),
            w_end=self._spin_w_end.value(),
            c1=self._spin_c1.value(),
            c2=self._spin_c2.value(),
            v_max_ratio=self._spin_vmax.value(),
            topology=self._combo_topo.currentData(),
            boundary=self._combo_boundary.currentData(),
            seed=seed_val if seed_val > 0 else None,
            objective=self._combo_func.currentData(),
            step_delay_ms=self._spin_delay.value(),
        )

    def _on_run(self) -> None:
        """Create SimulationWorker and start the background thread."""
        if self._sim_running:
            return

        from modules.logistics.particle_swarm_optimization.workers.simulation_worker import (
            SimulationWorker,
        )

        config = self._build_config()
        self._total_iters = config.n_iterations
        self._last_all_positions = []

        # Reset UI
        self._progress.setValue(0)
        self._lbl_status.setText("Trạng thái: Đang chạy…")
        self._lbl_status.setStyleSheet(_MONO_STYLE + " color:#27AE60;")
        self._btn_run.setEnabled(False)
        self._btn_stop.setEnabled(True)
        self._btn_export_scatter.setEnabled(False)
        self._btn_export_convergence.setEnabled(False)

        # Reset trajectory buffer and canvases
        self._trajectories = []
        self._convergence_canvas.reset()
        if config.n_dimensions == 2:
            self._particle_canvas.setup(
                config.objective,
                config.lower_bound,
                config.upper_bound,
            )

        # Create and start worker
        self._worker = SimulationWorker(config)
        self._worker.iteration_done.connect(self._on_iteration)
        self._worker.simulation_done.connect(self._on_done)
        self._worker.error_occurred.connect(self._on_error)
        self._worker.finished.connect(self._on_worker_finished)
        self._sim_running = True
        self._worker.start()

    def _on_stop(self) -> None:
        if self._worker is not None:
            self._worker.request_stop()
        self._lbl_status.setText("Trạng thái: Đang dừng…")

    def _on_iteration(
        self,
        iteration: int,
        gbest_fitness: float,
        gbest_pos: list,
        positions: list,
    ) -> None:
        """Slot called (on UI thread via Qt signal) for each PSO iteration."""
        self._last_all_positions = positions

        # Accumulate trajectory history (cap at _MAX_TRAJ_FRAMES to limit memory)
        if positions and len(positions[0]) >= 2:
            self._trajectories.append(positions)
            if len(self._trajectories) > _MAX_TRAJ_FRAMES:
                self._trajectories = self._trajectories[-_MAX_TRAJ_FRAMES:]

        # Progress bar
        pct = int(100 * iteration / max(1, self._total_iters))
        self._progress.setValue(pct)

        # Convergence chart — every iteration
        self._convergence_canvas.append(gbest_fitness)

        # Particle canvas:
        #   - trail modes: refresh every iteration (worker delay makes it smooth)
        #   - animation mode: throttle every _REDRAW_EVERY iters for performance
        if len(gbest_pos) >= 2:
            mode = self._view_mode
            do_draw = (
                mode in ("full_trail", "short_tail")
                or iteration % _REDRAW_EVERY == 0
            )
            if do_draw:
                self._particle_canvas.update_with_trails(
                    positions,
                    gbest_pos,
                    iteration,
                    self._trajectories,
                    mode,
                    self._spin_tail_len.value(),
                    self._spin_n_display.value(),
                )

        # Result labels
        self._lbl_fitness.setText(f"gBest fitness: {gbest_fitness:.8g}")
        pos_str = ", ".join(f"{v:.4f}" for v in gbest_pos[:6])
        if len(gbest_pos) > 6:
            pos_str += " …"
        self._lbl_pos.setText(f"gBest vị trí:\n[{pos_str}]")
        self._lbl_iters.setText(f"Vòng lặp: {iteration}/{self._total_iters}")

    def _on_done(self, result: dict) -> None:
        """Slot called when the simulation finishes."""
        self._last_result = result
        fitness = result["gbest_fitness"]
        pos: list[float] = result["gbest_position"]
        iters: int = result["iterations_done"]
        stopped: bool = result.get("stopped_early", False)

        self._progress.setValue(100 if not stopped else self._progress.value())

        # Final scatter refresh using current view mode
        if len(pos) >= 2 and self._last_all_positions:
            self._particle_canvas.update_with_trails(
                self._last_all_positions,
                pos,
                iters,
                self._trajectories,
                self._view_mode,
                self._spin_tail_len.value(),
                self._spin_n_display.value(),
            )

        pos_str = ", ".join(f"{v:.6f}" for v in pos[:6])
        if len(pos) > 6:
            pos_str += " …"

        self._lbl_fitness.setText(f"gBest fitness: {fitness:.8g}")
        self._lbl_pos.setText(f"gBest vị trí:\n[{pos_str}]")
        self._lbl_iters.setText(f"Vòng lặp: {iters}/{self._total_iters}")

        status = "Hoàn thành" if not stopped else "Đã dừng"
        self._lbl_status.setText(f"Trạng thái: {status}")
        self._lbl_status.setStyleSheet(
            _MONO_STYLE + " color:#2471A3; font-weight:bold;"
        )

        # Pass result to module for state persistence
        self._module._last_result = result

    def _on_error(self, msg: str) -> None:
        self._lbl_status.setText(f"Lỗi: {msg}")
        self._lbl_status.setStyleSheet(_MONO_STYLE + " color:#E74C3C;")
        self._module._logger.error(f"[pso] simulation error: {msg}")

    def _on_worker_finished(self) -> None:
        self._sim_running = False
        self._btn_run.setEnabled(True)
        self._btn_stop.setEnabled(False)
        self._btn_export_scatter.setEnabled(True)
        self._btn_export_convergence.setEnabled(True)
        self._worker = None

    # ── Export ────────────────────────────────────────────────────────────────

    def _on_export_scatter(self) -> None:
        try:
            data = self._particle_canvas.get_figure_bytes()
            if not data:
                return
            path = self._module._export_svc.ask_save_path(
                self,
                title="Xuất Scatter 2D",
                default_name="pso_scatter_2d.png",
                file_filter="PNG Image (*.png);;All Files (*)",
            )
            if path:
                self._module._export_svc.write_bytes(path, data)
                self._module._activity_svc.log(
                    "EXPORT_COMPLETED",
                    "PSO: pso_scatter_2d.png exported",
                    module_id=ParticleSwarmOptimizationModule.MODULE_ID,
                )
        except Exception as exc:
            self._module._logger.warning(f"[pso] export scatter failed: {exc}")

    def _on_export_convergence(self) -> None:
        try:
            data = self._convergence_canvas.get_figure_bytes()
            if not data:
                return
            path = self._module._export_svc.ask_save_path(
                self,
                title="Xuất Đồ thị Hội tụ",
                default_name="pso_convergence.png",
                file_filter="PNG Image (*.png);;All Files (*)",
            )
            if path:
                self._module._export_svc.write_bytes(path, data)
                self._module._activity_svc.log(
                    "EXPORT_COMPLETED",
                    "PSO: pso_convergence.png exported",
                    module_id=ParticleSwarmOptimizationModule.MODULE_ID,
                )
        except Exception as exc:
            self._module._logger.warning(f"[pso] export convergence failed: {exc}")

    # ── State helpers ─────────────────────────────────────────────────────────

    def get_ui_state(self) -> dict[str, Any]:
        """Snapshot current UI control values for persistence."""
        return {
            "objective": self._combo_func.currentData(),
            "n_dimensions": self._spin_dim.value(),
            "lower_bound": self._spin_lb.value(),
            "upper_bound": self._spin_ub.value(),
            "n_particles": self._spin_n.value(),
            "n_iterations": self._spin_iter.value(),
            "w_start": self._spin_w_start.value(),
            "w_end": self._spin_w_end.value(),
            "c1": self._spin_c1.value(),
            "c2": self._spin_c2.value(),
            "v_max_ratio": self._spin_vmax.value(),
            "topology": self._combo_topo.currentData(),
            "boundary": self._combo_boundary.currentData(),
            "seed": self._spin_seed.value(),
            "active_tab": self._tabs.currentIndex(),
            "step_delay_ms": self._spin_delay.value(),
            "view_mode": self._view_mode,
            "n_display_particles": self._spin_n_display.value(),
            "tail_length": self._spin_tail_len.value(),
        }

    def apply_ui_state(self, state: dict[str, Any]) -> None:
        """Restore UI controls from a saved state dict."""

        def _set_combo(combo: QComboBox, key: str) -> None:
            val = state.get(key)
            if val is None:
                return
            for i in range(combo.count()):
                if combo.itemData(i) == val:
                    combo.setCurrentIndex(i)
                    return

        _set_combo(self._combo_func, "objective")
        self._spin_dim.setValue(state.get("n_dimensions", 2))
        self._spin_lb.setValue(state.get("lower_bound", -5.12))
        self._spin_ub.setValue(state.get("upper_bound", 5.12))
        self._spin_n.setValue(state.get("n_particles", 30))
        self._spin_iter.setValue(state.get("n_iterations", 100))
        self._spin_w_start.setValue(state.get("w_start", 0.9))
        self._spin_w_end.setValue(state.get("w_end", 0.4))
        self._spin_c1.setValue(state.get("c1", 1.5))
        self._spin_c2.setValue(state.get("c2", 1.5))
        self._spin_vmax.setValue(state.get("v_max_ratio", 0.20))
        _set_combo(self._combo_topo, "topology")
        _set_combo(self._combo_boundary, "boundary")
        self._spin_seed.setValue(state.get("seed", 42))
        self._tabs.setCurrentIndex(state.get("active_tab", 0))
        self._spin_delay.setValue(state.get("step_delay_ms", _DEFAULT_DELAY_MS))
        self._spin_n_display.setValue(state.get("n_display_particles", 0))
        self._spin_tail_len.setValue(state.get("tail_length", 10))
        self._set_view_mode(state.get("view_mode", "animation"))


# ─── BaseModule implementation ────────────────────────────────────────────────


class ParticleSwarmOptimizationModule(BaseModule):
    """IIMP module — PSO Explorer v1.0.0.

    Hosts the full PSO simulation UI. The simulation runs in a background
    QThread (SimulationWorker) so the shell remains responsive at all times.
    """

    MODULE_ID = "particle_swarm_optimization"
    MODULE_NAME = "PSO — Tối ưu hóa Bầy đàn"
    MODULE_VERSION = "1.0.0"

    def __init__(self, manifest: dict, context: ModuleContext) -> None:
        super().__init__(manifest=manifest, context=context)
        self._logger = context.logger
        self._export_svc = context.export_service
        self._settings_svc = context.settings_service
        self._activity_svc = context.activity_service
        self._view: _PSOView | None = None
        self._last_result: dict | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_load")

    def build_view(self) -> Any:  # QWidget
        if self._view is None or not _qt_is_valid(self._view):
            self._view = _PSOView(self)
        return self._view

    def on_activate(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_activate")
        self._activity_svc.log(
            "MODULE_ACTIVATE",
            f"{self.MODULE_ID} activated",
            module_id=self.MODULE_ID,
        )

    def on_deactivate(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_deactivate")

    def on_unload(self) -> None:
        """Stop any running simulation worker before the module is unloaded."""
        if self._view is not None and self._view._worker is not None:
            self._view._worker.request_stop()
            self._view._worker.wait(3000)   # give up to 3 s for graceful exit
        self._logger.info(f"[{self.MODULE_ID}] on_unload")

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        state = default_state()
        if self._view is not None:
            state.update(self._view.get_ui_state())
        state["_state_version"] = STATE_VERSION
        if self._last_result:
            state["last_gbest_fitness"] = self._last_result.get("gbest_fitness")
            state["last_gbest_position"] = self._last_result.get("gbest_position")
            state["last_convergence"] = self._last_result.get("convergence_history", [])
        return state

    def restore_state(self, state: dict[str, Any]) -> None:
        if self._view is None:
            return
        self._view.apply_ui_state(state)

        # Restore convergence chart from last run if available
        conv: list[float] = state.get("last_convergence", [])
        if conv:
            self._view._convergence_canvas.set_history(conv)

        # Restore result labels
        fitness = state.get("last_gbest_fitness")
        pos: list[float] | None = state.get("last_gbest_position")
        if fitness is not None:
            self._view._lbl_fitness.setText(f"gBest fitness: {fitness:.8g}")
        if pos:
            pos_str = ", ".join(f"{v:.6f}" for v in pos[:6])
            if len(pos) > 6:
                pos_str += " …"
            self._view._lbl_pos.setText(f"gBest vị trí:\n[{pos_str}]")
        if conv:
            self._view._lbl_iters.setText(f"Vòng lặp: {len(conv) - 1}")
            self._view._lbl_status.setText("Trạng thái: Đã khôi phục")
            self._view._lbl_status.setStyleSheet(_MONO_STYLE + " color:#7F8C8D;")

        self._logger.debug(f"[{self.MODULE_ID}] restore_state done")
