"""Exponential Distribution Explorer — v1.0.0

Two simulation modes in a tab-panel layout:

  Tab 1  Phân phối Exp(μ)    — PDF curve with key statistics annotated;
                               vùng P(0≤X≤μ) ≈ 63,21% được tô màu.
  Tab 2  Tính xác suất        — Nhập a, b; tính đồng thời P(X≤a),
                               P(a≤X≤b) và P(X>b); tô màu 3 vùng.

Phân phối mũ Exp(μ):
  PDF  : f(x) = λ·exp(−λx),   x ≥ 0,   λ = 1/μ
  CDF  : F(x) = 1 − exp(−λx)
  Trung bình  : E[X] = μ = 1/λ
  Phương sai  : Var[X] = μ² = 1/λ²
  Trung vị    : m = μ·ln 2
  Tính chất không nhớ: P(X>s+t | X>s) = P(X>t)
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np
from scipy.stats import expon

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
        QDoubleSpinBox,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QScrollArea,
        QSizePolicy,
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

# Give the canvas a fallback base when Qt is unavailable (unit tests)
_CanvasBase = QWidget if _QT else object  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Canvas — renders both simulation modes
# ---------------------------------------------------------------------------


class _ExpCurveCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Embedded matplotlib Figure for rendering exponential distribution diagrams."""

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _MPL:
            self._figure = Figure(figsize=(10, 5.5), dpi=100)
            self._ax = self._figure.add_subplot(111)
            self._canvas = FigureCanvas(self._figure)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
        else:
            layout.addWidget(
                QLabel("⚠ matplotlib chưa được cài. Chạy: pip install matplotlib")
            )

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _decorate(ax) -> None:
        """Minimal axes decoration: remove 3 spines, keep bottom at y=0."""
        for sp in ("left", "right", "top"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_position(("data", 0))
        ax.set_yticks([])

    @staticmethod
    def _f(v: float, p: int) -> str:
        return f"{v:.{p}f}"

    @staticmethod
    def _safe_xticks(
        tick_dict: "dict[float, str]",
        x_max: float,
        rel_tol: float = 0.055,
    ) -> "tuple[list[float], list[str]]":
        """Merge tick entries that are too close together to prevent label overlap.

        Any entries within ``rel_tol * x_max`` of the previous kept tick are
        collapsed: their labels are joined with a newline and placed at the
        first value in the group.
        """
        if not tick_dict:
            return [], []
        items = sorted(tick_dict.items())
        threshold = max(rel_tol * x_max, 1e-12)
        out: list[tuple[float, str]] = []
        i = 0
        while i < len(items):
            v0, l0 = items[i]
            lbls = [l0]
            j = i + 1
            while j < len(items) and (items[j][0] - v0) < threshold:
                lbls.append(items[j][1])
                j += 1
            # Place merged label at the LAST (largest) value in the group so
            # the tick aligns with the rightmost statistical line (e.g. μ, not Me).
            v_pos = items[j - 1][0]
            out.append((v_pos, "\n".join(lbls)))
            i = j
        return [t for t, _ in out], [lbl for _, lbl in out]

    # ── Mode 1: Phân phối Exp(μ) ──────────────────────────────────────────────

    def render_distribution(self, mu: float, precision: int = 4) -> str:
        """Draw Exp(μ) PDF with key statistics annotated. Returns result text."""
        if not _MPL:
            return ""

        lam = 1.0 / mu
        median = mu * np.log(2.0)
        variance = mu ** 2

        ax = self._ax
        ax.clear()

        x_max = 5.5 * mu
        xs = np.linspace(0.0, x_max, 2000)
        ys = expon.pdf(xs, scale=mu)
        y_peak = float(expon.pdf(0.0, scale=mu))  # = λ = 1/μ

        # Main curve
        ax.plot(xs, ys, color="#2C3E50", lw=2.0, zorder=6)

        # Shade P(0 ≤ X ≤ μ) ≈ 63,21%
        mask_mu = (xs >= 0.0) & (xs <= mu)
        ax.fill_between(xs, ys, where=mask_mu, color="#2471A3", alpha=0.45, zorder=4)

        # Lightly shade P(μ < X ≤ 2μ) for visual context
        mask_2mu = (xs > mu) & (xs <= 2.0 * mu)
        ax.fill_between(xs, ys, where=mask_2mu, color="#5DADE2", alpha=0.22, zorder=3)

        # Vertical line at mean μ
        ax.axvline(
            mu, color="#E74C3C", linestyle="--", lw=1.5, zorder=7, alpha=0.88
        )
        # Vertical line at median
        ax.axvline(
            median, color="#27AE60", linestyle=":", lw=1.3, zorder=7, alpha=0.85
        )

        self._decorate(ax)

        pr = max(2, precision - 1)

        # X-axis ticks: 0, μ, 2μ, 3μ
        tick_dict = {
            0.0: "0",
            mu: f"μ={self._f(mu, pr)}",
            2.0 * mu: f"2μ={self._f(2.0 * mu, pr)}",
            3.0 * mu: f"3μ={self._f(3.0 * mu, pr)}",
        }
        ticks, tick_labels = self._safe_xticks(tick_dict, x_max)
        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, fontsize=8.5)

        p_0_mu = float(expon.cdf(mu, scale=mu))     # 1 − 1/e ≈ 0.6321
        p_0_2mu = float(expon.cdf(2.0 * mu, scale=mu))  # 1 − 1/e² ≈ 0.8647

        # Place percentage label inside the shaded band [0, μ]
        x_txt = mu * 0.38
        y_txt = float(expon.pdf(x_txt, scale=mu)) * 0.42
        ax.text(
            x_txt, y_txt,
            f"{p_0_mu * 100:.2f}%",
            ha="center", va="center", fontsize=11, color="#1A5276",
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="#1A5276", alpha=0.88),
        )

        self._figure.tight_layout(pad=1.0)
        self._canvas.draw()

        p = precision
        return (
            f"μ (Trung bình)   = {self._f(mu, p)}\n"
            f"λ (Tốc độ)       = {self._f(lam, p)}\n"
            f"σ² (Phương sai)  = {self._f(variance, p)}\n"
            f"σ  (Độ lệch chuẩn) = {self._f(mu, p)}\n"
            f"Trung vị (Me)    = {self._f(median, p)}\n\n"
            f"P(0 ≤ X ≤ μ)    = {self._f(p_0_mu, p)}  ≈ 63,21%\n"
            f"P(0 ≤ X ≤ 2μ)   = {self._f(p_0_2mu, p)}  ≈ 86,47%"
        )

    # ── Mode 1 (multi): Overlay nhiều Exp(μ) ─────────────────────────────────

    #: Color palette for multi-distribution overlay (index 0 = primary)
    _OVERLAY_COLORS = [
        "#2471A3",  # blue   — primary
        "#E74C3C",  # red
        "#27AE60",  # green
        "#8E44AD",  # purple
        "#F39C12",  # orange
        "#1ABC9C",  # teal
        "#D35400",  # dark orange
        "#2C3E50",  # charcoal
    ]

    def render_multi_distribution(
        self,
        mus: "list[float]",
        precision: int = 4,
    ) -> str:
        """Draw multiple Exp(μ) curves on the same axes.

        If ``mus`` contains exactly one entry, delegates to
        :meth:`render_distribution` so the shading bands are preserved.
        For two or more curves each distribution gets a distinct color and
        a legend entry; shading is omitted to avoid visual clutter.
        """
        if not mus:
            return ""
        if len(mus) == 1:
            return self.render_distribution(mus[0], precision)
        if not _MPL:
            return ""

        ax = self._ax
        ax.clear()

        x_max = max(5.5 * mu for mu in mus)
        xs = np.linspace(0.0, x_max, 2000)

        result_lines: list[str] = []
        p = precision
        for i, mu in enumerate(mus):
            color = self._OVERLAY_COLORS[i % len(self._OVERLAY_COLORS)]
            ys = expon.pdf(xs, scale=mu)
            lam = 1.0 / mu
            lbl = f"Exp(μ={self._f(mu, p)}, λ={self._f(lam, p)})"
            ax.plot(xs, ys, color=color, lw=2.0, label=lbl, zorder=5 + i)
            ax.axvline(
                mu, color=color, linestyle="--", lw=0.9,
                ymax=0.92, zorder=4 + i, alpha=0.7,
            )
            result_lines.append(lbl)

        self._decorate(ax)
        ax.legend(loc="upper right", fontsize=8.5, framealpha=0.92, edgecolor="#BDC3C7")

        self._figure.tight_layout(pad=1.0)
        self._canvas.draw()

        return "\n".join(result_lines)

    # ── Mode 2: x → Xác suất ─────────────────────────────────────────────────

    def render_x_to_prob(
        self,
        mu: float,
        x_a: float = 0.0,
        x_b: float = 1.0,
        precision: int = 4,
    ) -> str:
        """Draw Exp(μ) PDF with three shaded regions. Returns result text.

        Blue  [0, a]  → P(X ≤ a)
        Green [a, b]  → P(a ≤ X ≤ b)
        Gray  (b, ∞)  → P(X > b)
        """
        if not _MPL:
            return ""

        x_a = max(x_a, 0.0)
        x_b = max(x_b, x_a)

        ax = self._ax
        ax.clear()

        x_max = max(5.5 * mu, x_b + 1.5 * mu)
        xs = np.linspace(0.0, x_max, 2000)
        ys = expon.pdf(xs, scale=mu)

        ax.plot(xs, ys, color="#2C3E50", lw=2.0, zorder=5)

        p = precision
        p_left = float(expon.cdf(x_a, scale=mu))
        p_mid = float(expon.cdf(x_b, scale=mu) - expon.cdf(x_a, scale=mu))
        p_right = float(expon.sf(x_b, scale=mu))

        # Region [0, a]: blue → P(X ≤ a)
        ax.fill_between(xs, ys, where=(xs <= x_a),
                        color="#2471A3", alpha=0.58, zorder=3)
        # Region [a, b]: green → P(a ≤ X ≤ b)
        ax.fill_between(xs, ys, where=((xs >= x_a) & (xs <= x_b)),
                        color="#27AE60", alpha=0.60, zorder=3)
        # Region (b, ∞): gray → P(X > b)
        ax.fill_between(xs, ys, where=(xs > x_b),
                        color="#D5DBDB", alpha=0.35, zorder=2)

        ax.axvline(x_a, color="#2471A3", linestyle="--", lw=1.4, zorder=7, alpha=0.9)
        ax.axvline(x_b, color="#27AE60", linestyle="--", lw=1.4, zorder=7, alpha=0.9)

        tick_dict: dict[float, str] = {
            0.0: "0",
            x_b: f"b={self._f(x_b, p)}",
            mu: f"μ={self._f(mu, p)}",
        }
        if x_a > 0.0:
            tick_dict[x_a] = f"a={self._f(x_a, p)}"
        ticks_f, labels_f = self._safe_xticks(tick_dict, x_max)
        ax.set_xticks(ticks_f)
        ax.set_xticklabels(labels_f, fontsize=9.5, fontweight="bold")
        ax.set_title(
            f"P(a ≤ X ≤ b) = {self._f(p_mid, p)}",
            fontsize=12, fontweight="bold", pad=10,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#27AE60", alpha=0.90),
        )

        result_text = (
            f"μ = {self._f(mu, p)},  λ = {self._f(1.0 / mu, p)}\n"
            f"a = {self._f(x_a, p)},  b = {self._f(x_b, p)}\n\n"
            f"P(X ≤ a)      = {self._f(p_left, p)}\n"
            f"P(a ≤ X ≤ b)  = {self._f(p_mid, p)}\n"
            f"P(X > b)      = {self._f(p_right, p)}\n"
            f"Tổng          = {self._f(p_left + p_mid + p_right, p)}"
        )

        self._decorate(ax)
        self._figure.tight_layout(pad=1.0, rect=[0, 0, 1, 0.87])
        self._canvas.draw()
        return result_text

    # ── Export ────────────────────────────────────────────────────────────────

    def get_figure_bytes(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._figure.savefig(buf, format="png", dpi=300, bbox_inches="tight")
        return buf.getvalue()


# ---------------------------------------------------------------------------
# Module
# ---------------------------------------------------------------------------


class ExponentialDistributionModule(BaseModule):
    """IIMP module — Exponential Distribution Explorer v1.0.0.

    Two simulation modes:
      Tab 0  Phân phối Exp(μ)  — PDF curve with statistics and shaded P(0≤X≤μ)
      Tab 1  Tính xác suất     — Nhập a, b; tính P(X≤a), P(a≤X≤b), P(X>b)
    """

    MODULE_ID = "exponential_distribution"
    MODULE_NAME = "Exponential Distribution Explorer"
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

    def __init__(self, manifest: dict, context: ModuleContext) -> None:
        super().__init__(manifest=manifest, context=context)
        self._logger = context.logger
        self._export_svc = context.export_service
        self._settings_svc = context.settings_service
        self._activity_svc = context.activity_service

        # Persisted state
        self._mu: float = 1.0
        self._tab: int = 0
        self._x_a: float = 0.0
        self._x_b: float = 1.0
        self._precision: int = 4

        # Tab 0 overlay: additional Exp(μ) distributions drawn simultaneously
        self._overlay_mus: list[float] = []

        # UI refs — assigned in build_view
        self._view: "QWidget | None" = None
        self._canvas: _ExpCurveCanvas | None = None
        self._mu_spin: "QDoubleSpinBox | None" = None
        self._tab_widget: "QTabWidget | None" = None
        self._xa_spin: "QDoubleSpinBox | None" = None
        self._xb_spin: "QDoubleSpinBox | None" = None
        self._result_label: "QLabel | None" = None
        # Tab 0 overlay UI refs
        self._mu_add_spin: "QDoubleSpinBox | None" = None
        self._dist_list_frame: "QWidget | None" = None
        self._dist_list_layout: "QVBoxLayout | None" = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_load")
        raw = self._settings_svc.get_module_setting(self.MODULE_ID, "precision")
        if raw is not None:
            try:
                self._precision = int(raw)
            except (TypeError, ValueError):
                pass

    def build_view(self) -> "QWidget":
        """Build and return the main module widget."""
        root = QWidget()
        root.setObjectName("expModuleRoot")
        root.setProperty("moduleShell", "root")
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        control_panel = self._build_control_panel()
        control_panel.setProperty("moduleShell", "sidebar")
        control_panel.setFixedWidth(285)
        main_layout.addWidget(control_panel)

        self._canvas = _ExpCurveCanvas()
        main_layout.addWidget(self._canvas, stretch=1)

        self._view = root

        # Remove ▲▼ step buttons from every spinbox — user types values manually
        for spin in root.findChildren(QDoubleSpinBox):
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        self._update_plot()
        return root

    def on_activate(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] activated")

    def on_deactivate(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] deactivated")

    def on_unload(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] unloaded")

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict[str, Any]:
        return {
            "mu": self._mu,
            "tab": self._tab,
            "x_a": self._x_a,
            "x_b": self._x_b,
            "precision": self._precision,
            "overlay_mus": list(self._overlay_mus),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self._mu = max(float(state.get("mu", 1.0)), 0.001)
        self._tab = int(state.get("tab", 0))
        self._x_a = max(float(state.get("x_a", 0.0)), 0.0)
        self._x_b = max(float(state.get("x_b", 1.0)), self._x_a)
        self._precision = int(state.get("precision", 4))
        raw_overlays = state.get("overlay_mus", [])
        self._overlay_mus = [
            max(float(v), 0.001)
            for v in raw_overlays
            if isinstance(v, (int, float))
        ]
        self._logger.debug(f"[{self.MODULE_ID}] state restored")

        # Sync UI if already built
        if self._mu_spin is not None:
            self._mu_spin.setValue(self._mu)
        if self._tab_widget is not None:
            self._tab_widget.setCurrentIndex(self._tab)
        if self._xa_spin is not None:
            self._xa_spin.setValue(self._x_a)
        if self._xb_spin is not None:
            self._xb_spin.setValue(self._x_b)
        self._refresh_dist_list_ui()
        self._update_plot()

    # ── Export ────────────────────────────────────────────────────────────────

    def export(self, target_path: str, export_type: str = "png") -> None:
        if self._canvas is None:
            return
        data = self._canvas.get_figure_bytes()
        if not data:
            self._logger.warning(f"[{self.MODULE_ID}] export: no figure bytes")
            return
        with open(target_path, "wb") as fh:
            fh.write(data)
        self._logger.info(f"[{self.MODULE_ID}] exported → {target_path}")
        if self._activity_svc:
            try:
                from core.utils.constants import ActivityType

                self._activity_svc.log(
                    ActivityType.EXPORT_COMPLETED,
                    f"Exported → {target_path}",
                    module_id=self.MODULE_ID,
                )
            except Exception:  # noqa: BLE001
                pass

    # ── Computation helpers (pure — no Qt, no canvas, fully testable) ─────────

    @staticmethod
    def _compute_single(mu: float, x: float) -> tuple[float, float]:
        """Return (P(X≤x), P(X>x)) for Exp(mu).

        x is clamped to 0 when negative (Exp is undefined for x<0).
        """
        x_clamped = max(x, 0.0)
        p_cdf = float(expon.cdf(x_clamped, scale=mu))
        p_sf = float(expon.sf(x_clamped, scale=mu))
        return p_cdf, p_sf

    @staticmethod
    def _compute_interval(mu: float, a: float, b: float) -> tuple[float, float, float]:
        """Return (P(X<a), P(a≤X≤b), P(X>b)) for Exp(mu).

        a and b are clamped to ≥ 0; b is clamped to ≥ a.
        """
        a = max(a, 0.0)
        b = max(b, a)
        p_left = float(expon.cdf(a, scale=mu))
        p_mid = float(expon.cdf(b, scale=mu) - expon.cdf(a, scale=mu))
        p_right = float(expon.sf(b, scale=mu))
        return p_left, p_mid, p_right

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_control_panel(self) -> "QWidget":
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ── Distribution parameter ───────────────────────────────────────────
        params_group = QGroupBox("Tham số phân phối")
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(6)

        row_mu = QHBoxLayout()
        row_mu.addWidget(QLabel("μ (trung bình):"))
        mu_spin = QDoubleSpinBox()
        mu_spin.setRange(0.001, 10000.0)
        mu_spin.setDecimals(4)
        mu_spin.setSingleStep(0.5)
        mu_spin.setValue(self._mu)
        row_mu.addWidget(mu_spin)
        self._mu_spin = mu_spin
        params_layout.addLayout(row_mu)

        lam_hint = QLabel("(λ = 1/μ : tốc độ xảy ra sự kiện)")
        lam_hint.setProperty("moduleShell", "hint")
        params_layout.addWidget(lam_hint)

        layout.addWidget(params_group)

        # ── Tab widget: 2 simulation modes ──────────────────────────────────
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_tab_distribution(), "Phân phối")
        tabs.addTab(self._build_tab_x_to_prob(), "Tính xác suất")
        tabs.setCurrentIndex(self._tab)
        tabs.currentChanged.connect(self._on_tab_changed)
        self._tab_widget = tabs
        layout.addWidget(tabs)

        # ── Result display ───────────────────────────────────────────────────
        result_group = QGroupBox("Kết quả")
        result_layout = QVBoxLayout(result_group)
        result_label = QLabel("—")
        result_label.setWordWrap(True)
        result_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        result_label.setProperty("moduleShell", "result")
        result_label.setMinimumHeight(120)
        result_layout.addWidget(result_label)
        layout.addWidget(result_group)
        self._result_label = result_label

        # ── Action buttons ───────────────────────────────────────────────────
        btn_plot = QPushButton("▶  Vẽ đồ thị")
        btn_plot.setObjectName("btnPrimary")
        btn_plot.clicked.connect(self._on_plot_clicked)
        btn_plot.setToolTip("Vẽ phân phối Exp(μ) với các đặc trưng thống kê")
        layout.addWidget(btn_plot)

        btn_calc = QPushButton("🔍  Tính xác suất")
        btn_calc.setObjectName("btnPrimary")
        btn_calc.clicked.connect(self._on_calc_clicked)
        btn_calc.setToolTip("Chuyển sang tab x → Xác suất và tính ngay")
        layout.addWidget(btn_calc)

        btn_export = QPushButton("💾  Xuất PNG")
        btn_export.setObjectName("btnSecondary")
        btn_export.clicked.connect(self._on_export_clicked)
        layout.addWidget(btn_export)

        layout.addStretch()
        return panel

    def _build_tab_distribution(self) -> "QWidget":
        """Tab 0: Distribution overview — with multi-distribution overlay support."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(6)

        # ── Add-distribution group ───────────────────────────────────────────
        add_group = QGroupBox("Thêm phân phối overlay")
        add_layout = QVBoxLayout(add_group)
        add_layout.setSpacing(4)
        add_layout.setContentsMargins(8, 6, 8, 6)

        row_mu = QHBoxLayout()
        row_mu.addWidget(QLabel("μ:"))
        mu_add = QDoubleSpinBox()
        mu_add.setRange(0.001, 10000.0)
        mu_add.setDecimals(4)
        mu_add.setSingleStep(0.5)
        mu_add.setValue(1.0)
        row_mu.addWidget(mu_add)
        self._mu_add_spin = mu_add
        add_layout.addLayout(row_mu)

        btn_add = QPushButton("＋  Thêm vào biểu đồ")
        btn_add.setProperty("role", "secondary")
        btn_add.clicked.connect(self._on_add_dist_clicked)
        add_layout.addWidget(btn_add)
        layout.addWidget(add_group)

        # ── Overlay list header ──────────────────────────────────────────────
        header_row = QHBoxLayout()
        header_row.addWidget(QLabel("Overlay hiện tại:"))
        btn_clear = QPushButton("Xóa tất cả")
        btn_clear.setFixedHeight(22)
        btn_clear.setProperty("role", "subtle")
        btn_clear.clicked.connect(self._on_clear_dists_clicked)
        header_row.addStretch()
        header_row.addWidget(btn_clear)
        layout.addLayout(header_row)

        # ── Scrollable list ──────────────────────────────────────────────────
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(140)
        scroll.setFrameShape(QFrame.Shape.StyledPanel)

        dist_frame = QWidget()
        dist_layout = QVBoxLayout(dist_frame)
        dist_layout.setContentsMargins(4, 2, 4, 2)
        dist_layout.setSpacing(2)
        self._dist_list_frame = dist_frame
        self._dist_list_layout = dist_layout
        scroll.setWidget(dist_frame)
        layout.addWidget(scroll)

        # ── Hint ────────────────────────────────────────────────────────────
        hint = QLabel(
            "ℹ Phân phối chính dùng μ ở trên.\n"
            "  Vùng tô đậm chỉ hiển thị\n"
            "  khi không có overlay."
        )
        hint.setWordWrap(True)
        hint.setProperty("moduleShell", "hint")
        layout.addWidget(hint)
        layout.addStretch()

        self._refresh_dist_list_ui()
        return tab

    def _build_tab_x_to_prob(self) -> "QWidget":
        """Tab 1: Tính P(X≤a), P(a≤X≤b) và P(X>b) từ hai khoảng thời gian a, b."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 6)
        layout.setSpacing(6)

        layout.addWidget(QLabel("Khoảng thời gian a  (a ≥ 0):"))
        xa_spin = QDoubleSpinBox()
        xa_spin.setRange(0.0, 99999.0)
        xa_spin.setDecimals(4)
        xa_spin.setSingleStep(0.1)
        xa_spin.setValue(self._x_a)
        layout.addWidget(xa_spin)
        self._xa_spin = xa_spin

        layout.addWidget(QLabel("Khoảng thời gian b  (b ≥ a):"))
        xb_spin = QDoubleSpinBox()
        xb_spin.setRange(0.0, 99999.0)
        xb_spin.setDecimals(4)
        xb_spin.setSingleStep(0.1)
        xb_spin.setValue(self._x_b)
        layout.addWidget(xb_spin)
        self._xb_spin = xb_spin

        layout.addStretch()
        return tab

    # ── Overlay list helpers ──────────────────────────────────────────────────

    def _refresh_dist_list_ui(self) -> None:
        """Rebuild the scrollable overlay distribution list in Tab 0."""
        if self._dist_list_layout is None:
            return
        # Remove existing widgets
        while self._dist_list_layout.count():
            item = self._dist_list_layout.takeAt(0)
            if item is not None and item.widget() is not None:
                item.widget().deleteLater()

        if not self._overlay_mus:
            empty = QLabel("(chưa có overlay)")
            empty.setObjectName("mutedText")
            self._dist_list_layout.addWidget(empty)
            return

        colors = _ExpCurveCanvas._OVERLAY_COLORS
        p = self._precision
        for i, mu in enumerate(self._overlay_mus):
            color = colors[(i + 1) % len(colors)]
            row_w = QWidget()
            row = QHBoxLayout(row_w)
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(4)

            dot = QLabel("●")
            dot.setProperty("moduleShell", "overlayDot")
            palette = dot.palette()
            palette.setColor(QPalette.ColorRole.WindowText, QColor(color))
            dot.setPalette(palette)
            dot.setFixedWidth(18)
            row.addWidget(dot)

            lbl = QLabel(f"Exp(μ={mu:.{p}f})")
            lbl.setProperty("moduleShell", "hint")
            row.addWidget(lbl, stretch=1)

            btn_rm = QPushButton("×")
            btn_rm.setFixedSize(22, 22)
            btn_rm.setObjectName("overlayRemoveButton")
            btn_rm.clicked.connect(
                lambda _checked=False, idx=i: self._on_remove_dist_clicked(idx)
            )
            row.addWidget(btn_rm)
            self._dist_list_layout.addWidget(row_w)

    def _on_add_dist_clicked(self) -> None:
        if len(self._overlay_mus) >= 7:
            return  # max 7 overlays (8 total including primary)
        mu = max(
            self._mu_add_spin.value() if self._mu_add_spin is not None else 1.0,
            0.001,
        )
        self._overlay_mus.append(mu)
        self._refresh_dist_list_ui()
        self._update_plot()

    def _on_remove_dist_clicked(self, idx: int) -> None:
        if 0 <= idx < len(self._overlay_mus):
            self._overlay_mus.pop(idx)
            self._refresh_dist_list_ui()
            self._update_plot()

    def _on_clear_dists_clicked(self) -> None:
        self._overlay_mus.clear()
        self._refresh_dist_list_ui()
        self._update_plot()

    def _read_mu(self) -> float:
        if self._mu_spin is not None:
            return max(self._mu_spin.value(), 0.001)
        return self._mu

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_tab_changed(self, index: int) -> None:
        self._tab = index
        self._update_plot()

    def _on_plot_clicked(self) -> None:
        if self._tab_widget is not None:
            self._tab_widget.setCurrentIndex(0)
        self._tab = 0
        self._update_plot()

    def _on_calc_clicked(self) -> None:
        if self._tab_widget is not None:
            self._tab_widget.setCurrentIndex(1)
        self._tab = 1
        self._update_plot()

    def _on_export_clicked(self) -> None:
        if self._export_svc is None:
            self._logger.warning(f"[{self.MODULE_ID}] export_service not available")
            return
        path = self._export_svc.ask_save_path(
            parent=self._view,
            title="Xuất đồ thị phân phối mũ",
            default_name="phan_phoi_mu.png",
            file_filter="PNG Images (*.png);;All Files (*)",
        )
        if path:
            self.export(str(path))

    # ── Plot update ───────────────────────────────────────────────────────────

    def _update_plot(self) -> None:
        """Read inputs, compute, render canvas, update result label."""
        if self._canvas is None:
            return

        mu = self._read_mu()
        self._mu = mu
        tab = self._tab_widget.currentIndex() if self._tab_widget is not None else 0
        result_text = ""

        try:
            if tab == 0:
                all_mus = [mu] + list(self._overlay_mus)
                result_text = self._canvas.render_multi_distribution(all_mus, self._precision)

            else:  # tab == 1
                x_a = self._xa_spin.value() if self._xa_spin is not None else self._x_a
                x_b = self._xb_spin.value() if self._xb_spin is not None else self._x_b

                self._x_a = max(x_a, 0.0)
                self._x_b = max(x_b, self._x_a)

                result_text = self._canvas.render_x_to_prob(
                    mu=mu,
                    x_a=self._x_a,
                    x_b=self._x_b,
                    precision=self._precision,
                )

        except Exception as exc:  # noqa: BLE001
            result_text = f"⚠ Lỗi tính toán:\n{exc}"
            self._logger.warning(f"[{self.MODULE_ID}] _update_plot error: {exc}")

        if self._result_label is not None:
            self._result_label.setText(result_text)
