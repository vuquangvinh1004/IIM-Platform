"""Normal Distribution Explorer — v2.0.0

Three simulation modes in a tab-panel layout:

  Tab 1  Phân phối N(μ, σ)         — Bell curve with 68-95-99.7 percentage bands
  Tab 2  α → Z/X  (Tìm ngưỡng)    — Given tail probabilities, find critical values
  Tab 3  Z/X → α  (Tìm xác suất)  — Given critical values, compute probability areas

All modes support arbitrary parameters μ (mean) and σ (standard deviation).
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np
from scipy.stats import norm

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QPalette
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
        QButtonGroup,
        QDoubleSpinBox,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QRadioButton,
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
_ModuleWidgetBase = QWidget if _QT else object  # type: ignore[misc]



# ---------------------------------------------------------------------------
# Canvas — renders all three simulation modes
# ---------------------------------------------------------------------------


class _NormalCurveCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Embedded matplotlib Figure for rendering normal distribution diagrams."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _MPL:
            self._figure = Figure(figsize=(10, 5.5), dpi=100)
            self._ax = self._figure.add_subplot(111)
            self._canvas = FigureCanvas(self._figure)
            self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            layout.addWidget(self._canvas)
        else:
            layout.addWidget(QLabel("⚠ matplotlib chưa được cài. Chạy: pip install matplotlib"))

    # ── Shared helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _decorate(ax) -> None:
        """Minimal axes decoration: remove 3 spines, position bottom spine at zero."""
        for sp in ("left", "right", "top"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_position("zero")
        ax.set_yticks([])

    @staticmethod
    def _f(v: float, p: int) -> str:
        return f"{v:.{p}f}"

    # ── Mode 1: Phân phối N(μ, σ) ─────────────────────────────────────────────

    def render_distribution(self, mu: float, sigma: float, precision: int = 4) -> str:
        """Draw the bell curve with 68-95-99.7 reference bands. Returns result text."""
        if not _MPL:
            return ""

        ax = self._ax
        ax.clear()

        xs = np.linspace(mu - 4.5 * sigma, mu + 4.5 * sigma, 1500)
        ys = norm.pdf(xs, mu, sigma)
        y_peak = float(norm.pdf(mu, mu, sigma))

        ax.plot(xs, ys, color="#2C3E50", lw=2.0, zorder=6)

        # Three nested shaded bands (outermost lightest)
        band_cfg = [
            (3, "#AED6F1", 0.28),
            (2, "#5DADE2", 0.30),
            (1, "#2471A3", 0.38),
        ]
        for n, clr, alpha in band_cfg:
            ax.fill_between(
                xs, ys,
                where=(xs >= mu - n * sigma) & (xs <= mu + n * sigma),
                color=clr, alpha=alpha, zorder=2 + n,
            )

        # Reference lines
        ax.axvline(mu, color="#E74C3C", linestyle="--", lw=1.4, ymax=0.92, zorder=7, alpha=0.85)
        for n in (1, 2, 3):
            for sign in (-1, 1):
                ax.axvline(
                    mu + sign * n * sigma,
                    color="#7F8C8D", linestyle=":", lw=0.9, ymax=0.85, zorder=3, alpha=0.65,
                )

        self._decorate(ax)

        # X-axis ticks at μ−2σ … μ+2σ
        ticks = [mu + k * sigma for k in range(-2, 3)]
        tick_labels = []
        for k, v in zip(range(-2, 3), ticks):
            sfx = "" if k == 0 else (f"+{k}σ" if k > 0 else f"{k}σ")
            tick_labels.append(f"μ{sfx}\n{self._f(v, 2)}")
        ax.set_xticks(ticks)
        ax.set_xticklabels(tick_labels, fontsize=8.5)

        # Double-headed arrow annotations for each band
        annot_cfg = [
            ("68,27%", 1, "#1A5276", 0.58),
            ("95,45%", 2, "#154360", 0.36),
            ("99,73%", 3, "#0A2540", 0.17),
        ]
        for pct, n, clr, yfrac in annot_cfg:
            ypos = y_peak * yfrac
            ax.annotate(
                "",
                xy=(mu + n * sigma, ypos),
                xytext=(mu - n * sigma, ypos),
                arrowprops=dict(arrowstyle="<->", color=clr, lw=1.2),
            )
            ax.text(
                mu, ypos + y_peak * 0.026, pct,
                ha="center", va="bottom", fontsize=9.5, color=clr, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.22", fc="white", ec=clr, alpha=0.88),
            )

        # μ label above peak
        ax.text(mu, y_peak * 1.04, "μ", ha="center", va="bottom",
                fontsize=11, color="#E74C3C", fontweight="bold")

        self._figure.tight_layout(pad=1.0)
        self._canvas.draw()

        p = precision
        return (
            f"μ = {self._f(mu, 2)}\n"
            f"σ = {self._f(sigma, 2)}\n"
            f"σ² = {self._f(sigma ** 2, 2)}\n\n"
            f"[μ−σ,  μ+σ]  = [{self._f(mu - sigma, 2)},  {self._f(mu + sigma, 2)}]  → 68,27%\n"
            f"[μ−2σ, μ+2σ] = [{self._f(mu - 2*sigma, 2)},  {self._f(mu + 2*sigma, 2)}]  → 95,45%\n"
            f"[μ−3σ, μ+3σ] = [{self._f(mu - 3*sigma, 2)},  {self._f(mu + 3*sigma, 2)}]  → 99,73%"
        )

    # ── Mode 1 (multi): Overlay nhiều N(μ, σ) ────────────────────────────────

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
        distributions: list[tuple[float, float]],
        precision: int = 4,
    ) -> str:
        """Draw multiple N(μ, σ) curves on the same axes.

        If ``distributions`` contains exactly one entry, delegates to
        :meth:`render_distribution` so the 68-95-99.7 bands are preserved.
        For two or more curves each distribution gets a distinct color and
        a legend entry; the density bands are omitted to avoid clutter.
        """
        if not distributions:
            return ""
        if len(distributions) == 1:
            return self.render_distribution(
                distributions[0][0], distributions[0][1], precision
            )
        if not _MPL:
            return ""

        ax = self._ax
        ax.clear()

        x_min = min(mu - 4.5 * sigma for mu, sigma in distributions)
        x_max = max(mu + 4.5 * sigma for mu, sigma in distributions)
        xs = np.linspace(x_min, x_max, 2000)

        result_lines: list[str] = []
        p = precision
        for i, (mu, sigma) in enumerate(distributions):
            color = self._OVERLAY_COLORS[i % len(self._OVERLAY_COLORS)]
            ys = norm.pdf(xs, mu, sigma)
            lbl = f"N(μ={self._f(mu, 2)}, σ={self._f(sigma, 2)})"
            ax.plot(xs, ys, color=color, lw=2.0, label=lbl, zorder=5 + i)
            ax.axvline(
                mu, color=color, linestyle="--", lw=0.9,
                ymax=0.92, zorder=4 + i, alpha=0.7,
            )
            result_lines.append(
                f"{lbl}  σ²={self._f(sigma ** 2, 2)}"
            )

        self._decorate(ax)
        ax.legend(loc="upper right", fontsize=8.5, framealpha=0.92, edgecolor="#BDC3C7")

        self._figure.tight_layout(pad=1.0)
        self._canvas.draw()

        return "\n".join(result_lines)

    # ── Mode 2: α → Z/X ───────────────────────────────────────────────────────

    def render_alpha_to_z(
        self,
        mu: float, sigma: float,
        alpha_l: float, alpha_r: float,
        z_l: float, z_r: float,
        x_l: float, x_r: float,
        precision: int = 4,
    ) -> None:
        """Draw N(μ,σ) with tails shaded at the computed critical X values."""
        if not _MPL:
            return

        ax = self._ax
        ax.clear()

        area_m = 1.0 - alpha_l - alpha_r
        x_min = min(mu - 4 * sigma, x_l - 0.4 * sigma)
        x_max = max(mu + 4 * sigma, x_r + 0.4 * sigma)
        xs = np.linspace(x_min, x_max, 1500)
        ys = norm.pdf(xs, mu, sigma)
        y_peak = float(norm.pdf(mu, mu, sigma))

        ax.plot(xs, ys, color="#2C3E50", lw=2.0, zorder=5)
        ax.fill_between(xs, ys, where=xs < x_l, color="#E74C3C", alpha=0.75, zorder=3)
        ax.fill_between(xs, ys, where=xs > x_r, color="#E74C3C", alpha=0.75, zorder=3)
        ax.fill_between(xs, ys, where=(xs >= x_l) & (xs <= x_r), color="#3498DB", alpha=0.60, zorder=3)

        self._decorate(ax)
        ax.axvline(mu, color="#7F8C8D", linestyle="--", lw=0.9, ymax=0.92, zorder=2, alpha=0.7)

        ax.set_xticks([x_l, mu, x_r])
        ax.set_xticklabels(
            [self._f(x_l, 2), self._f(mu, 2), self._f(x_r, 2)],
            fontsize=10, fontweight="bold",
        )

        d = abs(x_r - x_l) or sigma
        # Arrow tips clamped to stay within shaded tail (below the PDF curve)
        y_bnd_l = float(norm.pdf(x_l, mu, sigma))
        y_bnd_r = float(norm.pdf(x_r, mu, sigma))
        y_tip_l = min(y_peak * 0.04, y_bnd_l * 0.55)
        y_tip_r = min(y_peak * 0.04, y_bnd_r * 0.55)
        # Tail labels: placed ABOVE the axes in axes-fraction space → never overlap distribution
        ax.annotate(
            f"α = {self._f(alpha_l, precision)}",
            xy=(x_l, y_tip_l), xycoords="data",
            xytext=(0.04, 1.06), textcoords="axes fraction",
            ha="left", va="bottom", fontsize=10, color="#C0392B",
            arrowprops=dict(arrowstyle="->", color="#C0392B"),
            annotation_clip=False,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#C0392B", alpha=0.92),
        )
        ax.annotate(
            f"α = {self._f(alpha_r, precision)}",
            xy=(x_r, y_tip_r), xycoords="data",
            xytext=(0.96, 1.06), textcoords="axes fraction",
            ha="right", va="bottom", fontsize=10, color="#C0392B",
            arrowprops=dict(arrowstyle="->", color="#C0392B"),
            annotation_clip=False,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#C0392B", alpha=0.92),
        )
        # Center label as axes title — always outside the plot area
        ax.set_title(
            f"1 − α = {self._f(area_m, precision)}",
            fontsize=12, fontweight="bold", pad=10,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#2980B9", alpha=0.90),
        )

        self._figure.tight_layout(pad=1.0, rect=[0, 0, 1, 0.87])
        self._canvas.draw()

    # ── Mode 3: Z/X → α ───────────────────────────────────────────────────────

    def render_z_to_alpha(
        self,
        mu: float, sigma: float,
        x_l: float, x_r: float,
        area_l: float, area_r: float, area_m: float,
        precision: int = 4,
    ) -> None:
        """Draw N(μ,σ) with probability areas annotated from the given X boundaries."""
        if not _MPL:
            return

        ax = self._ax
        ax.clear()

        x_min = min(mu - 4 * sigma, x_l - 0.4 * sigma)
        x_max = max(mu + 4 * sigma, x_r + 0.4 * sigma)
        xs = np.linspace(x_min, x_max, 1500)
        ys = norm.pdf(xs, mu, sigma)
        y_peak = float(norm.pdf(mu, mu, sigma))

        ax.plot(xs, ys, color="#2C3E50", lw=2.0, zorder=5)
        ax.fill_between(xs, ys, where=xs < x_l, color="#E74C3C", alpha=0.75, zorder=3)
        ax.fill_between(xs, ys, where=xs > x_r, color="#E74C3C", alpha=0.75, zorder=3)
        ax.fill_between(xs, ys, where=(xs >= x_l) & (xs <= x_r), color="#3498DB", alpha=0.60, zorder=3)

        self._decorate(ax)
        ax.axvline(mu, color="#7F8C8D", linestyle="--", lw=0.9, ymax=0.92, zorder=2, alpha=0.7)

        ax.set_xticks([x_l, mu, x_r])
        ax.set_xticklabels(
            [self._f(x_l, 2), self._f(mu, 2), self._f(x_r, 2)],
            fontsize=10, fontweight="bold",
        )

        d = abs(x_r - x_l) or sigma
        # Arrow tips clamped to stay within shaded tail (below the PDF curve)
        y_bnd_l = float(norm.pdf(x_l, mu, sigma))
        y_bnd_r = float(norm.pdf(x_r, mu, sigma))
        y_tip_l = min(y_peak * 0.04, y_bnd_l * 0.55)
        y_tip_r = min(y_peak * 0.04, y_bnd_r * 0.55)
        # Tail labels: placed ABOVE the axes in axes-fraction space → never overlap distribution
        ax.annotate(
            f"Đuôi trái\n= {self._f(area_l, precision)}",
            xy=(x_l, y_tip_l), xycoords="data",
            xytext=(0.04, 1.06), textcoords="axes fraction",
            ha="left", va="bottom", fontsize=10, color="#C0392B",
            arrowprops=dict(arrowstyle="->", color="#C0392B"),
            annotation_clip=False,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#C0392B", alpha=0.92),
        )
        ax.annotate(
            f"Đuôi phải\n= {self._f(area_r, precision)}",
            xy=(x_r, y_tip_r), xycoords="data",
            xytext=(0.96, 1.06), textcoords="axes fraction",
            ha="right", va="bottom", fontsize=10, color="#C0392B",
            arrowprops=dict(arrowstyle="->", color="#C0392B"),
            annotation_clip=False,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#C0392B", alpha=0.92),
        )
        # Center label as axes title — always outside the plot area
        ax.set_title(
            f"Diện tích giữa = {self._f(area_m, precision)}",
            fontsize=11, fontweight="bold", pad=10,
            bbox=dict(boxstyle="round,pad=0.4", fc="white", ec="#2980B9", alpha=0.90),
        )

        self._figure.tight_layout(pad=1.0, rect=[0, 0, 1, 0.87])
        self._canvas.draw()

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


class NormalDistributionModule(BaseModule):
    """IIMP module — Normal Distribution Explorer v3.0.0.

    Three simulation modes:
      Tab 0  Phân phối N(μ, σ)  — Bell curve (multi-overlay) with 68-95-99.7 bands
      Tab 1  α → Z/X            — Given tail probabilities, find critical values
      Tab 2  Z/X → α            — Given critical values, find probability areas
    """

    MODULE_ID = "normal_distribution"
    MODULE_NAME = "Normal Distribution Explorer"
    MODULE_VERSION = "3.0.0"

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
        self._mu: float = 0.0
        self._sigma: float = 1.0
        self._tab: int = 0
        self._alpha_l: float = 0.025
        self._alpha_r: float = 0.025
        self._z_l: float = -1.96
        self._z_r: float = 1.96
        self._z_input_mode: str = "z"   # "z" or "x"
        self._precision: int = 4

        # Mode 1 overlay: additional N(μ,σ) distributions drawn simultaneously
        self._overlay_dists: list[tuple[float, float]] = []

        # UI refs — assigned in build_view
        self._view: QWidget | None = None
        self._canvas: _NormalCurveCanvas | None = None
        self._mu_spin: QDoubleSpinBox | None = None
        self._sigma_spin: QDoubleSpinBox | None = None
        self._tab_widget: QTabWidget | None = None
        self._alpha_l_spin: QDoubleSpinBox | None = None
        self._alpha_r_spin: QDoubleSpinBox | None = None
        self._radio_z: QRadioButton | None = None
        self._radio_x: QRadioButton | None = None
        self._val_l_spin: QDoubleSpinBox | None = None
        self._val_r_spin: QDoubleSpinBox | None = None
        self._val_l_label: QLabel | None = None
        self._val_r_label: QLabel | None = None
        self._result_label: QLabel | None = None
        # Mode 1 overlay UI refs
        self._mu_add_spin: QDoubleSpinBox | None = None
        self._sigma_add_spin: QDoubleSpinBox | None = None
        self._dist_list_frame: QWidget | None = None
        self._dist_list_layout: QVBoxLayout | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_load")
        raw = self._settings_svc.get_module_setting(self.MODULE_ID, "precision")
        if raw is not None:
            try:
                self._precision = int(raw)
            except (TypeError, ValueError):
                pass

    def build_view(self) -> QWidget:
        """Build and return the main module widget."""
        root = QWidget()
        root.setObjectName("ndModuleRoot")
        root.setProperty("moduleShell", "root")
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        control_panel = self._build_control_panel()
        control_panel.setProperty("moduleShell", "sidebar")
        control_panel.setFixedWidth(285)
        main_layout.addWidget(control_panel)

        self._canvas = _NormalCurveCanvas()
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
            "sigma": self._sigma,
            "tab": self._tab,
            "alpha_l": self._alpha_l,
            "alpha_r": self._alpha_r,
            "z_l": self._z_l,
            "z_r": self._z_r,
            "z_input_mode": self._z_input_mode,
            "precision": self._precision,
            "overlay_dists": list(self._overlay_dists),
        }

    def restore_state(self, state: dict[str, Any]) -> None:
        self._mu = float(state.get("mu", 0.0))
        self._sigma = max(float(state.get("sigma", 1.0)), 0.001)
        self._tab = int(state.get("tab", 0))
        self._alpha_l = float(state.get("alpha_l", 0.025))
        self._alpha_r = float(state.get("alpha_r", 0.025))
        self._z_l = float(state.get("z_l", -1.96))
        self._z_r = float(state.get("z_r", 1.96))
        self._z_input_mode = str(state.get("z_input_mode", "z"))
        self._precision = int(state.get("precision", 4))
        raw_overlays = state.get("overlay_dists", [])
        self._overlay_dists = [
            (float(m), max(float(s), 0.001))
            for m, s in raw_overlays
        ][:7]
        self._logger.debug(f"[{self.MODULE_ID}] state restored")

        # Sync UI if already built
        if self._mu_spin is not None:
            self._mu_spin.setValue(self._mu)
        if self._sigma_spin is not None:
            self._sigma_spin.setValue(self._sigma)
        if self._tab_widget is not None:
            self._tab_widget.setCurrentIndex(self._tab)
        if self._alpha_l_spin is not None:
            self._alpha_l_spin.setValue(self._alpha_l)
        if self._alpha_r_spin is not None:
            self._alpha_r_spin.setValue(self._alpha_r)
        if self._radio_z is not None:
            self._radio_z.setChecked(self._z_input_mode == "z")
        if self._radio_x is not None:
            self._radio_x.setChecked(self._z_input_mode == "x")
        if self._val_l_spin is not None:
            # Restore the raw stored value; the stored values are always in
            # the selected mode (Z or X) at the time get_state() was called.
            self._val_l_spin.blockSignals(True)
            self._val_l_spin.setValue(self._z_l)
            self._val_l_spin.blockSignals(False)
        if self._val_r_spin is not None:
            self._val_r_spin.blockSignals(True)
            self._val_r_spin.setValue(self._z_r)
            self._val_r_spin.blockSignals(False)
        self._update_val_labels()
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
    def _compute_alpha_to_z(
        mu: float, sigma: float, alpha_l: float, alpha_r: float
    ) -> tuple[float, float, float, float, float]:
        """Return (z_l, z_r, x_l, x_r, area_m).

        Given left and right tail areas alpha_l, alpha_r, compute the
        corresponding standard Z critical values and actual X critical values
        for N(mu, sigma).
        """
        z_l = float(norm.ppf(alpha_l))
        z_r = float(norm.ppf(1.0 - alpha_r))
        x_l = mu + sigma * z_l
        x_r = mu + sigma * z_r
        area_m = 1.0 - alpha_l - alpha_r
        return z_l, z_r, x_l, x_r, area_m

    @staticmethod
    def _compute_z_to_alpha(
        mu: float, sigma: float,
        val_l: float, val_r: float,
        input_mode: str = "z",
    ) -> tuple[float, float, float, float, float, float, float]:
        """Return (z_l, z_r, x_l, x_r, area_l, area_r, area_m).

        Given critical values (Z or X) for the left and right boundary,
        compute the three probability areas for N(mu, sigma).
        If input_mode='z', val_l/val_r are standard Z values.
        If input_mode='x', val_l/val_r are actual X values in the distribution.
        Values are swapped internally if val_l > val_r.
        """
        if input_mode == "z":
            z_l, z_r = val_l, val_r
            x_l = mu + sigma * z_l
            x_r = mu + sigma * z_r
        else:  # "x"
            x_l, x_r = val_l, val_r
            z_l = (x_l - mu) / sigma
            z_r = (x_r - mu) / sigma
        if z_l > z_r:
            z_l, z_r = z_r, z_l
            x_l, x_r = x_r, x_l
        area_l = float(norm.cdf(z_l))
        area_r = float(1.0 - norm.cdf(z_r))
        area_m = 1.0 - area_l - area_r
        return z_l, z_r, x_l, x_r, area_l, area_r, area_m

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_control_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        # ── Shared distribution parameters ──────────────────────────────────
        params_group = QGroupBox("Tham số phân phối")
        params_layout = QVBoxLayout(params_group)
        params_layout.setSpacing(6)

        row_mu = QHBoxLayout()
        row_mu.addWidget(QLabel("μ (trung bình):"))
        mu_spin = QDoubleSpinBox()
        mu_spin.setRange(-1000.0, 1000.0)
        mu_spin.setDecimals(4)
        mu_spin.setSingleStep(0.5)
        mu_spin.setValue(self._mu)
        row_mu.addWidget(mu_spin)
        self._mu_spin = mu_spin
        params_layout.addLayout(row_mu)

        row_sigma = QHBoxLayout()
        row_sigma.addWidget(QLabel("σ (độ lệch chuẩn):"))
        sigma_spin = QDoubleSpinBox()
        sigma_spin.setRange(0.001, 1000.0)
        sigma_spin.setDecimals(4)
        sigma_spin.setSingleStep(0.1)
        sigma_spin.setValue(self._sigma)
        row_sigma.addWidget(sigma_spin)
        self._sigma_spin = sigma_spin
        params_layout.addLayout(row_sigma)

        layout.addWidget(params_group)

        # ── Tab widget: 3 simulation modes ──────────────────────────────────
        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.addTab(self._build_tab_distribution(), "Phân phối")
        tabs.addTab(self._build_tab_alpha_to_z(), "α → Z/X")
        tabs.addTab(self._build_tab_z_to_alpha(), "Z/X → α")
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
        result_label.setMinimumHeight(110)
        result_layout.addWidget(result_label)
        layout.addWidget(result_group)
        self._result_label = result_label

        # ── Action buttons ───────────────────────────────────────────────────
        btn_plot = QPushButton("▶  Vẽ đồ thị")
        btn_plot.setObjectName("btnPrimary")
        btn_plot.clicked.connect(self._on_plot_clicked)
        btn_plot.setToolTip("Vẽ phân phối N(μ, σ) với dải 68-95-99,7%")
        layout.addWidget(btn_plot)

        btn_find_z = QPushButton("🔍  Tìm Z/X  (cho α)")
        btn_find_z.setObjectName("btnPrimary")
        btn_find_z.clicked.connect(self._on_find_z_clicked)
        btn_find_z.setToolTip("Nhập α đuôi trái/phải → tính giá trị tới hạn Z và X")
        layout.addWidget(btn_find_z)

        btn_find_alpha = QPushButton("🔍  Tìm α  (cho Z/X)")
        btn_find_alpha.setObjectName("btnPrimary")
        btn_find_alpha.clicked.connect(self._on_find_alpha_clicked)
        btn_find_alpha.setToolTip("Nhập Z hoặc X tới hạn → tính diện tích đuôi trái, phải và vùng giữa")
        layout.addWidget(btn_find_alpha)

        btn_export = QPushButton("💾  Xuất PNG")
        btn_export.setObjectName("btnSecondary")
        btn_export.clicked.connect(self._on_export_clicked)
        layout.addWidget(btn_export)

        layout.addStretch()
        return panel

    def _build_tab_distribution(self) -> QWidget:
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
        mu_add.setRange(-1000.0, 1000.0)
        mu_add.setDecimals(4)
        mu_add.setSingleStep(0.5)
        mu_add.setValue(1.0)
        row_mu.addWidget(mu_add)
        self._mu_add_spin = mu_add
        add_layout.addLayout(row_mu)

        row_sigma = QHBoxLayout()
        row_sigma.addWidget(QLabel("σ:"))
        sigma_add = QDoubleSpinBox()
        sigma_add.setRange(0.001, 1000.0)
        sigma_add.setDecimals(4)
        sigma_add.setSingleStep(0.1)
        sigma_add.setValue(1.0)
        row_sigma.addWidget(sigma_add)
        self._sigma_add_spin = sigma_add
        add_layout.addLayout(row_sigma)

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
        scroll.setMaximumHeight(100)
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
            "ℹ Phân phối chính dùng μ, σ ở trên.\n"
            "  Băng 68-95-99,7% chỉ hiển thị\n"
            "  khi không có overlay."
        )
        hint.setWordWrap(True)
        hint.setProperty("moduleShell", "hint")
        layout.addWidget(hint)
        layout.addStretch()

        self._refresh_dist_list_ui()
        return tab

    def _build_tab_alpha_to_z(self) -> QWidget:
        """Tab 1: Given tail areas (α), find critical Z and X values."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        layout.addWidget(QLabel("α đuôi trái:"))
        alpha_l = QDoubleSpinBox()
        alpha_l.setRange(0.00001, 0.49999)
        alpha_l.setDecimals(5)
        alpha_l.setSingleStep(0.005)
        alpha_l.setValue(self._alpha_l)
        layout.addWidget(alpha_l)
        self._alpha_l_spin = alpha_l

        layout.addWidget(QLabel("α đuôi phải:"))
        alpha_r = QDoubleSpinBox()
        alpha_r.setRange(0.00001, 0.49999)
        alpha_r.setDecimals(5)
        alpha_r.setSingleStep(0.005)
        alpha_r.setValue(self._alpha_r)
        layout.addWidget(alpha_r)
        self._alpha_r_spin = alpha_r

        hint = QLabel("→ Tính z tới hạn và X tới hạn\n   tương ứng với N(μ, σ).")
        hint.setWordWrap(True)
        hint.setProperty("moduleShell", "hint")
        layout.addWidget(hint)
        layout.addStretch()
        return tab

    def _build_tab_z_to_alpha(self) -> QWidget:
        """Tab 2: Given critical values (Z or X), compute probability areas."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(8, 10, 8, 8)
        layout.setSpacing(6)

        # Radio buttons: Z input or X input
        radio_row = QHBoxLayout()
        radio_z = QRadioButton("Nhập Z")
        radio_x = QRadioButton("Nhập X")
        radio_z.setChecked(self._z_input_mode == "z")
        radio_x.setChecked(self._z_input_mode == "x")
        radio_group = QButtonGroup(tab)
        radio_group.addButton(radio_z, 0)
        radio_group.addButton(radio_x, 1)
        radio_row.addWidget(radio_z)
        radio_row.addWidget(radio_x)
        layout.addLayout(radio_row)
        self._radio_z = radio_z
        self._radio_x = radio_x
        radio_group.idToggled.connect(self._on_input_mode_changed)

        lbl_l = QLabel("Giá trị Z trái:" if self._z_input_mode == "z" else "Giá trị X trái:")
        layout.addWidget(lbl_l)
        self._val_l_label = lbl_l

        val_l = QDoubleSpinBox()
        val_l.setDecimals(4)
        val_l.setRange(-1e6, 1e6)   # wide range — no clamping for any Z or X value
        val_l.setSingleStep(0.1)
        val_l.setValue(self._z_l)
        layout.addWidget(val_l)
        self._val_l_spin = val_l

        lbl_r = QLabel("Giá trị Z phải:" if self._z_input_mode == "z" else "Giá trị X phải:")
        layout.addWidget(lbl_r)
        self._val_r_label = lbl_r

        val_r = QDoubleSpinBox()
        val_r.setDecimals(4)
        val_r.setRange(-1e6, 1e6)   # wide range — no clamping for any Z or X value
        val_r.setSingleStep(0.1)
        val_r.setValue(self._z_r)
        layout.addWidget(val_r)
        self._val_r_spin = val_r

        hint = QLabel("→ Tính diện tích đuôi trái, phải\n   và vùng giữa hai ngưỡng.")
        hint.setWordWrap(True)
        hint.setProperty("moduleShell", "hint")
        layout.addWidget(hint)
        layout.addStretch()
        return tab

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _update_val_labels(self) -> None:
        mode = self._z_input_mode
        if self._val_l_label:
            self._val_l_label.setText(
                "Giá trị Z trái:" if mode == "z" else "Giá trị X trái:"
            )
        if self._val_r_label:
            self._val_r_label.setText(
                "Giá trị Z phải:" if mode == "z" else "Giá trị X phải:"
            )

    def _read_mu_sigma(self) -> tuple[float, float]:
        mu = self._mu_spin.value() if self._mu_spin else self._mu
        sigma = self._sigma_spin.value() if self._sigma_spin else self._sigma
        return mu, max(sigma, 0.001)

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _on_tab_changed(self, index: int) -> None:
        self._tab = index
        self._update_plot()

    def _on_input_mode_changed(self, btn_id: int, checked: bool) -> None:
        """When toggling Z/X radio, convert current spinbox values to the new mode."""
        if not checked:
            return
        new_mode = "z" if btn_id == 0 else "x"
        if new_mode == self._z_input_mode:
            return

        mu, sigma = self._read_mu_sigma()
        if self._val_l_spin and self._val_r_spin:
            v_l = self._val_l_spin.value()
            v_r = self._val_r_spin.value()
            if new_mode == "x":
                # Z → X: convert current Z scores to actual X values
                new_l = mu + sigma * v_l
                new_r = mu + sigma * v_r
            else:
                # X → Z: convert current X values back to Z scores
                new_l = (v_l - mu) / sigma if sigma > 0 else v_l
                new_r = (v_r - mu) / sigma if sigma > 0 else v_r
            self._val_l_spin.setValue(new_l)
            self._val_r_spin.setValue(new_r)

        self._z_input_mode = new_mode
        self._update_val_labels()

    def _on_plot_clicked(self) -> None:
        if self._tab_widget:
            self._tab_widget.setCurrentIndex(0)
        self._tab = 0
        self._update_plot()

    def _on_find_z_clicked(self) -> None:
        """Switch to Tab 1 (α → Z/X) and compute immediately."""
        if self._tab_widget:
            self._tab_widget.setCurrentIndex(1)
        self._tab = 1
        self._update_plot()

    def _on_find_alpha_clicked(self) -> None:
        """Switch to Tab 2 (Z/X → α) and compute immediately."""
        if self._tab_widget:
            self._tab_widget.setCurrentIndex(2)
        self._tab = 2
        self._update_plot()

    def _on_export_clicked(self) -> None:
        if self._export_svc is None:
            self._logger.warning(f"[{self.MODULE_ID}] export_service not available")
            return
        path = self._export_svc.ask_save_path(
            parent=self._view,
            title="Xuất đồ thị phân phối chuẩn",
            default_name="phan_phoi_chuan.png",
            file_filter="PNG Images (*.png);;All Files (*)",
        )
        if path:
            self.export(str(path))

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

        if not self._overlay_dists:
            empty = QLabel("(chưa có overlay)")
            empty.setObjectName("mutedText")
            self._dist_list_layout.addWidget(empty)
            return

        colors = _NormalCurveCanvas._OVERLAY_COLORS
        p = self._precision
        for i, (mu, sigma) in enumerate(self._overlay_dists):
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

            lbl = QLabel(f"N({mu:.2f},  {sigma:.2f})")
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
        if len(self._overlay_dists) >= 7:
            return  # max 7 overlays (8 total including primary)
        mu = self._mu_add_spin.value() if self._mu_add_spin else 0.0
        sigma = max(
            self._sigma_add_spin.value() if self._sigma_add_spin else 1.0,
            0.001,
        )
        self._overlay_dists.append((mu, sigma))
        self._refresh_dist_list_ui()
        self._update_plot()

    def _on_remove_dist_clicked(self, idx: int) -> None:
        if 0 <= idx < len(self._overlay_dists):
            self._overlay_dists.pop(idx)
            self._refresh_dist_list_ui()
            self._update_plot()

    def _on_clear_dists_clicked(self) -> None:
        self._overlay_dists.clear()
        self._refresh_dist_list_ui()
        self._update_plot()

    # ── Plot update ───────────────────────────────────────────────────────────

    def _update_plot(self) -> None:  # noqa: C901
        """Read current inputs, compute, render canvas, update result label."""
        if self._canvas is None:
            return

        mu, sigma = self._read_mu_sigma()
        self._mu = mu
        self._sigma = sigma
        tab = self._tab_widget.currentIndex() if self._tab_widget else 0
        result_text = ""

        try:
            if tab == 0:
                # ── Mode 1: Distribution overview (with optional overlay) ────
                all_dists = [(mu, sigma)] + list(self._overlay_dists)
                result_text = self._canvas.render_multi_distribution(
                    all_dists, self._precision
                )

            elif tab == 1:
                # ── Mode 2: α → Z/X  ─────────────────────────────────────────
                alpha_l = (
                    self._alpha_l_spin.value() if self._alpha_l_spin else self._alpha_l
                )
                alpha_r = (
                    self._alpha_r_spin.value() if self._alpha_r_spin else self._alpha_r
                )
                self._alpha_l, self._alpha_r = alpha_l, alpha_r

                z_l, z_r, x_l, x_r, area_m = self._compute_alpha_to_z(
                    mu, sigma, alpha_l, alpha_r
                )
                self._canvas.render_alpha_to_z(
                    mu, sigma, alpha_l, alpha_r, z_l, z_r, x_l, x_r, self._precision
                )

                is_std = abs(mu) < 1e-9 and abs(sigma - 1.0) < 1e-9
                result_text = f"z trái  = {z_l:.2f}\nz phải  = {z_r:.2f}\n"
                if not is_std:
                    result_text += f"X trái  = {x_l:.2f}\nX phải  = {x_r:.2f}\n"
                result_text += (
                    f"α trái  = {alpha_l:.4f}\n"
                    f"α phải  = {alpha_r:.4f}\n"
                    f"1 − α   = {area_m:.4f}"
                )

            else:
                # ── Mode 3: Z/X → α  ─────────────────────────────────────────
                val_l = self._val_l_spin.value() if self._val_l_spin else self._z_l
                val_r = self._val_r_spin.value() if self._val_r_spin else self._z_r
                mode = self._z_input_mode
                self._z_l, self._z_r = val_l, val_r

                z_l, z_r, x_l, x_r, area_l, area_r, area_m = self._compute_z_to_alpha(
                    mu, sigma, val_l, val_r, mode
                )
                self._canvas.render_z_to_alpha(
                    mu, sigma, x_l, x_r, area_l, area_r, area_m, self._precision
                )

                is_std = abs(mu) < 1e-9 and abs(sigma - 1.0) < 1e-9
                result_text = f"z trái  = {z_l:.2f}\nz phải  = {z_r:.2f}\n"
                if not is_std:
                    result_text += f"X trái  = {x_l:.2f}\nX phải  = {x_r:.2f}\n"
                result_text += (
                    f"Đuôi trái  = {area_l:.4f}\n"
                    f"Đuôi phải  = {area_r:.4f}\n"
                    f"Diện tích giữa = {area_m:.4f}"
                )

        except Exception as exc:  # noqa: BLE001
            self._logger.warning(f"[{self.MODULE_ID}] _update_plot error: {exc}")
            result_text = f"⚠ Lỗi: {exc}"

        if self._result_label:
            self._result_label.setText(result_text)
