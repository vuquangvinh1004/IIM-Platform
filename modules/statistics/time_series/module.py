"""Time Series Simulation — v1.0.0

Four tabs demonstrating time series components for teaching:

  Tab 1  Xu hướng  (Trend     T_t)  — Long-term direction
  Tab 2  Mùa vụ   (Seasonal  S_t)  — Fixed-period recurring oscillations
  Tab 3  Chu kỳ   (Cyclical  C_t)  — Long-wave irregular fluctuations
  Tab 4  Tổng hợp (Y_t)            — Combined: additive or multiplicative model

Math:
  T_t = a × t^k          (increasing)  or  a × (N+1−t)^k  (decreasing)
  S_t = A × sin(2πt/P)   P ∈ {1, 3, 12} months
  C_t = A × sin(2πt/Pc)  Pc ∈ [24, 120] months
  I_t = σ × ε_t + shocks,  ε ~ N(0,1) fixed seed
  Y_t = T + S + C + I    (additive)
  Y_t = T × (1+S/Ts) × (1+C/Ts) + I  (multiplicative, Ts = mean|T|)
"""
from __future__ import annotations

import random
from typing import Any

import numpy as np

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QAbstractSpinBox,
        QButtonGroup,
        QCheckBox,
        QComboBox,
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

_CanvasBase = QWidget if _QT else object  # type: ignore[misc]
_WidgetBase = QWidget if _QT else object  # type: ignore[misc]

# Period display options for seasonal picker
# P=1 removed: sin(2πt/1) = 0 for all integer t, meaningless for monthly data
_PERIOD_OPTS = [("Hai tháng (P = 2)", 2), ("Quý  (P = 3)", 3), ("Nửa năm (P = 6)", 6), ("Năm  (P = 12)", 12)]

# Hex colours shared across tabs
_C_TREND = "#2471A3"      # blue
_C_SEASON = "#27AE60"     # green
_C_CYCLE = "#8E44AD"      # purple
_C_NOISE = "#E74C3C"      # red / shock
_C_COMBINED = "#2C3E50"   # charcoal

_BASE_NOISE_120 = np.random.default_rng(42).standard_normal(120)
_BASE_NOISE_POOL = np.random.default_rng(42).standard_normal(500)


# ─────────────────────────────────────────────────────────────────────────────
# Tiny UI factory helpers
# ─────────────────────────────────────────────────────────────────────────────

def _dspin(lo: float, hi: float, step: float, default: float, dec: int = 2) -> "QDoubleSpinBox":
    sb = QDoubleSpinBox()
    sb.setRange(lo, hi)
    sb.setSingleStep(step)
    sb.setValue(default)
    sb.setDecimals(dec)
    sb.setStepType(QAbstractSpinBox.StepType.AdaptiveDecimalStepType)
    return sb


def _hline() -> "QFrame":
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setFrameShadow(QFrame.Shadow.Sunken)
    f.setFixedHeight(1)
    return f


def _sidebar(content: "QWidget", width: int = 285) -> "QScrollArea":
    sa = QScrollArea()
    sa.setWidgetResizable(True)
    sa.setFixedWidth(width)
    content.setProperty("moduleShell", "sidebar")
    sa.setWidget(content)
    sa.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    sa.setFrameShape(QFrame.Shape.NoFrame)
    return sa


def _small_label(text: str) -> "QLabel":
    lbl = QLabel(text)
    lbl.setTextFormat(Qt.TextFormat.RichText)
    lbl.setProperty("moduleShell", "sectionLabel")
    return lbl


def _btn(text: str, role: str = "secondary") -> "QPushButton":
    b = QPushButton(text)
    b.setProperty("role", role)
    return b


# ─────────────────────────────────────────────────────────────────────────────
# Shared canvas wrapper
# ─────────────────────────────────────────────────────────────────────────────

class _TSCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Thin wrapper around a single matplotlib Figure / Axes."""

    def __init__(self, figsize: tuple = (10, 5), parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._fig = Figure(figsize=figsize, dpi=96)
            self._fig.patch.set_facecolor("#FAFAFA")
            self._ax = self._fig.add_subplot(111)
            self._ax.set_facecolor("#FAFAFA")
            self._fc = FigureCanvas(self._fig)
            self._fc.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._fc)
        else:
            warn = QLabel("⚠ matplotlib chưa được cài đặt. Chạy: pip install matplotlib")
            warn.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(warn)

    @property
    def ax(self) -> Any:
        return self._ax if _MPL else None

    def flush(self) -> None:
        if _MPL:
            self._fig.tight_layout(pad=1.2)
            self._fc.draw()

    @staticmethod
    def _decorate(ax, xlabel: str = "Tháng", ylabel: str = "Giá trị", title: str = "") -> None:
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.set_xlabel(xlabel, fontsize=9, labelpad=4)
        ax.set_ylabel(ylabel, fontsize=9, labelpad=4)
        if title:
            ax.set_title(title, fontsize=10, fontweight="bold", pad=6, color="#2C3E50")
        ax.grid(axis="y", linestyle="--", alpha=0.35, color="#BDC3C7")
        ax.tick_params(axis="both", labelsize=8)

    @staticmethod
    def _xticks_years(ax, n_months: int, interval: int = 12) -> None:
        ticks = list(range(interval, n_months + 1, interval))
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"Y{t // 12}" for t in ticks], fontsize=7.5)
        ax.set_xlim(0.5, n_months + 0.5)

    @staticmethod
    def _xticks_months(ax, n_months: int, interval: int = 6) -> None:
        ticks = list(range(interval, n_months + 1, interval))
        ax.set_xticks(ticks)
        ax.set_xticklabels([f"T{t}" for t in ticks], fontsize=7.5)
        ax.set_xlim(0.5, n_months + 0.5)


# ─────────────────────────────────────────────────────────────────────────────
# Tab 1 — Xu hướng (Trend)
# ─────────────────────────────────────────────────────────────────────────────

class _TrendTab(_WidgetBase):  # type: ignore[valid-type]
    """Tab showing the Trend component T_t over 120 months (10 years)."""

    N = 120

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        self._build_ui()
        self._refresh()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sc = QWidget()
        sl = QVBoxLayout(sc)
        sl.setSpacing(8)
        sl.setContentsMargins(8, 10, 8, 10)

        # Direction
        grp_dir = QGroupBox("Hướng xu hướng")
        vl = QVBoxLayout(grp_dir)
        self._rb_inc = QRadioButton("Tăng dần  ↗")
        self._rb_dec = QRadioButton("Giảm dần  ↘")
        self._rb_inc.setChecked(True)
        _bg = QButtonGroup(grp_dir)
        _bg.addButton(self._rb_inc)
        _bg.addButton(self._rb_dec)
        vl.addWidget(self._rb_inc)
        vl.addWidget(self._rb_dec)
        self._rb_inc.toggled.connect(self._refresh)
        sl.addWidget(grp_dir)

        # Type
        grp_type = QGroupBox("Dạng xu hướng")
        vl2 = QVBoxLayout(grp_type)
        self._rb_lin = QRadioButton("Tuyến tính  (k = 1)")
        self._rb_nlin = QRadioButton("Phi tuyến  (k ≠ 1)")
        self._rb_lin.setChecked(True)
        _bg2 = QButtonGroup(grp_type)
        _bg2.addButton(self._rb_lin)
        _bg2.addButton(self._rb_nlin)
        vl2.addWidget(self._rb_lin)
        vl2.addWidget(self._rb_nlin)
        self._rb_lin.toggled.connect(self._on_type_toggled)
        sl.addWidget(grp_type)

        # Parameters
        grp_param = QGroupBox("Tham số")
        vl3 = QVBoxLayout(grp_param)
        vl3.addWidget(_small_label("Độ dốc  a  (0.05 – 10):"))
        self._sp_a = _dspin(0.05, 10.0, 0.05, 1.0)
        self._sp_a.valueChanged.connect(self._refresh)
        vl3.addWidget(self._sp_a)
        vl3.addWidget(_small_label("Lũy thừa  k  (0.10 – 3.0):"))
        self._sp_k = _dspin(0.10, 3.0, 0.05, 1.0)
        self._sp_k.setEnabled(False)
        self._sp_k.valueChanged.connect(self._refresh)
        vl3.addWidget(self._sp_k)
        sl.addWidget(grp_param)

        sl.addStretch()
        root.addWidget(_sidebar(sc))

        # ── Right: canvas + description ───────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)

        self._canvas = _TSCanvas(figsize=(10, 5))
        rl.addWidget(self._canvas, 1)
        rl.addWidget(_hline())

        self._desc = QLabel()
        self._desc.setWordWrap(True)
        self._desc.setTextFormat(Qt.TextFormat.RichText)
        self._desc.setProperty("moduleShell", "infoPanel")
        self._desc.setFixedHeight(72)
        rl.addWidget(self._desc)

        root.addWidget(right, 1)

    def _on_type_toggled(self) -> None:
        self._sp_k.setEnabled(not self._rb_lin.isChecked())
        self._refresh()

    # ── Calculation & render ──────────────────────────────────────────────────

    def _refresh(self) -> None:
        if not _MPL:
            return
        direction = 1 if self._rb_inc.isChecked() else -1
        a = self._sp_a.value()
        k = 1.0 if self._rb_lin.isChecked() else self._sp_k.value()
        t = np.arange(1, self.N + 1, dtype=float)
        T = self._compute(direction, a, k, t)

        ax = self._canvas.ax
        ax.clear()
        ax.plot(t, T, color=_C_TREND, lw=2.2, label="$T_t$", zorder=4)
        ax.fill_between(t, T, alpha=0.10, color=_C_TREND, zorder=3)
        ax.axhline(0, color="#BDC3C7", lw=0.8, zorder=1)

        _TSCanvas._decorate(ax, "Thời gian (tháng)", "$T_t$", "Thành phần Xu hướng  $T_t$")
        _TSCanvas._xticks_years(ax, self.N, interval=12)

        self._canvas.flush()

        # Description
        k_str = "1,00" if self._rb_lin.isChecked() else f"{k:.2f}"
        huong = "tăng dần" if direction == 1 else "giảm dần"
        dang = "tuyến tính" if self._rb_lin.isChecked() else "phi tuyến"
        self._desc.setText(
            f"<b>Công thức:</b>  T<sub>t</sub> = a × t<sup>k</sup>  "
            f"({huong}, {dang})&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"a = {a:.3f}, k = {k_str}<br>"
            f"T<sub>1</sub> = {T[0]:.2f}&nbsp;&nbsp;"
            f"T<sub>60</sub> = {T[59]:.2f}&nbsp;&nbsp;"
            f"T<sub>120</sub> = {T[-1]:.2f}&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"Trục x: 120 tháng = 10 năm"
        )

    @staticmethod
    def _compute(direction: int, a: float, k: float, t: np.ndarray) -> np.ndarray:
        N = len(t)
        if direction == 1:
            return a * (t ** k)
        else:
            return a * (N + 1 - t) ** k


# ─────────────────────────────────────────────────────────────────────────────
# Tab 2 — Mùa vụ (Seasonal)
# ─────────────────────────────────────────────────────────────────────────────

class _SeasonalTab(_WidgetBase):  # type: ignore[valid-type]
    """Tab showing the Seasonal component S_t over 36 months (3 years)."""

    N = 36

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sc = QWidget()
        sl = QVBoxLayout(sc)
        sl.setSpacing(8)
        sl.setContentsMargins(8, 10, 8, 10)

        grp = QGroupBox("Tham số mùa vụ")
        vl = QVBoxLayout(grp)
        vl.addWidget(_small_label("Chu kỳ lặp  P:"))
        self._cmb_P = QComboBox()
        for label, _ in _PERIOD_OPTS:
            self._cmb_P.addItem(label)
        self._cmb_P.setCurrentIndex(3)  # Năm (P=12) default
        self._cmb_P.currentIndexChanged.connect(self._refresh)
        vl.addWidget(self._cmb_P)

        vl.addWidget(_small_label("Biên độ  A  (0.1 – 20):"))
        self._sp_A = _dspin(0.1, 20.0, 0.5, 5.0)
        self._sp_A.valueChanged.connect(self._refresh)
        vl.addWidget(self._sp_A)

        vl.addWidget(_small_label("Mức nền  base  (20 – 100):"))
        self._sp_base = _dspin(20.0, 100.0, 1.0, 20.0)
        self._sp_base.setToolTip(
            "Dịch chuyển đường lên theo trục Y.\n"
            "Đặt ≥ A để đảm bảo S_t ≥ 0 (phù hợp dữ liệu kinh doanh)."
        )
        self._sp_base.valueChanged.connect(self._refresh)
        vl.addWidget(self._sp_base)

        vl.addWidget(_hline())
        vl.addWidget(_small_label(
            "<b>Độ gấp khúc</b>  h  (0.0 = mượt, 1.0 = cực đại):"
        ))
        self._sp_harmonic = _dspin(0.0, 1.0, 0.05, 0.0)
        self._sp_harmonic.setToolTip(
            "Tăng độ gấp khúc bằng cách cộng thêm các sóng hài Fourier.\n"
            "h = 0 → sin thuần (tròn trịa).\n"
            "h = 0.5 → đỉnh nhọn, đáy phẳng (dạng kinh doanh).\n"
            "h = 1.0 → răng cưa mềm (5 sóng hài)."
        )
        self._sp_harmonic.valueChanged.connect(self._refresh)
        vl.addWidget(self._sp_harmonic)

        sl.addWidget(grp)
        sl.addStretch()
        root.addWidget(_sidebar(sc))

        # ── Right ─────────────────────────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)

        self._canvas = _TSCanvas(figsize=(10, 5))
        rl.addWidget(self._canvas, 1)
        rl.addWidget(_hline())

        self._desc = QLabel()
        self._desc.setWordWrap(True)
        self._desc.setTextFormat(Qt.TextFormat.RichText)
        self._desc.setProperty("moduleShell", "infoPanel")
        self._desc.setFixedHeight(72)
        rl.addWidget(self._desc)

        root.addWidget(right, 1)

    def _refresh(self) -> None:
        if not _MPL:
            return
        _, P = _PERIOD_OPTS[self._cmb_P.currentIndex()]
        A = self._sp_A.value()
        base = self._sp_base.value()
        h = self._sp_harmonic.value()

        # ── Supersample the continuous waveform at 40× resolution ──────────────────
        # This ensures h has a VISIBLE effect even for small P (e.g. P=3) where
        # integer-month sample points alone produce identical normalized profiles.
        t_fine = np.linspace(0.0, float(self.N), self.N * 60 + 1)
        t_eff_fine = t_fine - 0.5
        theta_fine = 2 * np.pi * t_eff_fine / P
        raw_fine = (
            np.sin(theta_fine)
            + h * 0.65 * np.sin(2 * theta_fine)
            + h * 0.30 * np.sin(3 * theta_fine)
            + h * 0.15 * np.sin(4 * theta_fine)
            + h * 0.08 * np.sin(5 * theta_fine)
        )
        norm = float(np.max(np.abs(raw_fine))) or 1.0
        S_fine = base + A * raw_fine / norm

        # Monthly sample points (actual data values shown on axis)
        t_m = np.arange(1, self.N + 1, dtype=float)
        theta_m = 2 * np.pi * (t_m - 0.5) / P
        raw_m = (
            np.sin(theta_m)
            + h * 0.65 * np.sin(2 * theta_m)
            + h * 0.30 * np.sin(3 * theta_m)
            + h * 0.15 * np.sin(4 * theta_m)
            + h * 0.08 * np.sin(5 * theta_m)
        )
        S_m = base + A * raw_m / norm  # same norm as fine curve

        S_min, S_max = float(np.min(S_fine)), float(np.max(S_fine))

        ax = self._canvas.ax
        ax.clear()

        # Continuous shape guide (faint filled area)
        ax.fill_between(t_fine, S_fine, base, alpha=0.12, color=_C_SEASON, zorder=2)
        # Continuous curve
        ax.plot(t_fine, S_fine, color=_C_SEASON, lw=2.0, zorder=4)
        # Monthly data point markers
        ax.plot(t_m, S_m, "o", color=_C_SEASON, ms=3.5, zorder=5, alpha=0.7)
        ax.axhline(base, color="#BDC3C7", lw=0.9, linestyle="--", zorder=1)
        if base != 0:
            ax.axhline(0, color="#BDC3C7", lw=0.5, zorder=1)

        # Mark period boundaries
        for tick in range(P, self.N + 1, P):
            ax.axvline(tick, color="#BDC3C7", lw=0.6, linestyle=":", zorder=1)

        _TSCanvas._decorate(
            ax, "Thời gian (tháng)", "$S_t$", "Thành phần Mùa vụ  $S_t$"
        )
        _TSCanvas._xticks_months(ax, self.N, interval=max(2, P))

        self._canvas.flush()

        p_name = _PERIOD_OPTS[self._cmb_P.currentIndex()][0].strip()
        if h == 0.0:
            formula = "A × sin(θ)"
        elif h <= 0.35:
            formula = "A × (sin θ + h·{0,65·sin 2θ + …}) ÷ max"
        else:
            n_terms = 2 + int(h * 3)  # 2-5 extra terms depending on h
            formula = f"A × (sin θ + h·∑ sóng hài [{n_terms} hạng]) ÷ max"
        self._desc.setText(
            f"<b>Công thức:</b>  S<sub>t</sub> = base + {formula}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"θ = <sup>2π(t−½)</sup>/<sub>P</sub>, &nbsp;P = {P} tháng, &nbsp;h = {h:.2f}<br>"
            f"A = {A:.2f}, &nbsp;base = {base:.2f}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"Dao động trong khoảng [{S_min:.2f},&nbsp;{S_max:.2f}]"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 3 — Chu kỳ (Cyclical)
# ─────────────────────────────────────────────────────────────────────────────

class _CyclicalTab(_WidgetBase):  # type: ignore[valid-type]
    """Tab showing the Cyclical component C_t over 240 months (20 years)."""

    N = 240

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sc = QWidget()
        sl = QVBoxLayout(sc)
        sl.setSpacing(8)
        sl.setContentsMargins(8, 10, 8, 10)

        grp = QGroupBox("Tham số chu kỳ")
        vl = QVBoxLayout(grp)
        vl.addWidget(_small_label("Chu kỳ lặp  P<sub>c</sub>  (24–120 tháng):"))
        self._sp_Pc = _dspin(24.0, 120.0, 6.0, 60.0, dec=0)
        self._sp_Pc.valueChanged.connect(self._refresh)
        vl.addWidget(self._sp_Pc)

        vl.addWidget(_small_label("Biên độ  A  (0.1 – 30):"))
        self._sp_A = _dspin(0.1, 30.0, 1.0, 5.0)
        self._sp_A.valueChanged.connect(self._refresh)
        vl.addWidget(self._sp_A)

        vl.addWidget(_small_label("Mức nền  base  (30 – 200):"))
        self._sp_base = _dspin(30.0, 200.0, 5.0, 30.0)
        self._sp_base.setToolTip(
            "Dịch chuyển đường lên theo trục Y.\n"
            "Đặt ≥ A để đảm bảo C_t ≥ 0 (phù hợp dữ liệu kinh doanh)."
        )
        self._sp_base.valueChanged.connect(self._refresh)
        vl.addWidget(self._sp_base)

        sl.addWidget(grp)
        sl.addStretch()
        root.addWidget(_sidebar(sc))

        # ── Right ─────────────────────────────────────────────────────────────
        right = QWidget()
        rl = QVBoxLayout(right)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)

        self._canvas = _TSCanvas(figsize=(10, 5))
        rl.addWidget(self._canvas, 1)
        rl.addWidget(_hline())

        self._desc = QLabel()
        self._desc.setWordWrap(True)
        self._desc.setTextFormat(Qt.TextFormat.RichText)
        self._desc.setProperty("moduleShell", "infoPanel")
        self._desc.setFixedHeight(72)
        rl.addWidget(self._desc)

        root.addWidget(right, 1)

    def _refresh(self) -> None:
        if not _MPL:
            return
        Pc = self._sp_Pc.value()
        A = self._sp_A.value()
        base = self._sp_base.value()
        t = np.arange(1, self.N + 1, dtype=float)
        t_eff = t - 0.5
        C = base + A * np.sin(2 * np.pi * t_eff / Pc)
        C_min, C_max = float(np.min(C)), float(np.max(C))

        ax = self._canvas.ax
        ax.clear()
        ax.plot(t, C, color=_C_CYCLE, lw=2.2, zorder=4)
        ax.fill_between(t, C, base, alpha=0.10, color=_C_CYCLE, zorder=3)
        ax.axhline(base, color="#BDC3C7", lw=0.9, linestyle="--", zorder=2)
        if base != 0:
            ax.axhline(0, color="#BDC3C7", lw=0.5, zorder=1)

        # Mark full-cycle boundaries
        for tick in np.arange(Pc, self.N + 1, Pc):
            ax.axvline(tick, color="#BDC3C7", lw=0.6, linestyle=":", zorder=1)

        _TSCanvas._decorate(
            ax, "Thời gian (tháng)", "$C_t$", "Thành phần Chu kỳ  $C_t$"
        )
        _TSCanvas._xticks_years(ax, self.N, interval=24)

        self._canvas.flush()

        years_pc = Pc / 12
        self._desc.setText(
            f"<b>Công thức:</b>  C<sub>t</sub> = base + A × sin"
            f"(<sup>2π(t−½)</sup>/<sub>P<sub>c</sub></sub>)"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"P<sub>c</sub> = {Pc:.0f} tháng (≈ {years_pc:.1f} năm)<br>"
            f"A = {A:.2f}, &nbsp;base = {base:.2f}"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;"
            f"Dao động trong khoảng [{C_min:.2f},&nbsp;{C_max:.2f}]"
            f"&nbsp;&nbsp;|&nbsp;&nbsp;Trục x: 240 tháng = 20 năm"
        )


# ─────────────────────────────────────────────────────────────────────────────
# Tab 4 — Tổng hợp (Combined)
# ─────────────────────────────────────────────────────────────────────────────

class _MainTab(_WidgetBase):  # type: ignore[valid-type]
    """Tab showing the full combined time series Y_t over 120 months."""

    N = 120

    def __init__(self, parent: Any = None) -> None:
        super().__init__(parent)
        self._shocks: list[tuple[int, float]] = []
        self._noise_arr: np.ndarray = _BASE_NOISE_120.copy()
        self._noise_seed: int = 42
        if not _QT:
            return
        self._build_ui()
        self._refresh()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(10)

        # ── Sidebar ───────────────────────────────────────────────────────────
        sc = QWidget()
        sl = QVBoxLayout(sc)
        sl.setSpacing(8)
        sl.setContentsMargins(8, 10, 8, 10)

        # --- Model type ---
        grp_model = QGroupBox("Loại mô hình")
        vl_m = QVBoxLayout(grp_model)
        self._rb_add = QRadioButton("Cộng tính:  Y = T + S + C + I")
        self._rb_mul = QRadioButton("Nhân tính:  Y = T × Fs × Fc + I")
        self._rb_add.setChecked(True)
        _bgm = QButtonGroup(grp_model)
        _bgm.addButton(self._rb_add)
        _bgm.addButton(self._rb_mul)
        vl_m.addWidget(self._rb_add)
        vl_m.addWidget(self._rb_mul)
        self._rb_add.toggled.connect(self._refresh)
        sl.addWidget(grp_model)

        # --- Trend ---
        grp_T = QGroupBox("Xu hướng  T")
        vl_T = QVBoxLayout(grp_T)
        self._chk_T = QCheckBox("Bật xu hướng")
        self._chk_T.setChecked(True)
        self._chk_T.stateChanged.connect(self._refresh)
        vl_T.addWidget(self._chk_T)
        vl_T.addWidget(_small_label("Hướng:"))
        self._cmb_dir = QComboBox()
        self._cmb_dir.addItems(["Tăng dần  ↗", "Giảm dần  ↘"])
        self._cmb_dir.currentIndexChanged.connect(self._refresh)
        vl_T.addWidget(self._cmb_dir)
        vl_T.addWidget(_small_label("Độ dốc  a:"))
        self._sp_ta = _dspin(0.05, 10.0, 0.05, 0.5)
        self._sp_ta.valueChanged.connect(self._refresh)
        vl_T.addWidget(self._sp_ta)
        vl_T.addWidget(_small_label("Lũy thừa  k:"))
        self._sp_tk = _dspin(0.10, 3.0, 0.05, 1.0)
        self._sp_tk.valueChanged.connect(self._refresh)
        vl_T.addWidget(self._sp_tk)
        sl.addWidget(grp_T)

        # --- Seasonal ---
        grp_S = QGroupBox("Mùa vụ  S")
        vl_S = QVBoxLayout(grp_S)
        self._chk_S = QCheckBox("Bật mùa vụ")
        self._chk_S.setChecked(True)
        self._chk_S.stateChanged.connect(self._refresh)
        vl_S.addWidget(self._chk_S)
        vl_S.addWidget(_small_label("Chu kỳ  P:"))
        self._cmb_P = QComboBox()
        for lbl, _ in _PERIOD_OPTS:
            self._cmb_P.addItem(lbl)
        self._cmb_P.setCurrentIndex(3)  # Năm (P=12) default
        self._cmb_P.currentIndexChanged.connect(self._refresh)
        vl_S.addWidget(self._cmb_P)
        vl_S.addWidget(_small_label("Biên độ  A<sub>s</sub>:"))
        self._sp_sa = _dspin(0.1, 30.0, 0.5, 3.0)
        self._sp_sa.valueChanged.connect(self._refresh)
        vl_S.addWidget(self._sp_sa)
        sl.addWidget(grp_S)

        # --- Cyclical ---
        grp_C = QGroupBox("Chu kỳ  C")
        vl_C = QVBoxLayout(grp_C)
        self._chk_C = QCheckBox("Bật chu kỳ")
        self._chk_C.setChecked(True)
        self._chk_C.stateChanged.connect(self._refresh)
        vl_C.addWidget(self._chk_C)
        vl_C.addWidget(_small_label("Chu kỳ lặp  P<sub>c</sub>  (tháng):"))
        self._sp_cp = _dspin(24.0, 120.0, 6.0, 60.0, dec=0)
        self._sp_cp.valueChanged.connect(self._refresh)
        vl_C.addWidget(self._sp_cp)
        vl_C.addWidget(_small_label("Biên độ  A<sub>c</sub>:"))
        self._sp_ca = _dspin(0.1, 30.0, 0.5, 5.0)
        self._sp_ca.valueChanged.connect(self._refresh)
        vl_C.addWidget(self._sp_ca)
        sl.addWidget(grp_C)

        # --- Noise & shocks ---
        grp_I = QGroupBox("Ngẫu nhiên  I")
        vl_I = QVBoxLayout(grp_I)
        self._chk_I = QCheckBox("Bật thành phần ngẫu nhiên")
        self._chk_I.setChecked(True)
        self._chk_I.stateChanged.connect(self._refresh)
        vl_I.addWidget(self._chk_I)
        vl_I.addWidget(_small_label("Độ lệch chuẩn  σ:"))
        self._sp_sig = _dspin(0.0, 20.0, 0.1, 1.5)
        self._sp_sig.valueChanged.connect(self._refresh)
        vl_I.addWidget(self._sp_sig)
        btn_reseed = _btn("Đổi mẫu nhiễu", "subtle")
        btn_reseed.clicked.connect(self._reseed_noise)
        vl_I.addWidget(btn_reseed)
        vl_I.addWidget(_hline())
        vl_I.addWidget(_small_label("Biến động đột biến:"))
        btn_shock = _btn("Thêm đột biến", "warning")
        btn_shock.clicked.connect(self._add_shock)
        vl_I.addWidget(btn_shock)
        btn_reset = _btn("Xóa đột biến", "subtle")
        btn_reset.clicked.connect(self._reset_shocks)
        vl_I.addWidget(btn_reset)
        self._lbl_shocks = _small_label("Đột biến: 0")
        vl_I.addWidget(self._lbl_shocks)
        sl.addWidget(grp_I)

        sl.addWidget(_hline())
        self._chk_overlay = QCheckBox("Hiển thị từng thành phần")
        self._chk_overlay.setChecked(False)
        self._chk_overlay.stateChanged.connect(self._refresh)
        sl.addWidget(self._chk_overlay)

        sl.addStretch()
        root.addWidget(_sidebar(sc, width=300))

        # ── Right: canvas only ────────────────────────────────────────────────
        self._canvas = _TSCanvas(figsize=(10, 5.5))
        root.addWidget(self._canvas, 1)

    # ── Shock management ──────────────────────────────────────────────────────

    def _add_shock(self) -> None:
        comps = self._compute_components()
        Y = comps["Y"]
        scale = max(float(np.max(np.abs(Y))), 1.0) * 0.28
        val = scale * random.choice([-1, 1])
        idx = random.randint(0, self.N - 1)
        self._shocks.append((idx, val))
        self._lbl_shocks.setText(f"Đột biến: {len(self._shocks)}")
        self._refresh()

    def _reset_shocks(self) -> None:
        self._shocks.clear()
        self._lbl_shocks.setText("Đột biến: 0")
        self._refresh()

    def _reseed_noise(self) -> None:
        self._noise_seed = random.randint(0, 2**30)
        self._noise_arr = np.random.default_rng(self._noise_seed).standard_normal(self.N)
        self._refresh()

    # ── Computation ───────────────────────────────────────────────────────────

    def _compute_components(self) -> dict:
        N = self.N
        t = np.arange(1, N + 1, dtype=float)

        a = self._sp_ta.value()
        k = self._sp_tk.value()
        direction = 1 if self._cmb_dir.currentIndex() == 0 else -1
        if direction == 1:
            T = a * (t ** k)
        else:
            T = a * (N + 1 - t) ** k

        _, P_s = _PERIOD_OPTS[self._cmb_P.currentIndex()]
        A_s = self._sp_sa.value()
        S = A_s * np.sin(2 * np.pi * t / P_s)

        Pc = self._sp_cp.value()
        A_c = self._sp_ca.value()
        C = A_c * np.sin(2 * np.pi * t / Pc)

        sigma = self._sp_sig.value()
        I_noise = sigma * self._noise_arr if sigma > 0 else np.zeros(N)
        I_shocks = np.zeros(N)
        for idx, val in self._shocks:
            if 0 <= idx < N:
                I_shocks[idx] += val
        I = I_noise + I_shocks

        T_en = self._chk_T.isChecked()
        S_en = self._chk_S.isChecked()
        C_en = self._chk_C.isChecked()
        I_en = self._chk_I.isChecked()
        additive = self._rb_add.isChecked()

        if additive:
            Y = (
                (T if T_en else np.zeros(N))
                + (S if S_en else np.zeros(N))
                + (C if C_en else np.zeros(N))
                + (I if I_en else np.zeros(N))
            )
        else:
            # Multiplicative: seasonal/cyclical expressed as percentage of trend
            T_base = np.maximum(T, 0.01) if T_en else np.ones(N) * 10.0
            T_scale = max(float(np.mean(np.abs(T_base))), 1.0)
            Sf = (1 + S / T_scale) if S_en else np.ones(N)
            Cf = (1 + C / T_scale) if C_en else np.ones(N)
            Y = T_base * Sf * Cf + (I if I_en else np.zeros(N))

        return {
            "t": t, "T": T, "S": S, "C": C, "I": I,
            "Y": Y,
            "T_en": T_en, "S_en": S_en, "C_en": C_en, "I_en": I_en,
            "additive": additive,
        }

    # ── Render ────────────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        if not _MPL:
            return
        d = self._compute_components()
        t, Y = d["t"], d["Y"]
        additive = d["additive"]
        show_comp = self._chk_overlay.isChecked()

        ax = self._canvas.ax
        ax.clear()

        # ── Component overlays (thin dashed) — shown for both additive and multiplicative ──
        if show_comp:
            if d["T_en"]:
                ax.plot(t, d["T"], color=_C_TREND, lw=1.1, ls="--", alpha=0.75, label="T (xu hướng)")
            if d["S_en"]:
                ax.plot(t, d["S"], color=_C_SEASON, lw=1.1, ls="--", alpha=0.75, label="S (mùa vụ)")
            if d["C_en"]:
                ax.plot(t, d["C"], color=_C_CYCLE, lw=1.1, ls="--", alpha=0.75, label="C (chu kỳ)")

        # ── Main Y line ──
        model_lbl = "Cộng tính" if additive else "Nhân tính"
        ax.plot(t, Y, color=_C_COMBINED, lw=2.3, zorder=5, label=f"$Y_t$ ({model_lbl})")

        # ── Shock markers ──
        shock_pts = [(idx + 1, Y[idx]) for idx, _ in self._shocks if 0 <= idx < self.N]
        if shock_pts:
            sx, sy = zip(*shock_pts)
            ax.scatter(sx, sy, color=_C_NOISE, s=55, zorder=7, label="Đột biến", marker="D")

        ax.axhline(0, color="#BDC3C7", lw=0.8, zorder=1)

        if show_comp or self._shocks:
            ax.legend(loc="upper left", fontsize=8.5, framealpha=0.92, edgecolor="#BDC3C7")

        _TSCanvas._decorate(ax, "Thời gian (tháng)", "$Y_t$", "Chuỗi số Thời gian  $Y_t$")
        _TSCanvas._xticks_years(ax, self.N, interval=12)

        self._canvas.flush()

    # ── State helpers ─────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        return {
            "model": "add" if self._rb_add.isChecked() else "mul",
            "T_en": self._chk_T.isChecked(),
            "T_dir": self._cmb_dir.currentIndex(),
            "T_a": self._sp_ta.value(),
            "T_k": self._sp_tk.value(),
            "S_en": self._chk_S.isChecked(),
            "S_P_idx": self._cmb_P.currentIndex(),
            "S_A": self._sp_sa.value(),
            "C_en": self._chk_C.isChecked(),
            "C_Pc": self._sp_cp.value(),
            "C_A": self._sp_ca.value(),
            "I_en": self._chk_I.isChecked(),
            "I_sigma": self._sp_sig.value(),
            "noise_seed": self._noise_seed,
            "shocks": self._shocks.copy(),
            "overlay": self._chk_overlay.isChecked(),
        }

    def restore_state(self, s: dict) -> None:
        def _set(widget, method, key, default):
            try:
                getattr(widget, method)(s.get(key, default))
            except Exception:
                pass

        if "model" in s:
            if s["model"] == "add":
                self._rb_add.setChecked(True)
            else:
                self._rb_mul.setChecked(True)
        _set(self._chk_T, "setChecked", "T_en", True)
        _set(self._cmb_dir, "setCurrentIndex", "T_dir", 0)
        _set(self._sp_ta, "setValue", "T_a", 0.5)
        _set(self._sp_tk, "setValue", "T_k", 1.0)
        _set(self._chk_S, "setChecked", "S_en", True)
        _set(self._cmb_P, "setCurrentIndex", "S_P_idx", 3)
        _set(self._sp_sa, "setValue", "S_A", 3.0)
        _set(self._chk_C, "setChecked", "C_en", True)
        _set(self._sp_cp, "setValue", "C_Pc", 60.0)
        _set(self._sp_ca, "setValue", "C_A", 5.0)
        _set(self._chk_I, "setChecked", "I_en", True)
        _set(self._sp_sig, "setValue", "I_sigma", 1.5)
        if "noise_seed" in s:
            self._noise_seed = int(s["noise_seed"])
            self._noise_arr = np.random.default_rng(self._noise_seed).standard_normal(self.N)
        if "shocks" in s:
            self._shocks = list(s["shocks"])
            self._lbl_shocks.setText(f"Đột biến: {len(self._shocks)}")
        if "overlay" in s:
            self._chk_overlay.setChecked(bool(s["overlay"]))


# ─────────────────────────────────────────────────────────────────────────────
# Main Module class
# ─────────────────────────────────────────────────────────────────────────────

class TimeSeriesModule(BaseModule):
    """IIMP module — Mô phỏng Chuỗi số Thời gian v1.0.0.

    Four tabs:
      Tab 1  Xu hướng  (Trend T_t)      — direction + power function
      Tab 2  Mùa vụ   (Seasonal S_t)   — sine wave with fixed period
      Tab 3  Chu kỳ   (Cyclical C_t)   — long-period sine wave
      Tab 4  Tổng hợp (Y_t)            — combined additive / multiplicative
    """

    MODULE_ID = "time_series_simulation"
    MODULE_VERSION = "1.0.0"

    def __init__(self, manifest: dict, context: ModuleContext) -> None:
        super().__init__(manifest=manifest, context=context)
        self._logger = context.logger
        self._settings_svc = context.settings_service
        self._activity_svc = context.activity_service

        # UI refs
        self._view: "QWidget | None" = None
        self._tabs: "QTabWidget | None" = None
        self._tab_trend: "_TrendTab | None" = None
        self._tab_seasonal: "_SeasonalTab | None" = None
        self._tab_cyclical: "_CyclicalTab | None" = None
        self._tab_main: "_MainTab | None" = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_load")

    def build_view(self) -> "QWidget":
        if not _QT:
            raise RuntimeError("PySide6 is required to build the module view.")

        root = QWidget()
        root.setObjectName("tsModuleRoot")
        root.setProperty("moduleShell", "root")
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setTabPosition(QTabWidget.TabPosition.North)

        self._tab_trend = _TrendTab()
        self._tab_seasonal = _SeasonalTab()
        self._tab_cyclical = _CyclicalTab()
        self._tab_main = _MainTab()

        tabs.addTab(self._tab_trend, "📈  Xu hướng")
        tabs.addTab(self._tab_seasonal, "🔄  Mùa vụ")
        tabs.addTab(self._tab_cyclical, "〰  Chu kỳ")
        tabs.addTab(self._tab_main, "📊  Tổng hợp")

        layout.addWidget(tabs)

        self._view = root
        self._tabs = tabs
        return root

    def on_activate(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_activate")
        self._activity_svc.log_activity(self.MODULE_ID, "activated")

    def on_deactivate(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_deactivate")

    def on_unload(self) -> None:
        self._logger.info(f"[{self.MODULE_ID}] on_unload")
        self._view = None
        self._tabs = None
        self._tab_trend = None
        self._tab_seasonal = None
        self._tab_cyclical = None
        self._tab_main = None

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict:
        state: dict = {"_state_version": "1.0.0"}
        if self._tabs is not None:
            state["active_tab"] = self._tabs.currentIndex()
        if self._tab_main is not None:
            state["main"] = self._tab_main.get_state()
        return state

    def restore_state(self, state: dict) -> None:
        if not isinstance(state, dict):
            return
        try:
            if self._tabs is not None and "active_tab" in state:
                self._tabs.setCurrentIndex(int(state["active_tab"]))
            if self._tab_main is not None and "main" in state:
                self._tab_main.restore_state(state["main"])
        except Exception as exc:
            self._logger.warning(f"[{self.MODULE_ID}] restore_state failed: {exc}")
