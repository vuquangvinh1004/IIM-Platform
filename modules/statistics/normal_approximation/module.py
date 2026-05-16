"""Normal Approximation Explorer — v1.0.0

Two side-by-side panels demonstrating the Central Limit Theorem in action:

  Panel 1  Phân phối Nhị thức B(n, p)  →  xấp xỉ N(np, npq)
  Panel 2  Phân phối Poisson P(μ)      →  xấp xỉ N(μ, μ)

Each panel shows a discrete probability mass function as a bar chart overlaid
with the continuous normal approximation curve. Users adjust parameters with
spin-box controls and observe real-time shape changes together with an
approximation-condition indicator (np ≥ 5 and nq ≥ 5 for Binomial; μ ≥ 10
for Poisson).

Computation notes
-----------------
* Binomial PMF  P(X=k) is evaluated in log-space to stay numerically stable
  for large n (up to n=300).
* Poisson PMF   P(X=k) is evaluated via the log-gamma approach for the same
  reason (large μ).
* The normal PDF overlaid on discrete bars uses the same Y-scale as the PMFs
  because P(X=k) ≈ f(k)·1  (bin width = 1) — no re-scaling needed.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any

import numpy as np

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
        QDoubleSpinBox,
        QFrame,
        QHBoxLayout,
        QLabel,
        QSizePolicy,
        QSpinBox,
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

if TYPE_CHECKING:
    from core.module_runtime.module_context import ModuleContext

# Fallback bases when Qt is unavailable (headless unit tests)
_CanvasBase = QWidget if _QT else object  # type: ignore[misc]
_ModuleWidgetBase = QWidget if _QT else object  # type: ignore[misc]


# ── Pure computation helpers ──────────────────────────────────────────────────

def _binom_pmf(k: int, n: int, p: float) -> float:
    """Binomial PMF P(X=k) evaluated in log-space for numerical stability."""
    if k < 0 or k > n:
        return 0.0
    if p <= 0.0:
        return 1.0 if k == 0 else 0.0
    if p >= 1.0:
        return 1.0 if k == n else 0.0
    try:
        log_prob = (
            math.lgamma(n + 1)
            - math.lgamma(k + 1)
            - math.lgamma(n - k + 1)
            + k * math.log(p)
            + (n - k) * math.log(1.0 - p)
        )
        return math.exp(log_prob)
    except (ValueError, OverflowError):
        return 0.0


def _poisson_pmf(k: int, lam: float) -> float:
    """Poisson PMF P(X=k) evaluated via log-gamma for numerical stability."""
    if k < 0 or lam <= 0.0:
        return 0.0
    try:
        return math.exp(-lam + k * math.log(lam) - math.lgamma(k + 1))
    except (ValueError, OverflowError):
        return 0.0


def _normal_pdf(x: np.ndarray, mu: float, sigma: float) -> np.ndarray:
    """Standard normal PDF evaluated at each element of *x*."""
    return (1.0 / (sigma * math.sqrt(2.0 * math.pi))) * np.exp(
        -0.5 * ((x - mu) / sigma) ** 2
    )


# ── Canvas widgets ────────────────────────────────────────────────────────────

class _ApproxCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Embedded matplotlib canvas shared by both approximation panels.

    Subclasses set BAR_COLOR and CURVE_COLOR and call ``_draw()`` with the
    precomputed discrete probabilities and distribution parameters.
    """

    BAR_COLOR: str = "#5DADE2"
    CURVE_COLOR: str = "#154360"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._figure = Figure(figsize=(5.5, 4.2), dpi=100)
            self._ax = self._figure.add_subplot(111)
            self._canvas_widget = FigureCanvas(self._figure)
            self._canvas_widget.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas_widget)
        else:
            layout.addWidget(
                QLabel("⚠ matplotlib chưa được cài.\nChạy: pip install matplotlib")
            )

    def _draw(
        self,
        ks: list[int],
        probs: list[float],
        mu: float,
        sigma: float,
        curve_label: str,
    ) -> None:
        """Render bar chart + normal curve. Called by subclass ``refresh()``."""
        if not (_QT and _MPL):
            return
        ax = self._ax
        ax.clear()

        # ── Bars (discrete PMF) ──
        ax.bar(
            ks,
            probs,
            color=self.BAR_COLOR,
            alpha=0.60,
            width=0.72,
            label="Phân phối rời rạc",
            zorder=2,
        )

        # ── Normal approximation curve ──
        x_lo = max(float(min(ks)) - 1.5, mu - 4.5 * sigma)
        x_hi = float(max(ks)) + 1.5
        x = np.linspace(x_lo, x_hi, 500)
        y = _normal_pdf(x, mu, sigma)
        ax.plot(
            x,
            y,
            color=self.CURVE_COLOR,
            linewidth=1.5,
            label=curve_label,
            zorder=3,
        )

        # ── Axes style ──
        for sp in ("left", "right", "top"):
            ax.spines[sp].set_visible(False)
        ax.spines["bottom"].set_color("#BDC3C7")
        ax.tick_params(axis="both", labelsize=8, colors="#555")
        ax.set_xlabel("k", fontsize=9, color="#555")
        ax.set_ylabel("P(X = k)", fontsize=9, color="#555")
        ax.legend(fontsize=8, framealpha=0.75, loc="upper right")
        self._figure.tight_layout()
        self._canvas_widget.draw()


class _BinomCanvas(_ApproxCanvas):
    """Canvas specialised for the Binomial approximation panel."""

    BAR_COLOR = "#1A6FA3"    # deep steel blue
    CURVE_COLOR = "#C0392B"  # red

    def refresh(self, n: int, p: float) -> None:
        if not (_QT and _MPL):
            return
        mu = n * p
        sigma = math.sqrt(n * p * (1.0 - p))
        if sigma < 1e-9:
            return
        k_lo = max(0, int(math.floor(mu - 4.5 * sigma)))
        k_hi = min(n, int(math.ceil(mu + 4.5 * sigma)))
        ks = list(range(k_lo, k_hi + 1))
        probs = [_binom_pmf(k, n, p) for k in ks]
        self._draw(ks, probs, mu, sigma, f"N({mu:.2f}, {sigma:.2f}²)")


class _PoissonCanvas(_ApproxCanvas):
    """Canvas specialised for the Poisson approximation panel."""

    BAR_COLOR = "#1A7A40"    # deep forest green
    CURVE_COLOR = "#C0392B"  # red

    def refresh(self, lam: float) -> None:
        if not (_QT and _MPL):
            return
        mu = lam
        sigma = math.sqrt(lam)
        if sigma < 1e-9:
            return
        k_lo = max(0, int(math.floor(mu - 4.5 * sigma)))
        k_hi = int(math.ceil(mu + 4.5 * sigma))
        ks = list(range(k_lo, k_hi + 1))
        probs = [_poisson_pmf(k, lam) for k in ks]
        self._draw(ks, probs, mu, sigma, f"N({mu:.1f}, {sigma:.3f}²)")


# ── UI helpers ────────────────────────────────────────────────────────────────

def _card_frame(parent: QWidget | None = None) -> QFrame:
    f = QFrame(parent)
    f.setStyleSheet(
        "QFrame { background: #FDFEFE; border-radius: 8px;"
        " border: 1px solid #ECF0F1; }"
    )
    return f


def _section_title(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(
        "font-size: 13px; font-weight: bold; color: #2C3E50; border: none;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return lbl


def _param_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet("font-size: 12px; color: #34495E; border: none;")
    return lbl


def _info_label() -> QLabel:
    lbl = QLabel()
    lbl.setStyleSheet("font-size: 11px; color: #555; border: none;")
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    lbl.setWordWrap(True)
    return lbl


# ── Main view ─────────────────────────────────────────────────────────────────

class _NormalApproxView(_ModuleWidgetBase):  # type: ignore[valid-type]
    """Root widget for the Normal Approximation module.

    Contains two independent panels (Binomial and Poisson), each with:
    - a matplotlib canvas showing bars + normal curve
    - parameter spin-boxes
    - a condition-check status label
    """

    # Default parameter values
    _DEFAULT_N: int = 20
    _DEFAULT_P: float = 0.50
    _DEFAULT_LAM: float = 10.0

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        self._binom_n: int = self._DEFAULT_N
        self._binom_p: float = self._DEFAULT_P
        self._poisson_lam: float = self._DEFAULT_LAM
        self._build_ui()
        self._refresh_binom()
        self._refresh_poisson()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 12, 16, 12)
        root.setSpacing(12)

        # Page title
        page_title = QLabel("Xấp xỉ Chuẩn của Phân phối Rời rạc")
        page_title.setStyleSheet(
            "font-size: 16px; font-weight: bold; color: #1A5276;"
            " border: none;"
        )
        page_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(page_title)

        # Two panels side by side
        panels = QHBoxLayout()
        panels.setSpacing(16)
        panels.addWidget(self._build_binom_panel(), stretch=1)
        panels.addWidget(self._build_poisson_panel(), stretch=1)
        root.addLayout(panels)

    def _build_binom_panel(self) -> QWidget:
        card = _card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)

        layout.addWidget(_section_title("Phân phối Nhị thức  B(n, p)"))

        self._binom_canvas = _BinomCanvas()
        layout.addWidget(self._binom_canvas, stretch=1)

        # Controls
        ctrl = QFrame()
        ctrl.setStyleSheet("QFrame { border: none; background: transparent; }")
        ctrl_row = QHBoxLayout(ctrl)
        ctrl_row.setContentsMargins(4, 2, 4, 2)
        ctrl_row.setSpacing(10)

        self._spin_n = QSpinBox()
        self._spin_n.setRange(5, 300)
        self._spin_n.setValue(self._binom_n)
        self._spin_n.setFixedWidth(60)
        self._spin_n.setStyleSheet("font-size: 12px;")
        self._spin_n.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_n.valueChanged.connect(self._on_binom_changed)

        self._spin_p = QDoubleSpinBox()
        self._spin_p.setRange(0.01, 0.99)
        self._spin_p.setSingleStep(0.01)
        self._spin_p.setDecimals(2)
        self._spin_p.setValue(self._binom_p)
        self._spin_p.setFixedWidth(60)
        self._spin_p.setStyleSheet("font-size: 12px;")
        self._spin_p.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_p.valueChanged.connect(self._on_binom_changed)

        ctrl_row.addStretch()
        ctrl_row.addWidget(_param_label("n ="))
        ctrl_row.addWidget(self._spin_n)
        ctrl_row.addSpacing(16)
        ctrl_row.addWidget(_param_label("p ="))
        ctrl_row.addWidget(self._spin_p)
        ctrl_row.addStretch()
        layout.addWidget(ctrl)

        self._binom_info = _info_label()
        layout.addWidget(self._binom_info)
        return card

    def _build_poisson_panel(self) -> QWidget:
        card = _card_frame()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 12, 12, 10)
        layout.setSpacing(8)

        layout.addWidget(_section_title("Phân phối Poisson  P(μ)"))

        self._poisson_canvas = _PoissonCanvas()
        layout.addWidget(self._poisson_canvas, stretch=1)

        # Controls
        ctrl = QFrame()
        ctrl.setStyleSheet("QFrame { border: none; background: transparent; }")
        ctrl_row = QHBoxLayout(ctrl)
        ctrl_row.setContentsMargins(4, 2, 4, 2)
        ctrl_row.setSpacing(10)

        self._spin_lam = QDoubleSpinBox()
        self._spin_lam.setRange(1.0, 100.0)
        self._spin_lam.setSingleStep(0.5)
        self._spin_lam.setDecimals(1)
        self._spin_lam.setValue(self._poisson_lam)
        self._spin_lam.setFixedWidth(64)
        self._spin_lam.setStyleSheet("font-size: 12px;")
        self._spin_lam.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._spin_lam.valueChanged.connect(self._on_poisson_changed)

        ctrl_row.addStretch()
        ctrl_row.addWidget(_param_label("μ ="))
        ctrl_row.addWidget(self._spin_lam)
        ctrl_row.addStretch()
        layout.addWidget(ctrl)

        self._poisson_info = _info_label()
        layout.addWidget(self._poisson_info)
        return card

    # ── Event handlers ────────────────────────────────────────────────────────

    def _on_binom_changed(self) -> None:
        self._binom_n = self._spin_n.value()
        self._binom_p = self._spin_p.value()
        self._refresh_binom()

    def _on_poisson_changed(self) -> None:
        self._poisson_lam = self._spin_lam.value()
        self._refresh_poisson()

    # ── Refresh logic ─────────────────────────────────────────────────────────

    def _refresh_binom(self) -> None:
        n, p = self._binom_n, self._binom_p
        q = 1.0 - p
        mu = n * p
        sigma = math.sqrt(n * p * q)
        self._binom_canvas.refresh(n, p)
        # Approximation condition: np ≥ 5 AND nq ≥ 5
        ok = (n * p >= 5.0) and (n * q >= 5.0)
        color = "#1D8348" if ok else "#C0392B"
        cond = "✓ Điều kiện xấp xỉ thoả (np ≥ 5 và nq ≥ 5)" if ok else (
            "✗ Điều kiện xấp xỉ chưa thoả — cần np ≥ 5 và nq ≥ 5"
        )
        self._binom_info.setText(
            f"μ = np = {mu:.3f}   σ = √(npq) = {sigma:.3f}   "
            f"[np={n*p:.1f}, nq={n*q:.1f}]\n{cond}"
        )
        self._binom_info.setStyleSheet(
            f"font-size: 11px; color: {color}; border: none;"
        )

    def _refresh_poisson(self) -> None:
        lam = self._poisson_lam
        sigma = math.sqrt(lam)
        self._poisson_canvas.refresh(lam)
        # Approximation condition: μ ≥ 10
        ok = lam >= 10.0
        color = "#1D8348" if ok else "#C0392B"
        cond = "✓ Điều kiện xấp xỉ thoả (μ ≥ 10)" if ok else (
            "✗ Điều kiện xấp xỉ chưa thoả — cần μ ≥ 10"
        )
        self._poisson_info.setText(
            f"μ = {lam:.1f}   σ = √μ = {sigma:.3f}\n{cond}"
        )
        self._poisson_info.setStyleSheet(
            f"font-size: 11px; color: {color}; border: none;"
        )

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict:
        return {
            "binom_n": self._binom_n,
            "binom_p": self._binom_p,
            "poisson_lambda": self._poisson_lam,
        }

    def restore_state(self, state: dict) -> None:
        n = max(5, min(300, int(state.get("binom_n", self._DEFAULT_N))))
        p = max(0.01, min(0.99, float(state.get("binom_p", self._DEFAULT_P))))
        lam = max(1.0, min(100.0, float(state.get("poisson_lambda", self._DEFAULT_LAM))))

        self._binom_n = n
        self._binom_p = p
        self._poisson_lam = lam

        # Update spin-boxes without triggering valueChanged → _refresh (we call manually)
        self._spin_n.blockSignals(True)
        self._spin_p.blockSignals(True)
        self._spin_lam.blockSignals(True)
        self._spin_n.setValue(n)
        self._spin_p.setValue(p)
        self._spin_lam.setValue(lam)
        self._spin_n.blockSignals(False)
        self._spin_p.blockSignals(False)
        self._spin_lam.blockSignals(False)

        self._refresh_binom()
        self._refresh_poisson()


# ── Module class ──────────────────────────────────────────────────────────────

class NormalApproximationModule(BaseModule):
    """IIMP module: Normal Approximation of Binomial and Poisson distributions."""

    def __init__(self, manifest: dict, context: Any) -> None:
        super().__init__(manifest, context)
        self._view: _NormalApproxView | None = None

    @property
    def module_id(self) -> str:
        return self.manifest.get("id", "normal_approximation")

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self.context.logger.info("NormalApproximationModule loaded.")

    def build_view(self) -> QWidget:  # type: ignore[override]
        if self._view is None:
            self._view = _NormalApproxView()
        return self._view  # type: ignore[return-value]

    def on_activate(self) -> None:
        self.context.logger.debug("NormalApproximationModule activated.")

    def on_deactivate(self) -> None:
        self.context.logger.debug("NormalApproximationModule deactivated.")

    def on_unload(self) -> None:
        self._view = None
        self.context.logger.info("NormalApproximationModule unloaded.")

    # ── State ─────────────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        state: dict = {"_state_version": "1.0.0"}
        if self._view is not None:
            state.update(self._view.get_state())
        return state

    def restore_state(self, state: dict) -> None:
        if self._view is not None:
            self._view.restore_state(state)
