"""Supply-Demand Simulation Module — v1.0.0

Three-tab interactive simulation of microeconomic supply and demand:

  Tab 1  Mô hình Cung - Cầu  — Full model with equilibrium, surplus/shortage
                                and factor sliders that shift S/D curves
  Tab 2  Đường Cung          — Supply curve deep-dive with 5 factor sliders
  Tab 3  Đường Cầu           — Demand curve deep-dive with 5 factor sliders
"""
from __future__ import annotations

from typing import Any

import numpy as np

try:
    from PySide6.QtCore import Qt, QSize, QTimer
    from PySide6.QtGui import QFont, QColor, QPalette
    from PySide6.QtWidgets import (
        QCheckBox,
        QComboBox,
        QDialog,
        QFrame,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSlider,
        QTabWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
        QGridLayout,
        QSpacerItem,
    )
    _QT = True
except ImportError:
    _QT = False

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.patches as mpatches
    _MPL = True
except ImportError:
    _MPL = False

from core.module_runtime.base_module import BaseModule
from core.module_runtime.module_context import ModuleContext

# ── Constants ──────────────────────────────────────────────────────────────

# Supply curve color (orange)
COLOR_SUPPLY = "#E07B39"
# Demand curve color (green)
COLOR_DEMAND = "#2E8B57"
# Equilibrium point
COLOR_EQ = "#8E44AD"
# Surplus fill
COLOR_SURPLUS = "#E74C3C"
# Shortage fill
COLOR_SHORTAGE = "#3498DB"
# Grid / background
COLOR_BG = "#FAFAFA"
# Axis
COLOR_AXIS = "#34495E"

# Base linear model: Q = a + b*P
# Supply: Qs = -10 + 3*P  =>  P = (Qs + 10) / 3
# Demand: Qd =  70 - 2*P  =>  P = (70 - Qd) / 2
# Equilibrium: -10 + 3P = 70 - 2P  => 5P = 80 => P* = 16, Q* = 38

BASE_S_INTERCEPT = -10.0   # Qs at P=0 (supply intercept on Q axis)
BASE_S_SLOPE = 3.0         # dQs/dP
BASE_D_INTERCEPT = 70.0    # Qd at P=0 (demand intercept on Q axis)
BASE_D_SLOPE = -2.0        # dQd/dP  (negative)

P_MIN = 0.0
P_MAX = 40.0
Q_MIN = 0.0
Q_MAX = 150.0

# ── Supply factors (Tab 1 + Tab 2) ─────────────────────────────────────────

SUPPLY_FACTORS = [
    {
        "id": "input_cost",
        "label": "Giá các yếu tố đầu vào",
        "tooltip_up": "Chi phí đầu vào giảm → sản xuất rẻ hơn → Cung tăng → đường S dịch sang phải",
        "tooltip_down": "Chi phí đầu vào tăng (nguyên liệu, nhân công) → sản xuất đắt hơn → Cung giảm → đường S dịch sang trái",
        "direction": "supply",
        "shift_sign": -1,
    },
    {
        "id": "technology",
        "label": "Công nghệ sản xuất",
        "tooltip_up": "Công nghệ tiến bộ → sản xuất hiệu quả hơn, chi phí thấp hơn → Cung tăng → đường S dịch sang phải",
        "tooltip_down": "Công nghệ kém đi → chi phí sản xuất tăng → Cung giảm → đường S dịch sang trái",
        "direction": "supply",
        "shift_sign": 1,
    },
    {
        "id": "producer_expect",
        "label": "Kỳ vọng của nhà sản xuất",
        "tooltip_up": "Kỳ vọng giá giảm → nhà SX bán hàng sớm → Cung hiện tại tăng → đường S dịch sang phải",
        "tooltip_down": "Kỳ vọng giá tăng → nhà SX tích trữ hàng → Cung hiện tại giảm → đường S dịch sang trái",
        "direction": "supply",
        "shift_sign": -1,
    },
    {
        "id": "tax",
        "label": "Thuế",
        "tooltip_up": "Thuế giảm → chi phí sản xuất giảm → Cung tăng → đường S dịch sang phải",
        "tooltip_down": "Thuế tăng → chi phí sản xuất tăng → Cung giảm → đường S dịch sang trái",
        "direction": "supply",
        "shift_sign": -1,
    },
    {
        "id": "subsidy",
        "label": "Trợ cấp",
        "tooltip_up": "Trợ cấp tăng → chi phí sản xuất thực tế giảm → Cung tăng → đường S dịch sang phải",
        "tooltip_down": "Trợ cấp giảm → chi phí tăng → Cung giảm → đường S dịch sang trái",
        "direction": "supply",
        "shift_sign": 1,
    },
    {
        "id": "num_sellers",
        "label": "Số lượng người bán",
        "tooltip_up": "Nhiều doanh nghiệp gia nhập ngành → Cung thị trường tăng → đường S dịch sang phải",
        "tooltip_down": "Doanh nghiệp rời khỏi ngành → Cung thị trường giảm → đường S dịch sang trái",
        "direction": "supply",
        "shift_sign": 1,
    },
]

# ── Demand factors (Tab 1 + Tab 3) ─────────────────────────────────────────

DEMAND_FACTORS = [
    {
        "id": "income_normal",
        "label": "Thu nhập (hàng thông thường)",
        "tooltip_up": "Thu nhập tăng → người mua chi tiêu nhiều hơn cho hàng thông thường → Cầu tăng → đường D dịch sang phải",
        "tooltip_down": "Thu nhập giảm → cầu hàng thông thường giảm → đường D dịch sang trái",
        "direction": "demand",
        "shift_sign": 1,
    },
    {
        "id": "income_inferior",
        "label": "Thu nhập (hàng thứ cấp)",
        "tooltip_up": "Thu nhập giảm → người mua chuyển sang dùng hàng thứ cấp (rẻ hơn) → Cầu tăng → đường D dịch sang phải",
        "tooltip_down": "Thu nhập tăng → người mua bỏ hàng thứ cấp, dùng hàng tốt hơn → Cầu giảm → đường D dịch sang trái",
        "direction": "demand",
        "shift_sign": -1,
    },
    {
        "id": "substitute",
        "label": "Giá hàng thay thế",
        "tooltip_up": "Giá hàng thay thế tăng → người mua chuyển sang mặt hàng này → Cầu tăng → đường D dịch sang phải",
        "tooltip_down": "Giá hàng thay thế giảm → người mua ưu tiên hàng thay thế → Cầu giảm → đường D dịch sang trái",
        "direction": "demand",
        "shift_sign": 1,
    },
    {
        "id": "complement",
        "label": "Giá hàng bổ sung",
        "tooltip_up": "Giá hàng bổ sung giảm → người mua dùng cả hai nhiều hơn → Cầu tăng → đường D dịch sang phải",
        "tooltip_down": "Giá hàng bổ sung tăng → nhu cầu cả gói giảm → Cầu giảm → đường D dịch sang trái",
        "direction": "demand",
        "shift_sign": -1,
    },
    {
        "id": "preference",
        "label": "Sở thích và Thị hiếu",
        "tooltip_up": "Thị hiếu / xu hướng tăng → người mua chuộng mặt hàng này hơn → Cầu tăng → đường D dịch sang phải",
        "tooltip_down": "Thị hiếu giảm → người mua thờ ơ với mặt hàng này → Cầu giảm → đường D dịch sang trái",
        "direction": "demand",
        "shift_sign": 1,
    },
    {
        "id": "consumer_expect",
        "label": "Kỳ vọng về giá",
        "tooltip_up": "Kỳ vọng giá sẽ tăng → người mua mua sớm → Cầu hiện tại tăng → đường D dịch sang phải",
        "tooltip_down": "Kỳ vọng giá sẽ giảm → người mua trì hoãn mua → Cầu hiện tại giảm → đường D dịch sang trái",
        "direction": "demand",
        "shift_sign": 1,
    },
    {
        "id": "num_buyers",
        "label": "Số lượng người mua",
        "tooltip_up": "Thị trường mở rộng / dân số tăng → Cầu tăng → đường D dịch sang phải",
        "tooltip_down": "Thị trường thu hẹp / dân số giảm → Cầu giảm → đường D dịch sang trái",
        "direction": "demand",
        "shift_sign": 1,
    },
]

# All factors for Tab 1 selection
ALL_FACTORS = SUPPLY_FACTORS + DEMAND_FACTORS

# Model assumptions text
ASSUMPTIONS_TEXT = """<h3 style="color:#2C3E50;">Các giả định khi xây dựng mô hình Cung - Cầu</h3>

<p><b>1. Ceteris Paribus (Các yếu tố khác không đổi)</b><br>
Khi xem xét tác động của giá lên lượng cung/cầu, ta giả định tất cả các yếu tố khác (thu nhập, công nghệ, thuế...) đều giữ nguyên.</p>

<p><b>2. Thị trường cạnh tranh hoàn hảo</b><br>
Có rất nhiều người mua và người bán, sản phẩm đồng nhất, và không ai có đủ quyền lực để tự ý điều khiển giá (người chấp nhận giá).</p>

<p><b>3. Hành vi hợp lý (Rationality)</b><br>
Người tiêu dùng luôn muốn tối đa hóa lợi ích; nhà sản xuất luôn muốn tối đa hóa lợi nhuận.</p>

<p><b>4. Thông tin hoàn hảo</b><br>
Mọi người tham gia thị trường đều biết rõ về giá cả, chất lượng và các điều kiện giao dịch.</p>

<p><b>5. Không có ngoại ứng</b><br>
Các hành vi mua bán chỉ ảnh hưởng đến người trong cuộc, không gây tác động lên bên thứ ba.</p>"""

# Law tooltips
LAW_SUPPLY_PRICE = "Luật Cung: Khi giá tăng, lượng cung tăng (và ngược lại), giả định các yếu tố khác không đổi."
LAW_DEMAND_PRICE = "Luật Cầu: Khi giá tăng, lượng cầu giảm (và ngược lại), giả định các yếu tố khác không đổi."

# ─────────────────────────────────────────────────────────────────────────────
# Helper: compute Qs and Qd given intercepts, slope and price P
# ─────────────────────────────────────────────────────────────────────────────

def _qs(p: float, intercept: float, slope: float) -> float:
    return max(0.0, intercept + slope * p)


def _qd(p: float, intercept: float, slope: float) -> float:
    return max(0.0, intercept + slope * p)


def _equilibrium(s_intercept: float, s_slope: float,
                 d_intercept: float, d_slope: float) -> tuple[float, float]:
    """Solve: s_intercept + s_slope*P = d_intercept + d_slope*P"""
    denom = d_slope - s_slope
    if abs(denom) < 1e-9:
        return (P_MAX / 2, Q_MAX / 2)
    p_eq = (s_intercept - d_intercept) / denom
    p_eq = max(P_MIN, min(P_MAX, p_eq))
    q_eq = _qs(p_eq, s_intercept, s_slope)
    return (p_eq, q_eq)


# ─────────────────────────────────────────────────────────────────────────────
# Canvas — Tab 1 (Supply + Demand model)
# ─────────────────────────────────────────────────────────────────────────────

_CanvasBase = QWidget if _QT else object  # type: ignore[misc]


class _SDCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Matplotlib canvas for the supply-demand model (Tab 1)."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _MPL:
            self._fig = Figure(figsize=(7, 5.5), dpi=100, facecolor=COLOR_BG)
            self._ax = self._fig.add_subplot(111)
            self._fig.subplots_adjust(left=0.09, right=0.97, top=0.97, bottom=0.11)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
        else:
            layout.addWidget(QLabel("⚠ matplotlib chưa được cài."))

    def _setup_axes(self) -> None:
        ax = self._ax
        ax.set_facecolor(COLOR_BG)
        ax.set_xlim(Q_MIN, Q_MAX)
        ax.set_ylim(P_MIN, P_MAX)
        ax.set_xlabel("Lượng (Q)", fontsize=12, color=COLOR_AXIS)
        ax.set_ylabel("Giá (P)", fontsize=12, color=COLOR_AXIS)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLOR_AXIS)
        ax.spines["bottom"].set_color(COLOR_AXIS)
        ax.tick_params(colors=COLOR_AXIS, labelsize=11)
        ax.grid(True, linestyle="--", alpha=0.3, color="#BDC3C7")

    def render(
        self,
        s_intercept: float,
        s_slope: float,
        d_intercept: float,
        d_slope: float,
        current_price: float,
    ) -> dict:
        """Render full S-D model. Returns dict with computed values."""
        if not _MPL:
            return {}

        ax = self._ax
        ax.clear()
        self._setup_axes()

        p_arr = np.linspace(P_MIN, P_MAX, 500)

        # Supply curve: Q as function of P
        qs_arr = np.clip(s_intercept + s_slope * p_arr, Q_MIN, Q_MAX)
        # Demand curve: Q as function of P
        qd_arr = np.clip(d_intercept + d_slope * p_arr, Q_MIN, Q_MAX)

        # Plot S curve (horizontal = Q, vertical = P)
        ax.plot(qs_arr, p_arr, color=COLOR_SUPPLY, lw=2.2,
                label="Cung (S)", zorder=5)
        # Plot D curve
        ax.plot(qd_arr, p_arr, color=COLOR_DEMAND, lw=2.2,
                label="Cầu (D)", zorder=5)

        # Equilibrium
        p_eq, q_eq = _equilibrium(s_intercept, s_slope, d_intercept, d_slope)
        q_eq = float(np.clip(q_eq, Q_MIN, Q_MAX))
        # Economic Q values (for labels) and visual Q values (clipped, for markers/fill)
        qs_econ = _qs(current_price, s_intercept, s_slope)
        qd_econ = _qd(current_price, d_intercept, d_slope)
        qs_current = float(np.clip(s_intercept + s_slope * current_price, Q_MIN, Q_MAX))
        qd_current = float(np.clip(d_intercept + d_slope * current_price, Q_MIN, Q_MAX))

        # ── Dư thừa / Thiếu hụt: double-headed arrow showing Qs−Qd gap ──────
        TOLERANCE = 0.5
        _gap_drawn = False
        if current_price > p_eq + TOLERANCE:
            # Dư thừa: Qs > Qd — arrow from Qd to Qs at current_price
            q_left, q_right = qd_current, qs_current
            gap_color = COLOR_SURPLUS
            gap_text = f"Dư thừa: Qs−Qd = {qs_econ - qd_econ:.1f}"
            _gap_drawn = abs(q_right - q_left) > 0.5
        elif current_price < p_eq - TOLERANCE:
            # Thiếu hụt: Qd > Qs — arrow from Qs to Qd at current_price
            q_left, q_right = qs_current, qd_current
            gap_color = COLOR_SHORTAGE
            gap_text = f"Thiếu hụt: Qd−Qs = {qd_econ - qs_econ:.1f}"
            _gap_drawn = abs(q_right - q_left) > 0.5
        else:
            q_left = q_right = 0.0
            gap_color = COLOR_EQ
            gap_text = ""

        if _gap_drawn:
            # Vertical drop-lines from both points down to Q axis
            ax.plot([q_left, q_left], [0, current_price],
                    ":", color=gap_color, lw=1.0, alpha=0.65, zorder=3)
            ax.plot([q_right, q_right], [0, current_price],
                    ":", color=gap_color, lw=1.0, alpha=0.65, zorder=3)
            # Double-headed horizontal arrow
            ax.annotate(
                "",
                xy=(q_right, current_price),
                xytext=(q_left, current_price),
                arrowprops=dict(
                    arrowstyle="<->",
                    color=gap_color,
                    lw=2.2,
                    mutation_scale=18,
                ),
                zorder=8,
            )
            # Label above/below the arrow midpoint depending on price level
            mid_q = (q_left + q_right) / 2
            y_frac = current_price / P_MAX
            va_pos = "bottom" if y_frac < 0.6 else "top"
            y_offset = current_price + (0.8 if y_frac < 0.6 else -0.8)
            ax.text(
                mid_q, y_offset, gap_text,
                color=gap_color, fontsize=10, fontweight="bold",
                va=va_pos, ha="center", zorder=12,
                bbox=dict(boxstyle="round,pad=0.35",
                          fc="white", ec=gap_color, alpha=0.92, lw=1.2),
            )

        # Current price horizontal line + points on both curves
        ax.axhline(current_price, color="#95A5A6", linestyle=":", lw=1.2, zorder=2)
        ax.scatter([qs_current], [current_price],
                   color=COLOR_SUPPLY, s=60, zorder=9, edgecolors="white", lw=1.2)
        ax.scatter([qd_current], [current_price],
                   color=COLOR_DEMAND, s=60, zorder=9, edgecolors="white", lw=1.2)

        # Equilibrium dashed reference lines
        ax.axhline(p_eq, color=COLOR_EQ, linestyle="--", lw=0.8, alpha=0.5, zorder=2)
        ax.axvline(q_eq, color=COLOR_EQ, linestyle="--", lw=0.8, alpha=0.5, zorder=2)

        ax.legend(loc="upper right", fontsize=11, framealpha=0.9)
        self._canvas.draw()

        pos = self._ax.get_position()
        return {
            "p_eq": p_eq,
            "q_eq": q_eq,
            "qs_current": qs_current,
            "qd_current": qd_current,
            "ax_top_frac": 1.0 - pos.y1,
            "ax_bottom_frac": pos.y0,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Canvas — Tab 2 & 3 (Single curve)
# ─────────────────────────────────────────────────────────────────────────────

class _SingleCurveCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Matplotlib canvas for a single supply or demand curve."""

    def __init__(self, curve_type: str = "supply", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._curve_type = curve_type
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if _MPL:
            self._fig = Figure(figsize=(6.5, 5), dpi=100, facecolor=COLOR_BG)
            self._ax = self._fig.add_subplot(111)
            self._fig.subplots_adjust(left=0.09, right=0.97, top=0.97, bottom=0.11)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
        else:
            layout.addWidget(QLabel("⚠ matplotlib chưa được cài."))

    def _setup_axes(self) -> None:
        ax = self._ax
        ax.set_facecolor(COLOR_BG)
        ax.set_xlim(Q_MIN, Q_MAX)
        ax.set_ylim(P_MIN, P_MAX)
        ax.set_xlabel("Lượng (Q)", fontsize=12, color=COLOR_AXIS)
        ax.set_ylabel("Giá (P)", fontsize=12, color=COLOR_AXIS)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLOR_AXIS)
        ax.spines["bottom"].set_color(COLOR_AXIS)
        ax.tick_params(colors=COLOR_AXIS, labelsize=11)
        ax.grid(True, linestyle="--", alpha=0.3, color="#BDC3C7")

    def render(self, intercept: float, slope: float, current_price: float) -> None:
        if not _MPL:
            return

        ax = self._ax
        ax.clear()
        self._setup_axes()

        p_arr = np.linspace(P_MIN, P_MAX, 500)
        q_arr = np.clip(intercept + slope * p_arr, Q_MIN, Q_MAX)

        is_supply = self._curve_type == "supply"
        color = COLOR_SUPPLY if is_supply else COLOR_DEMAND
        label = "Cung (S)" if is_supply else "Cầu (D)"

        ax.plot(q_arr, p_arr, color=color, lw=2.4, label=label, zorder=5)

        # Moving point on the curve
        q_current = max(0.0, intercept + slope * current_price)
        ax.scatter([q_current], [current_price], color=color, s=70, zorder=9, edgecolors="white", lw=1.5)

        # Dashed reference lines to axes
        ax.axhline(current_price, color="#95A5A6", linestyle=":", lw=1.2, zorder=2)
        ax.axvline(q_current, color="#95A5A6", linestyle=":", lw=1.2, zorder=2)

        # Fixed-position P/Q info box — always visible regardless of slider position
        ax.text(
            0.04, 0.96,
            f"P = {current_price:.1f}\nQ = {q_current:.1f}",
            transform=ax.transAxes,
            fontsize=13, color=color, fontweight="bold",
            va="top", ha="left", zorder=10,
            bbox=dict(boxstyle="round,pad=0.5", fc="white", ec=color,
                      alpha=0.95, lw=1.5),
        )

        ax.legend(loc="upper right", fontsize=11, framealpha=0.9)
        self._canvas.draw()

        pos = self._ax.get_position()
        return {"ax_top_frac": 1.0 - pos.y1, "ax_bottom_frac": pos.y0}


# ─────────────────────────────────────────────────────────────────────────────
# Vertical price slider widget
# ─────────────────────────────────────────────────────────────────────────────

class _VerticalPriceSlider(QWidget):
    """Vertical price slider with dynamic margins that align its track with the matplotlib y-axis."""

    def __init__(self, label: str = "P (Giá)", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # Fractions of figure height above / below the matplotlib axes.
        # Updated after every canvas.render() via set_axis_fracs().
        self._top_frac: float = 0.06
        self._bottom_frac: float = 0.13

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)
        outer.setSpacing(2)

        self._title_label = QLabel(label)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(11)
        self._title_label.setFont(font)
        outer.addWidget(self._title_label)

        # Container whose top/bottom margins are adjusted to align with the y-axis
        self._slider_container = QWidget()
        self._slider_layout = QVBoxLayout(self._slider_container)
        self._slider_layout.setContentsMargins(0, 0, 0, 0)
        self._slider_layout.setSpacing(0)

        self.slider = QSlider(Qt.Orientation.Vertical)
        self.slider.setMinimum(int(P_MIN * 10))
        self.slider.setMaximum(int(P_MAX * 10))
        self.slider.setValue(160)  # Default P = 16 (equilibrium)
        self.slider.setSingleStep(1)
        self.slider.setPageStep(10)
        self.slider.setStyleSheet("""
            QSlider::groove:vertical {
                background: #BDC3C7;
                width: 8px;
                border-radius: 4px;
            }
            QSlider::handle:vertical {
                background: #2C3E50;
                border: 2px solid #ECF0F1;
                width: 22px;
                height: 22px;
                border-radius: 11px;
                margin: -7px;
            }
            QSlider::sub-page:vertical {
                background: #3498DB;
                border-radius: 4px;
            }
        """)
        self._slider_layout.addWidget(
            self.slider, stretch=1, alignment=Qt.AlignmentFlag.AlignHCenter
        )
        outer.addWidget(self._slider_container, stretch=1)

        self._value_label = QLabel("P = 16.0")
        self._value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_label.setStyleSheet(
            "font-weight: bold; font-size: 13px; color: #2C3E50;"
            "background: #ECF0F1; border-radius: 4px; padding: 4px;"
        )
        outer.addWidget(self._value_label)

        self.slider.valueChanged.connect(self._update_label)

    def _update_label(self, val: int) -> None:
        self._value_label.setText(f"P = {val / 10:.1f}")

    @property
    def price(self) -> float:
        return self.slider.value() / 10.0

    def set_axis_fracs(self, top_frac: float, bottom_frac: float) -> None:
        """Update fractions from matplotlib axes position and reapply margins."""
        self._top_frac = top_frac
        self._bottom_frac = bottom_frac
        self._apply_margins()

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        self._apply_margins()

    def _apply_margins(self) -> None:
        """Set top/bottom margins on the slider container so the track aligns with y-axis."""
        total_h = self.height()
        if total_h <= 0:
            return
        title_h = self._title_label.sizeHint().height() + 2
        value_h = self._value_label.sizeHint().height() + 2
        top_px = max(0, int(self._top_frac * total_h) - title_h)
        bot_px = max(0, int(self._bottom_frac * total_h) - value_h)
        self._slider_layout.setContentsMargins(0, top_px, 0, bot_px)


# ─────────────────────────────────────────────────────────────────────────────
# Horizontal factor slider widget
# ─────────────────────────────────────────────────────────────────────────────

# Slider handle shapes encoded as Unicode for display
HANDLE_SHAPES = ["■", "▲", "◆"]


class _FactorSlider(QWidget):
    """A horizontal slider for a single factor that shifts a curve."""

    def __init__(
        self,
        factor: dict,
        shape_symbol: str = "■",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._factor = factor
        self._shape = shape_symbol
        self._active = False

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(2, 2, 2, 2)
        self._layout.setSpacing(2)

        # Header row: shape + label
        header = QHBoxLayout()
        self._shape_lbl = QLabel(shape_symbol)
        self._shape_lbl.setStyleSheet("font-size: 16px; color: #7F8C8D;")
        header.addWidget(self._shape_lbl)
        self._name_lbl = QLabel(factor["label"])
        self._name_lbl.setStyleSheet("font-size: 11px; color: #7F8C8D;")
        header.addWidget(self._name_lbl, stretch=1)
        self._layout.addLayout(header)

        # Slider row
        slider_row = QHBoxLayout()
        left_lbl = QLabel("◀")
        left_lbl.setStyleSheet("color: #BDC3C7; font-size: 10px;")
        slider_row.addWidget(left_lbl)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(-50)
        self.slider.setMaximum(50)
        self.slider.setValue(0)
        self.slider.setSingleStep(1)
        self.slider.setEnabled(False)
        self._apply_inactive_style()
        slider_row.addWidget(self.slider, stretch=1)

        right_lbl = QLabel("▶")
        right_lbl.setStyleSheet("color: #BDC3C7; font-size: 10px;")
        slider_row.addWidget(right_lbl)
        self._layout.addLayout(slider_row)

    def _apply_active_style(self) -> None:
        color = COLOR_SUPPLY if self._factor["direction"] == "supply" else COLOR_DEMAND
        self.slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                background: #BDC3C7;
                height: 8px;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {color};
                border: 2px solid white;
                width: 20px;
                height: 20px;
                border-radius: 10px;
                margin: -6px;
            }}
            QSlider::sub-page:horizontal {{
                background: {color};
                opacity: 0.5;
                border-radius: 4px;
            }}
        """)
        self._shape_lbl.setStyleSheet(f"font-size: 16px; color: {color}; font-weight:bold;")
        self._name_lbl.setStyleSheet(f"font-size: 11px; color: {color}; font-weight: bold;")

    def _apply_inactive_style(self) -> None:
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: #E0E0E0;
                height: 6px;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #BDBDBD;
                border: 1px solid #9E9E9E;
                width: 14px;
                height: 14px;
                border-radius: 7px;
                margin: -4px;
            }
        """)
        self._shape_lbl.setStyleSheet("font-size: 16px; color: #BDBDBD;")
        self._name_lbl.setStyleSheet("font-size: 11px; color: #BDBDBD;")

    def activate(self, factor: dict) -> None:
        self._factor = factor
        self._active = True
        self._name_lbl.setText(factor["label"])
        self.slider.setValue(0)
        self.slider.setEnabled(True)
        self._apply_active_style()

    def deactivate(self) -> None:
        self._active = False
        self.slider.setValue(0)
        self.slider.setEnabled(False)
        self._apply_inactive_style()
        self._name_lbl.setText("(chưa chọn)")
        self._shape_lbl.setStyleSheet("font-size: 16px; color: #BDBDBD;")

    @property
    def shift_value(self) -> float:
        """Returns the shift magnitude * sign of factor direction."""
        if not self._active:
            return 0.0
        return self.slider.value() * self._factor["shift_sign"] * 0.3

    @property
    def factor(self) -> dict:
        return self._factor

    @property
    def is_active(self) -> bool:
        return self._active


# ─────────────────────────────────────────────────────────────────────────────
# Assumptions dialog
# ─────────────────────────────────────────────────────────────────────────────

class _AssumptionsDialog(QDialog):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Giả định của mô hình Cung - Cầu")
        self.setMinimumWidth(480)
        self.setMinimumHeight(380)
        layout = QVBoxLayout(self)

        text = QTextEdit()
        text.setReadOnly(True)
        text.setHtml(ASSUMPTIONS_TEXT)
        layout.addWidget(text)

        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


# ─────────────────────────────────────────────────────────────────────────────
# Welfare canvas + dialog
# ─────────────────────────────────────────────────────────────────────────────

class _WelfareCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Matplotlib canvas for CS/PS/DWL welfare analysis."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        if _MPL:
            self._fig = Figure(figsize=(7, 5.2), dpi=100, facecolor=COLOR_BG)
            self._ax = self._fig.add_subplot(111)
            self._fig.subplots_adjust(left=0.09, right=0.97, top=0.97, bottom=0.11)
            self._canvas = FigureCanvas(self._fig)
            self._canvas.setSizePolicy(
                QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
            )
            layout.addWidget(self._canvas)
        else:
            layout.addWidget(QLabel("⚠ matplotlib chưa được cài."))

    def _setup_axes(self) -> None:
        ax = self._ax
        ax.set_facecolor(COLOR_BG)
        ax.set_xlim(Q_MIN, Q_MAX * 0.7)
        ax.set_ylim(P_MIN, P_MAX)
        ax.set_xlabel("Lượng (Q)", fontsize=12, color=COLOR_AXIS)
        ax.set_ylabel("Giá (P)", fontsize=12, color=COLOR_AXIS)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color(COLOR_AXIS)
        ax.spines["bottom"].set_color(COLOR_AXIS)
        ax.tick_params(colors=COLOR_AXIS, labelsize=11)
        ax.grid(True, linestyle="--", alpha=0.3, color="#BDC3C7")

    def render(
        self,
        s_intercept: float, s_slope: float,
        d_intercept: float, d_slope: float,
        p_control: float | None = None,
        control_type: str | None = None,
    ) -> dict:
        if not _MPL:
            return {}

        ax = self._ax
        ax.clear()
        self._setup_axes()

        p_arr = np.linspace(P_MIN, P_MAX, 500)
        qs_arr = np.clip(s_intercept + s_slope * p_arr, Q_MIN, Q_MAX)
        qd_arr = np.clip(d_intercept + d_slope * p_arr, Q_MIN, Q_MAX)
        ax.plot(qs_arr, p_arr, color=COLOR_SUPPLY, lw=2.2, label="Cung (S)", zorder=5)
        ax.plot(qd_arr, p_arr, color=COLOR_DEMAND, lw=2.2, label="Cầu (D)", zorder=5)

        p_eq, q_eq = _equilibrium(s_intercept, s_slope, d_intercept, d_slope)
        q_eq = float(np.clip(q_eq, Q_MIN, Q_MAX))

        # Price-axis intercepts (at Q=0)
        p_d_axis = float(np.clip(-d_intercept / d_slope, P_MIN, P_MAX))
        p_s_axis = float(np.clip(-s_intercept / s_slope, P_MIN, P_MAX))

        # Baseline total social welfare at equilibrium
        cs_eq = 0.5 * q_eq * (p_d_axis - p_eq)
        ps_eq = 0.5 * q_eq * (p_eq - p_s_axis)
        total_sw_eq = cs_eq + ps_eq

        # Helper: inverse supply/demand
        def inv_d(q: float) -> float:
            return float((q - d_intercept) / d_slope)
        def inv_s(q: float) -> float:
            return float((q - s_intercept) / s_slope)

        # ── Determine CS / PS / DWL geometry ─────────────────────────────────
        effective_type = control_type
        if effective_type == "ceiling" and (p_control is None or p_control >= p_eq - 0.1):
            effective_type = None
        if effective_type == "floor" and (p_control is None or p_control <= p_eq + 0.1):
            effective_type = None

        if effective_type is None:
            # Equilibrium: CS triangle, PS triangle, no DWL
            cs_poly = [(0, p_d_axis), (q_eq, p_eq), (0, p_eq)]
            ps_poly = [(0, p_s_axis), (q_eq, p_eq), (0, p_eq)]
            cs_val, ps_val, dwl_val = cs_eq, ps_eq, 0.0

        elif effective_type == "ceiling":
            q_t = float(np.clip(s_intercept + s_slope * p_control, Q_MIN, Q_MAX))
            p_d_qt = inv_d(q_t)
            # CS trapezoid
            cs_poly = [(0, p_d_axis), (q_t, p_d_qt), (q_t, p_control), (0, p_control)]
            # PS triangle
            ps_poly = [(0, p_s_axis), (q_t, p_control), (0, p_control)]
            # DWL triangle
            dwl_poly = [(q_t, p_d_qt), (q_eq, p_eq), (q_t, p_control)]
            cs_val = 0.5 * q_t * (p_d_axis - p_control + p_d_qt - p_control)
            ps_val = 0.5 * q_t * (p_control - p_s_axis)
            dwl_val = 0.5 * (q_eq - q_t) * (p_d_qt - p_control)

        else:  # floor
            q_t = float(np.clip(d_intercept + d_slope * p_control, Q_MIN, Q_MAX))
            p_s_qt = inv_s(q_t)
            # CS triangle
            cs_poly = [(0, p_d_axis), (q_t, p_control), (0, p_control)]
            # PS trapezoid
            ps_poly = [(0, p_s_axis), (q_t, p_s_qt), (q_t, p_control), (0, p_control)]
            # DWL triangle
            dwl_poly = [(q_t, p_control), (q_eq, p_eq), (q_t, p_s_qt)]
            cs_val = 0.5 * q_t * (p_d_axis - p_control)
            ps_val = 0.5 * q_t * (2 * p_control - p_s_axis - p_s_qt)
            dwl_val = 0.5 * (q_eq - q_t) * (p_control - p_s_qt)

        # ── Draw welfare polygons ─────────────────────────────────────────────
        from matplotlib.patches import Polygon as MplPolygon
        ax.add_patch(MplPolygon(
            cs_poly, closed=True,
            facecolor=COLOR_DEMAND, alpha=0.25,
            edgecolor=COLOR_DEMAND, hatch="///", lw=0.5, zorder=3,
        ))
        ax.add_patch(MplPolygon(
            ps_poly, closed=True,
            facecolor=COLOR_SUPPLY, alpha=0.25,
            edgecolor=COLOR_SUPPLY, hatch="\\\\\\", lw=0.5, zorder=3,
        ))
        if effective_type is not None and dwl_val > 0.1:
            ax.add_patch(MplPolygon(
                dwl_poly, closed=True,
                facecolor="#7F8C8D", alpha=0.55,
                edgecolor="#2C3E50", hatch="xxx", lw=0.5, zorder=4,
            ))

        # ── Price control line ────────────────────────────────────────────────
        if effective_type == "ceiling":
            ax.axhline(p_control, color="#C0392B", lw=2, linestyle="--", zorder=6)
            ax.text(q_eq * 0.02, p_control + 0.6,
                    f"Giá trần  Pc = {p_control:.1f}",
                    color="#C0392B", fontsize=10, fontweight="bold", zorder=7)
        elif effective_type == "floor":
            ax.axhline(p_control, color="#27AE60", lw=2, linestyle="--", zorder=6)
            ax.text(q_eq * 0.02, p_control + 0.6,
                    f"Giá sàn  Pf = {p_control:.1f}",
                    color="#27AE60", fontsize=10, fontweight="bold", zorder=7)

        # Equilibrium point + reference lines
        ax.scatter([q_eq], [p_eq], color=COLOR_EQ, s=80, zorder=9,
                   edgecolors="white", lw=1.5)
        ax.axhline(p_eq, color=COLOR_EQ, linestyle="--", lw=0.8, alpha=0.5, zorder=2)
        ax.axvline(q_eq, color=COLOR_EQ, linestyle="--", lw=0.8, alpha=0.5, zorder=2)
        ax.text(
            q_eq + 2.0, p_eq,
            f"P* = {p_eq:.1f}",
            color=COLOR_EQ, fontsize=10, fontweight="bold",
            va="center", ha="left", zorder=10,
        )

        # ── Legend: labels only, no numbers (numbers are in summary bar) ────
        cs_patch = mpatches.Patch(
            facecolor=COLOR_DEMAND, alpha=0.4,
            label="Thặng dư tiêu dùng (CS)"
        )
        ps_patch = mpatches.Patch(
            facecolor=COLOR_SUPPLY, alpha=0.4,
            label="Thặng dư sản xuất (PS)"
        )
        handles = [cs_patch, ps_patch]
        if effective_type is not None and dwl_val > 0.1:
            handles.append(mpatches.Patch(
                facecolor="#7F8C8D", alpha=0.6,
                label="Tổn thất xã hội (DWL)"
            ))
        ax.legend(handles=handles, loc="upper right", fontsize=9, framealpha=0.95)

        self._canvas.draw()

        return {
            "CS": cs_val, "PS": ps_val, "DWL": dwl_val,
            "Total_SW": cs_val + ps_val,
            "Total_SW_eq": total_sw_eq,
        }


class _WelfareDialog(QDialog):
    """Interactive welfare analysis dialog."""

    def __init__(
        self,
        s_intercept: float, s_slope: float,
        d_intercept: float, d_slope: float,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._s_intercept = s_intercept
        self._s_slope = s_slope
        self._d_intercept = d_intercept
        self._d_slope = d_slope

        self.setWindowTitle("Thặng dư & Tổn thất xã hội")
        self.setMinimumSize(860, 600)
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── Mode selector ──────────────────────────────────────────────────
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Chế độ giá:"))
        self._mode_combo = QComboBox()
        self._mode_combo.addItems([
            "Không kiểm soát (Thị trường tự do)",
            "Áp giá trần — Price Ceiling  (P < P*)",
            "Áp giá sàn  — Price Floor    (P > P*)",
        ])
        self._mode_combo.setStyleSheet("font-size: 12px; padding: 4px;")
        mode_row.addWidget(self._mode_combo)
        mode_row.addStretch()
        layout.addLayout(mode_row)

        # ── Price control slider (hidden until mode != 0) ──────────────────
        self._ctrl_widget = QWidget()
        ctrl_row = QHBoxLayout(self._ctrl_widget)
        ctrl_row.setContentsMargins(0, 0, 0, 0)
        ctrl_row.addWidget(QLabel("Mức giá kiểm soát:"))
        self._ctrl_slider = QSlider(Qt.Orientation.Horizontal)
        self._ctrl_slider.setMinimum(int(P_MIN * 10))
        self._ctrl_slider.setMaximum(int(P_MAX * 10))
        self._ctrl_slider.setValue(100)
        ctrl_row.addWidget(self._ctrl_slider, stretch=1)
        self._ctrl_val_label = QLabel("P = 10.0")
        self._ctrl_val_label.setMinimumWidth(80)
        ctrl_row.addWidget(self._ctrl_val_label)
        self._ctrl_widget.setVisible(False)
        layout.addWidget(self._ctrl_widget)

        # ── Welfare canvas ─────────────────────────────────────────────────
        self._canvas = _WelfareCanvas()
        layout.addWidget(self._canvas, stretch=1)

        # ── Numeric summary ────────────────────────────────────────────────
        self._summary = QLabel("")
        self._summary.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._summary.setWordWrap(True)
        self._summary.setStyleSheet(
            "background: #F0ECF6; border: 1px solid #8E44AD; border-radius: 6px;"
            "padding: 7px 12px; font-size: 12px; color: #2C3E50;"
        )
        layout.addWidget(self._summary)

        # ── Close button ───────────────────────────────────────────────────
        close_btn = QPushButton("Đóng")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        # ── Signals ────────────────────────────────────────────────────────
        self._mode_combo.currentIndexChanged.connect(self._on_mode_changed)
        self._ctrl_slider.valueChanged.connect(self._on_slider_changed)

        self._refresh()

    def _on_mode_changed(self, idx: int) -> None:
        self._ctrl_widget.setVisible(idx > 0)
        p_eq, _ = _equilibrium(
            self._s_intercept, self._s_slope,
            self._d_intercept, self._d_slope,
        )
        P_CTRL_MIN = 32   # 3.2
        P_CTRL_MAX = 350  # 35.0
        if idx == 1:  # ceiling — range 3.2 .. (P* - 0.1)
            hi = max(P_CTRL_MIN + 1, int(p_eq * 10) - 1)
            self._ctrl_slider.setMinimum(P_CTRL_MIN)
            self._ctrl_slider.setMaximum(hi)
            self._ctrl_slider.setValue(max(P_CTRL_MIN, int(p_eq * 0.6 * 10)))
        elif idx == 2:  # floor — range (P* + 0.1) .. 35.0
            lo = min(P_CTRL_MAX - 1, int(p_eq * 10) + 1)
            self._ctrl_slider.setMinimum(lo)
            self._ctrl_slider.setMaximum(P_CTRL_MAX)
            self._ctrl_slider.setValue(min(P_CTRL_MAX, int(p_eq * 1.4 * 10)))
        self._refresh()

    def _on_slider_changed(self, val: int) -> None:
        self._ctrl_val_label.setText(f"P = {val / 10:.1f}")
        self._refresh()

    def _refresh(self) -> None:
        idx = self._mode_combo.currentIndex()
        p_ctrl = self._ctrl_slider.value() / 10.0

        if idx == 0:
            result = self._canvas.render(
                self._s_intercept, self._s_slope,
                self._d_intercept, self._d_slope,
            )
        elif idx == 1:
            result = self._canvas.render(
                self._s_intercept, self._s_slope,
                self._d_intercept, self._d_slope,
                p_ctrl, "ceiling",
            )
        else:
            result = self._canvas.render(
                self._s_intercept, self._s_slope,
                self._d_intercept, self._d_slope,
                p_ctrl, "floor",
            )

        if result:
            cs = result["CS"]
            ps = result["PS"]
            dwl = result["DWL"]
            total = result["Total_SW"]
            total_eq = result["Total_SW_eq"]
            loss = total_eq - total
            parts = [
                f"CS = {cs:.1f}",
                f"PS = {ps:.1f}",
                f"Phúc lợi xã hội = {total:.1f}",
            ]
            if dwl > 0.1:
                parts.append(f"Tổn thất xã hội DWL = {dwl:.1f}")
                parts.append(f"Giảm so với cân bằng = {loss:.1f}")
            self._summary.setText("   |   ".join(parts))


# ─────────────────────────────────────────────────────────────────────────────
# TAB 1: Full Supply-Demand Model
# ─────────────────────────────────────────────────────────────────────────────

class _Tab1Widget(QWidget):
    """Main supply-demand model tab."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        # State
        self._s_shift = 0.0
        self._d_shift = 0.0
        self._factor_sliders: list[_FactorSlider] = []
        self._selected_factors: list[dict | None] = [None, None, None]
        self._factor_checkboxes: list[QCheckBox] = []

        self._build_ui()
        self._connect_signals()
        self._refresh()
        # Deferred re-render so slider margins are computed at actual widget size
        QTimer.singleShot(0, self._refresh)

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(6)

        # ── Top: assumptions button (above the main row) ─────────────────────
        top_row = QHBoxLayout()
        top_row.addStretch()
        self._assumptions_btn = QPushButton("📋 Giả định mô hình")
        self._assumptions_btn.setProperty("role", "secondary")
        top_row.addWidget(self._assumptions_btn)

        self._welfare_btn = QPushButton("📊 Thặng dư/Tổn thất xã hội")
        self._welfare_btn.setProperty("role", "secondary")
        top_row.addWidget(self._welfare_btn)
        outer_layout.addLayout(top_row)

        # ── Equation display row (HTML rich-text, colored by curve) ───────────
        self._equation_label = QLabel("")
        self._equation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._equation_label.setTextFormat(Qt.TextFormat.RichText)
        self._equation_label.setProperty("moduleShell", "infoPanel")
        outer_layout.addWidget(self._equation_label)

        # ── Main row: slider | canvas | right (all same height in HBox) ──────
        main_layout = QHBoxLayout()
        main_layout.setSpacing(8)

        # Left: price slider — height == canvas height (same HBox row)
        self._price_slider = _VerticalPriceSlider()
        self._price_slider.setFixedWidth(80)
        main_layout.addWidget(self._price_slider)

        # Center: canvas directly in HBox → height == slider height
        self._canvas = _SDCanvas()
        main_layout.addWidget(self._canvas, stretch=1)

        # ── Right panel ──────────────────────────────────────────────────────
        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)

        # Factor selection group
        factor_group = QGroupBox("Yếu tố ảnh hưởng")
        factor_group.setProperty("moduleShell", "panel")
        factor_vbox = QVBoxLayout(factor_group)
        factor_vbox.setSpacing(2)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(240)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        inner = QWidget()
        inner_layout = QVBoxLayout(inner)
        inner_layout.setSpacing(2)

        # Build checkboxes for all factors
        for i, factor in enumerate(ALL_FACTORS):
            row = QHBoxLayout()
            cb = QCheckBox(factor["label"])
            cb.setStyleSheet("font-size: 9px;")
            # Color by type
            if factor["direction"] == "supply":
                cb.setStyleSheet(f"font-size: 11px; color: {COLOR_SUPPLY};")
            else:
                cb.setStyleSheet(f"font-size: 11px; color: {COLOR_DEMAND};")
            self._factor_checkboxes.append(cb)
            row.addWidget(cb)

            # Placeholder for shape indicator
            shape_lbl = QLabel("")
            shape_lbl.setFixedWidth(20)
            shape_lbl.setObjectName(f"shape_{i}")
            row.addWidget(shape_lbl)
            inner_layout.addLayout(row)

        inner.setLayout(inner_layout)
        scroll.setWidget(inner)
        factor_vbox.addWidget(scroll)
        right_panel.addWidget(factor_group)

        # Factor sliders group
        sliders_group = QGroupBox("Thanh trượt yếu tố")
        sliders_group.setProperty("moduleShell", "panel")
        sliders_vbox = QVBoxLayout(sliders_group)
        sliders_vbox.setSpacing(6)

        for i in range(3):
            fs = _FactorSlider(
                {"id": "", "label": "(chưa chọn)", "direction": "supply",
                 "shift_sign": 1, "tooltip_up": "", "tooltip_down": ""},
                HANDLE_SHAPES[i],
            )
            self._factor_sliders.append(fs)
            sliders_vbox.addWidget(fs)

        right_panel.addWidget(sliders_group)

        # Reset button
        self._reset_btn = QPushButton("↺ Thiết lập lại")
        self._reset_btn.setProperty("role", "danger")
        right_panel.addWidget(self._reset_btn)
        right_panel.addStretch()

        right_widget = QWidget()
        right_widget.setFixedWidth(240)
        right_widget.setLayout(right_panel)
        main_layout.addWidget(right_widget)

        outer_layout.addLayout(main_layout, stretch=1)

        # ── Info box below the main row (full width) ────────────────────────
        self._info_box = QLabel("")
        self._info_box.setProperty("moduleShell", "infoPanel")
        self._info_box.setAlignment(Qt.AlignmentFlag.AlignCenter)
        outer_layout.addWidget(self._info_box)

    def _connect_signals(self) -> None:
        self._price_slider.slider.valueChanged.connect(self._refresh)
        self._assumptions_btn.clicked.connect(self._show_assumptions)
        self._welfare_btn.clicked.connect(self._show_welfare)
        self._reset_btn.clicked.connect(self._reset)

        for cb in self._factor_checkboxes:
            cb.stateChanged.connect(self._on_factor_toggle)

        for fs in self._factor_sliders:
            fs.slider.valueChanged.connect(self._on_factor_slider_changed)

    def _on_factor_toggle(self) -> None:
        """Assign checked factors to the three sliders in order."""
        checked_factors = [
            ALL_FACTORS[i]
            for i, cb in enumerate(self._factor_checkboxes)
            if cb.isChecked()
        ]
        # Limit to 3
        checked_factors = checked_factors[:3]

        # Update slider assignments
        for i, fs in enumerate(self._factor_sliders):
            if i < len(checked_factors):
                fs.activate(checked_factors[i])
            else:
                fs.deactivate()

        # Update shape labels next to checkboxes
        # First clear all
        for cb in self._factor_checkboxes:
            parent_layout = cb.parent().layout() if cb.parent() else None
        # Rebuild shape labels by scanning inner widget
        assigned_ids = [
            self._factor_sliders[i].factor["id"]
            for i in range(len(checked_factors))
        ]
        inner_widget = self._factor_checkboxes[0].parent() if self._factor_checkboxes else None
        if inner_widget:
            for i, factor in enumerate(ALL_FACTORS):
                shape_lbl = inner_widget.findChild(QLabel, f"shape_{i}")
                if shape_lbl:
                    if factor["id"] in assigned_ids:
                        idx = assigned_ids.index(factor["id"])
                        shape_lbl.setText(HANDLE_SHAPES[idx])
                        shape_lbl.setStyleSheet(
                            f"font-size: 14px; color:"
                            f"{'#E07B39' if factor['direction']=='supply' else '#2E8B57'};"
                            f" font-weight: bold;"
                        )
                    else:
                        shape_lbl.setText("")

        self._refresh()

    def _on_factor_slider_changed(self) -> None:
        self._refresh()

    def _compute_shifts(self) -> tuple[float, float]:
        s_shift = 0.0
        d_shift = 0.0
        for fs in self._factor_sliders:
            if fs.is_active:
                if fs.factor["direction"] == "supply":
                    s_shift += fs.shift_value
                else:
                    d_shift += fs.shift_value
        return s_shift, d_shift

    @staticmethod
    def _fmt_eq(intercept: float, slope: float, q_sym: str) -> str:
        """Format 'Qs = a + bP' or 'Qd = a - bP' for display."""
        slope_abs = abs(slope)
        slope_sign = "+" if slope >= 0 else "\u2212"  # − character
        slope_int = int(slope_abs) if slope_abs == int(slope_abs) else slope_abs
        if intercept == int(intercept):
            a_str = str(int(intercept))
        else:
            a_str = f"{intercept:.1f}"
        return f"{q_sym} = {a_str} {slope_sign} {slope_int}P"

    def _refresh(self) -> None:
        s_shift, d_shift = self._compute_shifts()
        s_intercept = BASE_S_INTERCEPT + s_shift
        d_intercept = BASE_D_INTERCEPT + d_shift
        current_price = self._price_slider.price

        # Update equation labels (colored HTML)
        s_eq = self._fmt_eq(s_intercept, BASE_S_SLOPE, "Qs")
        d_eq = self._fmt_eq(d_intercept, BASE_D_SLOPE, "Qd")
        self._equation_label.setText(
            f'<span style="color:{COLOR_SUPPLY}; font-size:17px; font-weight:bold;">'
            f'{s_eq}</span>'
            f'&nbsp;&nbsp;&nbsp;<span style="color:#95A5A6; font-size:16px;">\u2502</span>&nbsp;&nbsp;&nbsp;'
            f'<span style="color:{COLOR_DEMAND}; font-size:17px; font-weight:bold;">'
            f'{d_eq}</span>'
        )

        result = self._canvas.render(
            s_intercept, BASE_S_SLOPE,
            d_intercept, BASE_D_SLOPE,
            current_price,
        )

        if result:
            if "ax_top_frac" in result:
                self._price_slider.set_axis_fracs(
                    result["ax_top_frac"], result["ax_bottom_frac"]
                )
            p_eq = result["p_eq"]
            q_eq = result["q_eq"]
            qs = result["qs_current"]
            qd = result["qd_current"]
            TOLERANCE = 0.05
            if abs(current_price - p_eq) < TOLERANCE:
                status = "✅ Thị trường CÂN BẰNG"
                color = COLOR_EQ
            elif current_price > p_eq:
                status = f"📈 DƯ THỪA: Qs ({qs:.1f}) > Qd ({qd:.1f})"
                color = COLOR_SURPLUS
            else:
                status = f"📉 THIẾU HỤT: Qd ({qd:.1f}) > Qs ({qs:.1f})"
                color = COLOR_SHORTAGE

            self._info_box.setText(
                f"P* = {p_eq:.1f}   Q* = {q_eq:.1f}   |   "
                f"P hiện tại = {current_price:.1f}   Qs = {qs:.1f}   Qd = {qd:.1f}   |   "
                f"<span style='color:{color}; font-weight:700;'>{status}</span>"
            )

    def _show_assumptions(self) -> None:
        dlg = _AssumptionsDialog(self)
        dlg.exec()

    def _show_welfare(self) -> None:
        s_shift, d_shift = self._compute_shifts()
        dlg = _WelfareDialog(
            BASE_S_INTERCEPT + s_shift, BASE_S_SLOPE,
            BASE_D_INTERCEPT + d_shift, BASE_D_SLOPE,
            parent=self,
        )
        dlg.exec()

    def _reset(self) -> None:
        self._price_slider.slider.setValue(160)
        for cb in self._factor_checkboxes:
            cb.setChecked(False)
        for fs in self._factor_sliders:
            fs.deactivate()
        self._refresh()

    def get_state(self) -> dict:
        return {
            "price": self._price_slider.price,
            "checked_factors": [
                ALL_FACTORS[i]["id"]
                for i, cb in enumerate(self._factor_checkboxes)
                if cb.isChecked()
            ],
            "slider_values": [fs.slider.value() for fs in self._factor_sliders],
        }

    def restore_state(self, state: dict) -> None:
        if "price" in state:
            self._price_slider.slider.setValue(int(state["price"] * 10))
        if "checked_factors" in state:
            checked_ids = state["checked_factors"]
            for i, cb in enumerate(self._factor_checkboxes):
                cb.setChecked(ALL_FACTORS[i]["id"] in checked_ids)
        if "slider_values" in state:
            for i, fs in enumerate(self._factor_sliders):
                if i < len(state["slider_values"]):
                    fs.slider.setValue(state["slider_values"][i])


# ─────────────────────────────────────────────────────────────────────────────
# TAB 2 & 3: Single curve deep-dive
# ─────────────────────────────────────────────────────────────────────────────

class _SingleCurveTab(QWidget):
    """Reusable tab for Supply or Demand deep-dive."""

    def __init__(self, curve_type: str = "supply", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._curve_type = curve_type
        self._factors = SUPPLY_FACTORS if curve_type == "supply" else DEMAND_FACTORS
        self._base_intercept = BASE_S_INTERCEPT if curve_type == "supply" else BASE_D_INTERCEPT
        self._base_slope = BASE_S_SLOPE if curve_type == "supply" else BASE_D_SLOPE
        self._factor_sliders: list[_FactorSlider] = []
        self._last_interacted: str = "price"

        self._build_ui()
        self._connect_signals()
        self._refresh("price")
        # Deferred re-render so slider margins are computed at actual widget size
        QTimer.singleShot(0, lambda: self._refresh("price"))

    def _build_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)
        outer_layout.setSpacing(6)

        # ── Equation display row ──────────────────────────────────────────────
        self._equation_label = QLabel("")
        self._equation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._equation_label.setProperty("moduleShell", "equationPanel")
        outer_layout.addWidget(self._equation_label)

        # ── Main row: slider | canvas | right (all same height in HBox) ──────
        main_layout = QHBoxLayout()
        main_layout.setSpacing(8)

        # Left: price slider — height == canvas height (same HBox row)
        self._price_slider = _VerticalPriceSlider("P (Giá)")
        self._price_slider.setFixedWidth(75)
        main_layout.addWidget(self._price_slider)

        # Center: canvas directly in HBox → height == slider height
        self._canvas = _SingleCurveCanvas(self._curve_type)
        main_layout.addWidget(self._canvas, stretch=1)

        # ── Right: factor sliders ────────────────────────────────────────────
        right_widget = QWidget()
        right_widget.setFixedWidth(220)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setSpacing(6)

        title = QLabel("Yếu tố dịch chuyển đường")
        title.setProperty("moduleShell", "curveTitle")
        title.setProperty("curve", self._curve_type)
        right_layout.addWidget(title)

        # Scroll area so 6–7 factor sliders don't overflow the panel
        sliders_scroll = QScrollArea()
        sliders_scroll.setWidgetResizable(True)
        sliders_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        sliders_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sliders_inner = QWidget()
        sliders_inner_layout = QVBoxLayout(sliders_inner)
        sliders_inner_layout.setSpacing(6)
        sliders_inner_layout.setContentsMargins(0, 0, 4, 0)

        for factor in self._factors:
            fs = _FactorSlider(factor, "■")
            fs.activate(factor)
            self._factor_sliders.append(fs)
            sliders_inner_layout.addWidget(fs)

        sliders_inner_layout.addStretch()
        sliders_scroll.setWidget(sliders_inner)
        right_layout.addWidget(sliders_scroll, stretch=1)

        # Reset button
        reset_btn = QPushButton("↺ Thiết lập lại")
        reset_btn.setProperty("role", "secondary")
        reset_btn.clicked.connect(self._reset)
        right_layout.addWidget(reset_btn)

        main_layout.addWidget(right_widget)

        outer_layout.addLayout(main_layout, stretch=1)

        # ── Tooltip box below the main row (full width) ─────────────────────
        self._tooltip_box = QLabel("")
        self._tooltip_box.setWordWrap(True)
        self._tooltip_box.setProperty("moduleShell", "tooltipPanel")
        self._tooltip_box.setMinimumHeight(50)
        self._tooltip_box.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        outer_layout.addWidget(self._tooltip_box)

    def _connect_signals(self) -> None:
        self._price_slider.slider.valueChanged.connect(
            lambda: self._refresh("price")
        )
        for i, fs in enumerate(self._factor_sliders):
            factor = self._factors[i]
            fs.slider.valueChanged.connect(
                lambda _val, f=factor: self._refresh(f["id"])
            )

    def _get_current_intercept(self) -> float:
        total_shift = sum(fs.shift_value for fs in self._factor_sliders)
        return self._base_intercept + total_shift

    def _refresh(self, source: str = "price") -> None:
        self._last_interacted = source
        intercept = self._get_current_intercept()
        current_price = self._price_slider.price

        # Update equation label (colored HTML)
        if self._curve_type == "supply":
            slope_sign = "+"
            slope_val = int(abs(BASE_S_SLOPE))
            q_sym = "Qs"
            eq_color = COLOR_SUPPLY
        else:
            slope_sign = "\u2212"
            slope_val = int(abs(BASE_D_SLOPE))
            q_sym = "Qd"
            eq_color = COLOR_DEMAND
        a_str = str(int(intercept)) if intercept == int(intercept) else f"{intercept:.1f}"
        eq_text = f"{q_sym} = {a_str} {slope_sign} {slope_val}P"
        self._equation_label.setText(
            f'<span style="color:{eq_color}; font-size:17px; font-weight:bold;">{eq_text}</span>'
        )

        result = self._canvas.render(intercept, self._base_slope, current_price)
        if result:
            self._price_slider.set_axis_fracs(
                result["ax_top_frac"], result["ax_bottom_frac"]
            )
        self._update_tooltip(source)

    def _update_tooltip(self, source: str) -> None:
        if source == "price":
            if self._curve_type == "supply":
                self._tooltip_box.setText(LAW_SUPPLY_PRICE)
            else:
                self._tooltip_box.setText(LAW_DEMAND_PRICE)
            return

        # Find matching factor
        for factor in self._factors:
            if factor["id"] == source:
                # Determine slider value to pick appropriate text
                slider_val = 0
                for fs in self._factor_sliders:
                    if fs.is_active and fs.factor["id"] == source:
                        slider_val = fs.slider.value()
                        break
                if factor["shift_sign"] * slider_val >= 0:
                    text = factor["tooltip_up"]
                else:
                    text = factor["tooltip_down"]
                self._tooltip_box.setText(text)
                return

    def _reset(self) -> None:
        self._price_slider.slider.setValue(160)
        for fs in self._factor_sliders:
            fs.slider.setValue(0)
        self._refresh("price")

    def get_state(self) -> dict:
        return {
            "price": self._price_slider.price,
            "factor_values": {
                fs.factor["id"]: fs.slider.value()
                for fs in self._factor_sliders
            },
        }

    def restore_state(self, state: dict) -> None:
        if "price" in state:
            self._price_slider.slider.setValue(int(state["price"] * 10))
        if "factor_values" in state:
            for fs in self._factor_sliders:
                fid = fs.factor["id"]
                if fid in state["factor_values"]:
                    fs.slider.setValue(state["factor_values"][fid])


# ─────────────────────────────────────────────────────────────────────────────
# Main module widget
# ─────────────────────────────────────────────────────────────────────────────

_ModuleWidgetBase = QWidget if _QT else object  # type: ignore[misc]


class _SupplyDemandWidget(_ModuleWidgetBase):  # type: ignore[valid-type]
    """Root QWidget returned by build_view()."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("moduleShell", "root")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setDocumentMode(True)

        self._tab1 = _Tab1Widget()
        self._tab2 = _SingleCurveTab("supply")
        self._tab3 = _SingleCurveTab("demand")

        self._tabs.addTab(self._tab1, "📊 Mô hình Cung - Cầu")
        self._tabs.addTab(self._tab2, "📈 Đường Cung")
        self._tabs.addTab(self._tab3, "📉 Đường Cầu")

        layout.addWidget(self._tabs)

    def get_state(self) -> dict:
        return {
            "active_tab": self._tabs.currentIndex(),
            "tab1": self._tab1.get_state(),
            "tab2": self._tab2.get_state(),
            "tab3": self._tab3.get_state(),
        }

    def restore_state(self, state: dict) -> None:
        if "active_tab" in state:
            self._tabs.setCurrentIndex(state["active_tab"])
        if "tab1" in state:
            self._tab1.restore_state(state["tab1"])
        if "tab2" in state:
            self._tab2.restore_state(state["tab2"])
        if "tab3" in state:
            self._tab3.restore_state(state["tab3"])


# ─────────────────────────────────────────────────────────────────────────────
# Module class — IIMP SDK contract
# ─────────────────────────────────────────────────────────────────────────────


class SupplyDemandModule(BaseModule):
    """IIMP module: interactive supply-demand simulation for education."""

    def __init__(self, manifest: dict, context: Any) -> None:
        super().__init__(manifest, context)
        self._widget: _SupplyDemandWidget | None = None

    # ── Mandatory lifecycle ───────────────────────────────────────────────────

    def on_load(self) -> None:
        pass

    def build_view(self) -> QWidget:
        if self._widget is None:
            self._widget = _SupplyDemandWidget()
        return self._widget

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    def on_unload(self) -> None:
        self._widget = None

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict:
        if self._widget is None:
            return {}
        state = self._widget.get_state()
        state["_state_version"] = "1.0.0"
        return state

    def restore_state(self, state: dict) -> None:
        if self._widget is None:
            return
        self._widget.restore_state(state)
