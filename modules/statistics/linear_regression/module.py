"""Phân tích Hồi quy Tuyến tính Đơn — v1.0.0

Mô phỏng tương tác cho phân tích hồi quy tuyến tính đơn giản:
  - Nhập dữ liệu quan sát (X, Y) tối đa 10 điểm
  - Biểu đồ phân tán với đường xu hướng tương tác
  - Tịnh tiến (kéo thân đường) và xoay (kéo đầu mút)
  - Hiển thị sai số e_i, tổng bình phương sai số
  - Giải OLS tìm hệ số ước lượng b₀, b₁
  - Dự báo tương tác với khoảng tin cậy động

Phương trình hồi quy ước lượng: Ŷ = b₀ + b₁·X
  b₁ = [nΣXY − ΣXΣY] / [nΣX² − (ΣX)²]
  b₀ = Ȳ − b₁·X̄
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np

try:
    from scipy import stats as _scipy_stats
    _SCIPY = True
except ImportError:  # pragma: no cover
    _SCIPY = False

try:
    from PySide6.QtCore import Qt, Signal
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QDialog,
        QDialogButtonBox,
        QDoubleSpinBox,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QHeaderView,
        QLabel,
        QMessageBox,
        QPushButton,
        QScrollArea,
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

_CanvasBase = QWidget if _QT else object  # type: ignore[misc]


# ═══════════════════════════════════════════════════════════════════════════════
# Data Input Dialog
# ═══════════════════════════════════════════════════════════════════════════════


class _DataInputDialog(QDialog):
    """Dialog to enter/edit X, Y observation pairs."""

    def __init__(self, x_data: list[float], y_data: list[float],
                 parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nhập dữ liệu quan sát")
        self.setMinimumSize(360, 420)
        self._x_result: list[float] = []
        self._y_result: list[float] = []
        self._build_ui(x_data, y_data)

    def _build_ui(self, x_data: list[float], y_data: list[float]) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        hint = QLabel("Nhập dữ liệu quan sát (tối đa 30 điểm):")
        layout.addWidget(hint)

        # Row count selector
        row_hl = QHBoxLayout()
        row_hl.addWidget(QLabel("Số quan sát:"))
        self._row_spin = QSpinBox()
        self._row_spin.setRange(2, 30)
        self._row_spin.setValue(max(2, len(x_data)))
        self._row_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._row_spin.valueChanged.connect(self._resize_table)
        row_hl.addWidget(self._row_spin)
        row_hl.addStretch()
        layout.addLayout(row_hl)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["X", "Y"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._table, stretch=1)

        # Pre-fill
        n = max(2, len(x_data))
        self._row_spin.setValue(n)
        self._table.setRowCount(n)
        for i in range(n):
            xv = str(x_data[i]) if i < len(x_data) else ""
            yv = str(y_data[i]) if i < len(y_data) else ""
            self._table.setItem(i, 0, QTableWidgetItem(xv))
            self._table.setItem(i, 1, QTableWidgetItem(yv))

        # Buttons
        btn_layout = QHBoxLayout()
        self._btn_ok = QPushButton("Hoàn tất")
        self._btn_ok.clicked.connect(self._accept_data)
        self._btn_reset = QPushButton("Nhập lại")
        self._btn_reset.setStyleSheet(
            "background-color: transparent; color: #E74C3C;"
            " border: 1px solid #E74C3C;"
        )
        self._btn_reset.clicked.connect(self._reset_table)
        btn_layout.addWidget(self._btn_ok)
        btn_layout.addWidget(self._btn_reset)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

    def _resize_table(self, n: int) -> None:
        old = self._table.rowCount()
        self._table.setRowCount(n)
        for i in range(old, n):
            self._table.setItem(i, 0, QTableWidgetItem(""))
            self._table.setItem(i, 1, QTableWidgetItem(""))

    def _reset_table(self) -> None:
        n = self._table.rowCount()
        for i in range(n):
            self._table.setItem(i, 0, QTableWidgetItem(""))
            self._table.setItem(i, 1, QTableWidgetItem(""))

    def _accept_data(self) -> None:
        xs, ys = [], []
        for i in range(self._table.rowCount()):
            xi = self._table.item(i, 0)
            yi = self._table.item(i, 1)
            try:
                xv = float(xi.text().strip()) if xi and xi.text().strip() else None
                yv = float(yi.text().strip()) if yi and yi.text().strip() else None
            except ValueError:
                QMessageBox.warning(self, "Lỗi", f"Hàng {i+1}: giá trị không hợp lệ.")
                return
            if xv is not None and yv is not None:
                xs.append(xv)
                ys.append(yv)
        if len(xs) < 2:
            QMessageBox.warning(self, "Lỗi", "Cần ít nhất 2 quan sát hợp lệ.")
            return
        self._x_result = xs
        self._y_result = ys
        self.accept()

    def get_data(self) -> tuple[list[float], list[float]]:
        return self._x_result, self._y_result


# ═══════════════════════════════════════════════════════════════════════════════
# Solve Dialog
# ═══════════════════════════════════════════════════════════════════════════════


class _SolveDialog(QDialog):
    """Shows OLS formulas and computed coefficients."""

    def __init__(self, x: np.ndarray, y: np.ndarray,
                 parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Giải hệ số hồi quy OLS")
        self.setMinimumSize(520, 420)
        self._b0: float = 0.0
        self._b1: float = 0.0
        self._build_ui(x, y)

    def _build_ui(self, x: np.ndarray, y: np.ndarray) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        n = len(x)
        sx = np.sum(x)
        sy = np.sum(y)
        sxy = np.sum(x * y)
        sx2 = np.sum(x ** 2)
        x_bar = np.mean(x)
        y_bar = np.mean(y)

        denom = n * sx2 - sx ** 2
        if abs(denom) < 1e-12:
            self._b1 = 0.0
        else:
            self._b1 = float((n * sxy - sx * sy) / denom)
        self._b0 = float(y_bar - self._b1 * x_bar)

        bold = QFont()
        bold.setBold(True)

        title = QLabel("Phương pháp Bình phương Nhỏ nhất Thông thường (OLS)")
        title.setFont(bold)
        title.setStyleSheet("font-size: 18px; color: #2C3E50;")
        layout.addWidget(title)

        eq_lbl = QLabel(
            "<div style='font-size:16px; margin:2px 0 6px 0;'>"
            "<b>Phương trình hồi quy ước lượng:</b> Ŷ = b<sub>0</sub> + b<sub>1</sub>·X"
            "</div>"
        )
        eq_lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(eq_lbl)

        coeff_title = QLabel("<b style='font-size:16px;'>Công thức tính hệ số:</b>")
        coeff_title.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(coeff_title)

        # b1 fraction — centered
        b1_lbl = QLabel(
            "<table cellpadding='0' cellspacing='0' style='font-size:16px; margin:0;'>"
            "<tr>"
            "<td style='vertical-align:middle; padding-right:4px;'>b<sub>1</sub> =</td>"
            "<td align='center'>"
            "<table cellpadding='0' cellspacing='0'>"
            "<tr><td align='center' style='border-bottom:1px solid #333; padding:1px 6px;'>"
            "n·ΣX<sub>i</sub>Y<sub>i</sub> − ΣX<sub>i</sub>·ΣY<sub>i</sub></td></tr>"
            "<tr><td align='center' style='padding:1px 6px;'>"
            "n·ΣX<sub>i</sub>² − (ΣX<sub>i</sub>)²</td></tr>"
            "</table></td></tr></table>"
        )
        b1_lbl.setTextFormat(Qt.TextFormat.RichText)
        b1_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(b1_lbl)

        # b0 fraction — centered
        b0_lbl = QLabel(
            "<table cellpadding='0' cellspacing='0' style='font-size:16px; margin:0;'>"
            "<tr>"
            "<td style='vertical-align:middle; padding-right:4px;'>b<sub>0</sub> =</td>"
            "<td align='center'>"
            "<table cellpadding='0' cellspacing='0'>"
            "<tr><td align='center' style='border-bottom:1px solid #333; padding:1px 6px;'>"
            "ΣY<sub>i</sub></td></tr>"
            "<tr><td align='center' style='padding:1px 6px;'>n</td></tr>"
            "</table></td>"
            "<td style='vertical-align:middle; padding:0 4px;'> − b<sub>1</sub>·</td>"
            "<td align='center'>"
            "<table cellpadding='0' cellspacing='0'>"
            "<tr><td align='center' style='border-bottom:1px solid #333; padding:1px 6px;'>"
            "ΣX<sub>i</sub></td></tr>"
            "<tr><td align='center' style='padding:1px 6px;'>n</td></tr>"
            "</table></td></tr></table>"
        )
        b0_lbl.setTextFormat(Qt.TextFormat.RichText)
        b0_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(b0_lbl)

        # Intermediate results
        mid_lbl = QLabel(
            "<div style='font-size:16px; line-height:1.6;'>"
            "<b>Kết quả trung gian:</b><br>"
            f"n = {n}<br>"
            f"ΣX<sub>i</sub> = {sx:.2f}<br>"
            f"ΣY<sub>i</sub> = {sy:.2f}<br>"
            f"ΣX<sub>i</sub>Y<sub>i</sub> = {sxy:.2f}<br>"
            f"ΣX<sub>i</sub>² = {sx2:.2f}<br>"
            f"X̄ = {x_bar:.2f}<br>"
            f"Ȳ = {y_bar:.2f}"
            "</div>"
        )
        mid_lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(mid_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        result = QLabel(
            f"<div style='font-size:17px; line-height:1.8;'>"
            f"<b>b<sub>1</sub> = {self._b1:.2f}</b><br>"
            f"<b>b<sub>0</sub> = {self._b0:.2f}</b><br><br>"
            f"<b style='color:#2980B9;'>Ŷ = {self._b0:.2f} + {self._b1:.2f}·X</b>"
            f"</div>"
        )
        result.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(result)

        layout.addStretch()

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)

    def get_coefficients(self) -> tuple[float, float]:
        return self._b0, self._b1


# ═══════════════════════════════════════════════════════════════════════════════
# R² / SS Analysis Dialog
# ═══════════════════════════════════════════════════════════════════════════════


class _R2Dialog(QDialog):
    """Shows SS decomposition illustration and R² computation."""

    def __init__(self, x: np.ndarray, y: np.ndarray,
                 b0: float, b1: float,
                 parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Phân tích R² — Hệ số xác định")
        self.setMinimumSize(960, 580)
        self._build_ui(x, y, b0, b1)

    def _build_ui(self, x: np.ndarray, y: np.ndarray,
                  b0: float, b1: float) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        n = len(x)
        y_hat = b0 + b1 * x
        y_bar = float(np.mean(y))

        # SS values
        sst = float(np.sum((y - y_bar) ** 2))
        sse = float(np.sum((y - y_hat) ** 2))
        ssr = float(np.sum((y_hat - y_bar) ** 2))
        r2 = ssr / sst if abs(sst) > 1e-12 else 0.0

        # Intermediate sums for formula substitution
        sy = float(np.sum(y))
        sy2 = float(np.sum(y ** 2))
        sxy = float(np.sum(x * y))
        sx = float(np.sum(x))

        # ── Two-panel layout ──────────────────────────────────────────────────
        content = QHBoxLayout()
        content.setSpacing(10)

        # ── LEFT: Chart illustration ──────────────────────────────────────────
        fig = Figure(figsize=(5, 4.5), dpi=100)
        ax = fig.add_subplot(111)
        canvas = FigureCanvas(fig)
        canvas.setMinimumWidth(420)

        # Scatter
        ax.scatter(x, y, c="#2C3E50", s=60, zorder=5, edgecolors="white",
                   linewidths=1.0, label="Quan sát")

        # Regression line
        x_margin = (x.max() - x.min()) * 0.12 if x.max() != x.min() else 1.0
        x_line = np.array([x.min() - x_margin, x.max() + x_margin])
        y_line = b0 + b1 * x_line
        ax.plot(x_line, y_line, color="#E74C3C", linewidth=2,
                label="Ŷ = b₀ + b₁·X", zorder=3)

        # Mean line
        ax.axhline(y_bar, color="#27AE60", linewidth=1.8, linestyle="--",
                   label=f"Ȳ = {y_bar:.2f}", zorder=2)

        # Draw SS arrows for each point
        for i in range(n):
            xi, yi, yhi = x[i], y[i], y_hat[i]
            offset = x_margin * 0.06

            # SST: Yᵢ − Ȳ (blue, leftmost)
            ax.annotate(
                "", xy=(xi - offset, yi), xytext=(xi - offset, y_bar),
                arrowprops=dict(arrowstyle="<->", color="#3498DB",
                                lw=1.3, linestyle="-"),
                zorder=4,
            )

            # SSR: Ŷᵢ − Ȳ (green, center)
            ax.annotate(
                "", xy=(xi, yhi), xytext=(xi, y_bar),
                arrowprops=dict(arrowstyle="<->", color="#27AE60",
                                lw=1.3, linestyle="-"),
                zorder=4,
            )

            # SSE: Yᵢ − Ŷᵢ (red, rightmost)
            ax.annotate(
                "", xy=(xi + offset, yi), xytext=(xi + offset, yhi),
                arrowprops=dict(arrowstyle="<->", color="#E74C3C",
                                lw=1.3, linestyle="-"),
                zorder=4,
            )

        # Legend for SS arrows (invisible scatter for legend entries)
        ax.plot([], [], color="#3498DB", linewidth=2, label="SST: Yᵢ − Ȳ")
        ax.plot([], [], color="#27AE60", linewidth=2, label="SSR: Ŷᵢ − Ȳ")
        ax.plot([], [], color="#E74C3C", linewidth=2, label="SSE: Yᵢ − Ŷᵢ")

        ax.set_xlabel("X", fontsize=11)
        ax.set_ylabel("Y", fontsize=11)
        ax.set_title("Minh họa phân tích tổng bình phương", fontsize=12,
                      fontweight="bold", pad=10)
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        content.addWidget(canvas, stretch=1)

        # ── RIGHT: Formulas + computation ─────────────────────────────────────
        right_panel = QScrollArea()
        right_panel.setWidgetResizable(True)
        right_panel.setMinimumWidth(400)
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 6, 10, 6)
        right_layout.setSpacing(4)

        # Title
        title = QLabel("<b style='font-size:16px; color:#2C3E50;'>"
                        "Tính các tổng bình phương</b>")
        title.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(title)

        identity = QLabel(
            "<div style='font-size:17px; font-weight:bold; margin:4px 0 10px 0;"
            " text-align:center;'>SST = SSR + SSE</div>"
        )
        identity.setTextFormat(Qt.TextFormat.RichText)
        identity.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        right_layout.addWidget(identity)

        # Helper: build a single visual line with inline fractions
        # Each arg is either a str (plain text) or a (numerator, denominator) tuple
        def _line(*parts: "str | tuple[str, str]") -> str:
            cells = []
            for p in parts:
                if isinstance(p, tuple):
                    num, den = p
                    cells.append(
                        "<td style='vertical-align:middle;'>"
                        "<table cellpadding='0' cellspacing='0'>"
                        f"<tr><td align='center' style='border-bottom:1px solid #333;"
                        f" padding:0 4px;'>{num}</td></tr>"
                        f"<tr><td align='center' style='padding:0 4px;'>{den}</td></tr>"
                        "</table></td>"
                    )
                else:
                    cells.append(
                        f"<td style='vertical-align:middle;"
                        f" white-space:nowrap;'>{p}</td>"
                    )
            return (
                "<table cellpadding='0' cellspacing='0'><tr>"
                + "".join(cells)
                + "</tr></table>"
            )

        fs = "font-size:14px;"

        # --- SST ---
        sst_title = QLabel("<b style='font-size:14px; color:#3498DB;'>SST "
                           "(Total Sum of Squares)</b>")
        sst_title.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(sst_title)

        sst_formula = QLabel(
            f"<div style='{fs}'>"
            + _line("SST = ΣY<sub>i</sub>² − ",
                    ("(ΣY<sub>i</sub>)²", "n"))
            + _line(f"&nbsp;&nbsp;&nbsp;&nbsp;= {sy2:.2f} − ",
                    (f"({sy:.2f})²", str(n)),
                    f"&nbsp;= {sy2:.2f} − {sy**2/n:.2f}")
            + f"<div>&nbsp;&nbsp;&nbsp;&nbsp;= <b>{sst:.2f}</b></div>"
            + "</div>"
        )
        sst_formula.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(sst_formula)

        # --- SSR ---
        ssr_title = QLabel("<b style='font-size:14px; color:#27AE60;'>SSR "
                           "(Regression Sum of Squares)</b>")
        ssr_title.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(ssr_title)

        ssr_formula = QLabel(
            f"<div style='{fs}'>"
            + _line("SSR = b<sub>1</sub>(ΣX<sub>i</sub>Y<sub>i</sub> − ",
                    ("ΣX<sub>i</sub>·ΣY<sub>i</sub>", "n"),
                    ")")
            + _line(f"&nbsp;&nbsp;&nbsp;&nbsp;= {b1:.2f} × ({sxy:.2f} − ",
                    (f"{sx:.2f}×{sy:.2f}", str(n)),
                    f") = {b1:.2f} × {sxy - sx*sy/n:.2f}")
            + f"<div>&nbsp;&nbsp;&nbsp;&nbsp;= <b>{ssr:.2f}</b></div>"
            + "</div>"
        )
        ssr_formula.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(ssr_formula)

        # --- SSE ---
        sse_title = QLabel("<b style='font-size:14px; color:#E74C3C;'>SSE "
                           "(Error Sum of Squares)</b>")
        sse_title.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(sse_title)

        sse_formula = QLabel(
            f"<div style='{fs} line-height:1.6;'>"
            "SSE = ΣY<sub>i</sub>² − b<sub>1</sub>·ΣX<sub>i</sub>Y<sub>i</sub>"
            " − b<sub>0</sub>·ΣY<sub>i</sub><br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;= {sy2:.2f} − {b1:.2f}×{sxy:.2f}"
            f" − {b0:.2f}×{sy:.2f}<br>"
            f"&nbsp;&nbsp;&nbsp;&nbsp;= <b>{sse:.2f}</b>"
            "</div>"
        )
        sse_formula.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(sse_formula)

        # Verification
        verify = QLabel(
            "<div style='font-size:13px; color:#888; margin:4px 0;'>"
            f"Kiểm tra: SSR + SSE = {ssr:.2f} + {sse:.2f} = {ssr+sse:.2f} ≈ "
            f"SST = {sst:.2f}</div>"
        )
        verify.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(verify)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        right_layout.addWidget(sep)

        # --- R² ---
        r2_title = QLabel("<b style='font-size:16px; color:#8E44AD;'>Hệ số xác định R²</b>")
        r2_title.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(r2_title)

        r2_formula = QLabel(
            f"<div style='font-size:15px;'>"
            + _line("R² = ", ("SSR", "SST"))
            + _line("&nbsp;&nbsp;&nbsp;= ",
                    (f"{ssr:.2f}", f"{sst:.2f}"))
            + f"<div>&nbsp;&nbsp;&nbsp;= "
            + f"<b style='color:#8E44AD; font-size:17px;'>{r2:.4f}</b></div>"
            + "</div>"
        )
        r2_formula.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(r2_formula)

        interpret = QLabel(
            f"<div style='font-size:13px; color:#555; margin-top:4px;'>"
            f"→ {r2*100:.2f}% biến thiên của Y được giải thích bởi mô hình hồi quy."
            f"</div>"
        )
        interpret.setTextFormat(Qt.TextFormat.RichText)
        right_layout.addWidget(interpret)

        right_layout.addStretch()
        right_panel.setWidget(right_widget)
        content.addWidget(right_panel, stretch=1)

        layout.addLayout(content)

        # Close button
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)


# ═══════════════════════════════════════════════════════════════════════════════
# Forecast Dialog
# ═══════════════════════════════════════════════════════════════════════════════


class _ForecastDialog(QDialog):
    """Interactive forecast dialog with confidence band.

    Layout (outside the chart):
    - Horizontal slider below chart → drag to change X prediction value.
    - Vertical slider on the left  → drag to change confidence level 0–100 %.

    On the chart:
    - Scatter plot + OLS regression line (red).
    - A filled circle on the regression line that tracks the current X value.
    - Two dashed lines (parallel to regression) representing the prediction
      interval width; they expand / contract as confidence changes.
    """

    def __init__(
        self,
        x: "np.ndarray",
        y: "np.ndarray",
        b0: float,
        b1: float,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Dự báo tương tác — Hồi quy tuyến tính đơn")
        self.setMinimumSize(820, 560)
        self.resize(900, 620)

        self._x = x
        self._y = y
        self._b0 = b0
        self._b1 = b1
        self._n = len(x)
        self._x_bar = float(np.mean(x))

        # Prediction stats for interval
        y_hat = b0 + b1 * x
        residuals = y - y_hat
        sse = float(np.sum(residuals ** 2))
        self._mse = sse / max(self._n - 2, 1)
        self._sxx = float(np.sum((x - self._x_bar) ** 2))
        self._s = float(np.sqrt(self._mse))  # standard error of regression

        # Current X range for slider
        x_margin = (x.max() - x.min()) * 0.20 if x.max() != x.min() else 1.0
        self._x_lo = float(x.min() - x_margin)
        self._x_hi = float(x.max() + x_margin)

        # Slider steps
        self._x_steps = 400
        self._conf_steps = 100  # 0..100 → 0%..100%

        # Initial slider positions: center X, 95% confidence
        self._curr_x = float(np.mean(x))
        self._conf_level = 95  # integer 0–100

        # Fixed axis limits — computed once so axes never rescale during interaction
        hw_lo = self._prediction_half_width(self._x_lo, 0.999)
        hw_hi = self._prediction_half_width(self._x_hi, 0.999)
        y_reg_lo = b0 + b1 * self._x_lo
        y_reg_hi = b0 + b1 * self._x_hi
        _y_cands = (
            list(y)
            + [y_reg_lo + hw_lo, y_reg_lo - hw_lo,
               y_reg_hi + hw_hi, y_reg_hi - hw_hi]
        )
        _y_lo = min(_y_cands)
        _y_hi = max(_y_cands)
        _y_pad = (_y_hi - _y_lo) * 0.12 if _y_hi != _y_lo else 1.0
        self._ax_xlim = (self._x_lo, self._x_hi)
        self._ax_ylim = (_y_lo - _y_pad, _y_hi + _y_pad)

        self._build_ui()
        self._refresh_plot()

    # ── UI construction ────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(6)

        # ── Title bar ──────────────────────────────────────────────────────────
        b0_str = f"{self._b0:.4f}"
        b1_str = f"{self._b1:.4f}"
        title = QLabel(
            f"<b style='font-size:15px; color:#2C3E50;'>"
            f"Ŷ = {b0_str} + {b1_str}·X</b>"
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        outer.addWidget(title)

        # ── Main content row (vertical slider + chart) ─────────────────────────
        content_row = QHBoxLayout()
        content_row.setSpacing(4)

        # LEFT: vertical confidence slider
        left_col = QVBoxLayout()
        left_col.setSpacing(2)

        conf_top_lbl = QLabel("100%")
        conf_top_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        conf_top_lbl.setStyleSheet("font-size:11px; color:#555;")
        left_col.addWidget(conf_top_lbl)

        self._conf_slider = _DiamondSlider(Qt.Orientation.Vertical)
        self._conf_slider.setMinimum(0)
        self._conf_slider.setMaximum(100)
        self._conf_slider.setValue(self._conf_level)
        self._conf_slider.setToolTip("Kéo để thay đổi độ tin cậy (0%–100%)")
        self._conf_slider.setMinimumHeight(300)
        self._conf_slider.setFixedWidth(32)
        self._conf_slider.setInvertedAppearance(True)  # top = 100%
        left_col.addWidget(self._conf_slider, stretch=1)

        conf_bot_lbl = QLabel("0%")
        conf_bot_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        conf_bot_lbl.setStyleSheet("font-size:11px; color:#555;")
        left_col.addWidget(conf_bot_lbl)

        conf_title = QLabel("Độ tin cậy")
        conf_title.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        conf_title.setStyleSheet("font-size:11px; color:#888;")
        left_col.addWidget(conf_title)

        content_row.addLayout(left_col)

        # CENTER: matplotlib canvas + X slider in a vertical sub-layout
        right_col = QVBoxLayout()
        right_col.setSpacing(2)

        self._figure = Figure(figsize=(7, 4.5), dpi=100)
        self._ax = self._figure.add_subplot(111)
        self._mpl_canvas = FigureCanvas(self._figure)
        self._mpl_canvas.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        # Re-sync slider margins after each render (handles resize too)
        self._mpl_canvas.mpl_connect("draw_event",
                                     lambda _: self._sync_slider_margins())
        self._mpl_canvas.mpl_connect("resize_event",
                                     lambda _: self._sync_slider_margins())
        right_col.addWidget(self._mpl_canvas, stretch=1)

        # X slider — positioned to align exactly with the chart X axis
        self._x_slider_container = QWidget()
        self._x_slider_container.setFixedHeight(32)
        _x_inner = QHBoxLayout(self._x_slider_container)
        _x_inner.setContentsMargins(0, 0, 0, 0)
        _x_inner.setSpacing(0)
        self._x_slider = _CircleSlider(Qt.Orientation.Horizontal)
        self._x_slider.setMinimum(0)
        self._x_slider.setMaximum(self._x_steps)
        self._x_slider.setValue(self._x_to_slider(self._curr_x))
        self._x_slider.setToolTip("Kéo để thay đổi giá trị X dự báo")
        _x_inner.addWidget(self._x_slider)
        right_col.addWidget(self._x_slider_container)

        content_row.addLayout(right_col, stretch=1)

        outer.addLayout(content_row, stretch=1)

        # ── Info label row ─────────────────────────────────────────────────────
        self._info_lbl = QLabel()
        self._info_lbl.setTextFormat(Qt.TextFormat.RichText)
        self._info_lbl.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self._info_lbl.setStyleSheet(
            "background-color: #ECF0F1; border-radius: 4px; padding: 4px 8px;"
            " font-size: 13px;"
        )
        outer.addWidget(self._info_lbl)

        # ── Close button ───────────────────────────────────────────────────────
        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        outer.addWidget(btns)

        # ── Connect sliders ────────────────────────────────────────────────────
        self._x_slider.valueChanged.connect(self._on_x_slider_changed)
        self._conf_slider.valueChanged.connect(self._on_conf_slider_changed)

    # ── Slider helpers ─────────────────────────────────────────────────────────

    def _x_to_slider(self, x_val: float) -> int:
        rng = self._x_hi - self._x_lo
        if rng < 1e-12:
            return self._x_steps // 2
        return int(round((x_val - self._x_lo) / rng * self._x_steps))

    def _slider_to_x(self, step: int) -> float:
        return self._x_lo + step / self._x_steps * (self._x_hi - self._x_lo)

    # ── Interval computation ───────────────────────────────────────────────────

    def _prediction_half_width(self, x_pred: float, conf: float) -> float:
        """Half-width of OLS prediction interval at x_pred for conf ∈ [0,1]."""
        if conf < 1e-6 or not _SCIPY:
            return 0.0
        alpha = 1.0 - conf
        df = max(self._n - 2, 1)
        t_val = float(_scipy_stats.t.ppf(1.0 - alpha / 2.0, df))
        factor = 1.0 + 1.0 / self._n
        if self._sxx > 1e-12:
            factor += (x_pred - self._x_bar) ** 2 / self._sxx
        return t_val * self._s * float(np.sqrt(max(factor, 0.0)))

    # ── Plot ───────────────────────────────────────────────────────────────────

    def _refresh_plot(self) -> None:
        ax = self._ax
        ax.clear()

        x, y = self._x, self._y
        b0, b1 = self._b0, self._b1
        x_pred = self._curr_x
        conf = self._conf_level / 100.0

        x_line = np.linspace(self._ax_xlim[0], self._ax_xlim[1], 300)
        y_line = b0 + b1 * x_line

        # Scatter — no legend entry
        ax.scatter(x, y, c="#2C3E50", s=60, zorder=5,
                   edgecolors="white", linewidths=1.0)

        # Regression line — no legend entry
        ax.plot(x_line, y_line, color="#E74C3C", linewidth=2.2, zorder=3)

        # Point estimate (always at x_pred)
        y_pred = b0 + b1 * x_pred

        # Band half-width: computed at x_bar so dashed lines are truly
        # parallel (constant offset) and only change with confidence level.
        # Prediction interval at x_pred is shown in the info label only.
        hw_band = self._prediction_half_width(self._x_bar, conf)
        hw_pred = self._prediction_half_width(x_pred, conf)

        # Confidence band (two dashed lines, offset = hw_band = constant w.r.t. X)
        if hw_band > 0:
            lo = y_pred - hw_pred
            hi = y_pred + hw_pred
            band_label = f"Khoảng tin cậy {self._conf_level}%"
            ax.plot(x_line, y_line + hw_band, color="#3498DB", linewidth=1.6,
                    linestyle="--", zorder=2, label=band_label)
            ax.plot(x_line, y_line - hw_band, color="#3498DB", linewidth=1.6,
                    linestyle="--", zorder=2)
        else:
            lo = hi = None

        # Point estimate marker
        point_label = "Ước lượng điểm"
        ax.plot(x_pred, y_pred, "o", color="#27AE60", markersize=12, zorder=7,
                markeredgecolor="white", markeredgewidth=2, label=point_label)

        # Crosshair guides
        ax.axvline(x_pred, color="#27AE60", linewidth=1.0,
                   linestyle=":", alpha=0.6, zorder=2)
        ax.axhline(y_pred, color="#27AE60", linewidth=1.0,
                   linestyle=":", alpha=0.6, zorder=2)

        # Fixed axes — never change
        ax.set_xlim(*self._ax_xlim)
        ax.set_ylim(*self._ax_ylim)

        ax.set_xlabel("X", fontsize=11)
        ax.set_ylabel("Y", fontsize=11)
        ax.set_title("Dự báo điểm và dự báo khoảng",
                     fontsize=12, color="#2C3E50", fontweight="bold")
        ax.legend(loc="upper left", fontsize=9)
        ax.grid(True, alpha=0.25)
        self._figure.tight_layout(pad=1.5)
        self._mpl_canvas.draw_idle()

        # Info label — only 2 items
        if lo is not None:
            info_html = (
                f"Khoảng tin cậy <b>{self._conf_level}%</b>: "
                f"[<b>{lo:.4f}</b> ; <b>{hi:.4f}</b>]"
                f" &nbsp;|&nbsp; "
                f"Ước lượng điểm: "
                f"<b style='color:#27AE60;'>Ŷ({x_pred:.4f}) = {y_pred:.4f}</b>"
            )
        else:
            info_html = (
                f"Độ tin cậy: <b>0%</b> — Không hiển thị khoảng"
                f" &nbsp;|&nbsp; "
                f"Ước lượng điểm: "
                f"<b style='color:#27AE60;'>Ŷ({x_pred:.4f}) = {y_pred:.4f}</b>"
            )
        self._info_lbl.setText(info_html)

    # ── Slider handlers ────────────────────────────────────────────────────────

    def _on_x_slider_changed(self, value: int) -> None:
        self._curr_x = self._slider_to_x(value)
        self._refresh_plot()

    def _on_conf_slider_changed(self, value: int) -> None:
        self._conf_level = value
        self._refresh_plot()

    # ── Axis-aligned slider margins ────────────────────────────────────────────

    def _sync_slider_margins(self) -> None:
        """Set left/right margins of the X slider container to match the
        matplotlib axes bounding box, so the slider tracks the X axis exactly."""
        canvas_w = self._mpl_canvas.width()
        if canvas_w <= 0:
            return
        pos = self._ax.get_position()  # axes bbox in figure fraction [0, 1]
        left_px = max(0, int(pos.x0 * canvas_w))
        right_px = max(0, int((1.0 - pos.x1) * canvas_w))
        layout = self._x_slider_container.layout()
        if layout is not None:
            layout.setContentsMargins(left_px, 0, right_px, 0)


# ───────────────────────────────────────────────────────────────────────────────
# Custom slider subclasses: circle handle (horizontal) & diamond handle (vertical)
# ───────────────────────────────────────────────────────────────────────────────

if _QT:
    from PySide6.QtWidgets import QSlider
    from PySide6.QtGui import QPainter, QBrush, QPen, QColor, QPolygonF
    from PySide6.QtCore import QRectF, QPointF

    class _CircleSlider(QSlider):
        """QSlider with a filled-circle thumb, drawn via widget dimensions."""

        _THUMB_R = 9  # radius in px

        def paintEvent(self, event) -> None:  # type: ignore[override]
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            r = self._THUMB_R
            pad = r + 2
            w = self.width()
            h = self.height()

            # Groove: horizontal line at widget vertical center
            mid_y = h // 2
            painter.setPen(QPen(QColor("#BDC3C7"), 3))
            painter.drawLine(pad, mid_y, w - pad, mid_y)

            # Thumb position
            ratio = (self.value() - self.minimum()) / max(self.maximum() - self.minimum(), 1)
            cx = pad + ratio * (w - 2 * pad)
            cy = h / 2

            painter.setBrush(QBrush(QColor("#27AE60")))
            painter.setPen(QPen(QColor("white"), 2))
            painter.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

    class _DiamondSlider(QSlider):
        """QSlider with a diamond-shaped thumb.

        paintEvent: value=max drawn at top, value=min drawn at bottom.
        Mouse events are fully overridden to match this visual mapping:
          drag UP   → increase value (toward max / 100%)
          drag DOWN → decrease value (toward min /   0%)
        """

        _HALF = 9  # half-size of diamond in px

        def paintEvent(self, event) -> None:  # type: ignore[override]
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)

            half = self._HALF
            pad = half + 2
            w = self.width()
            h = self.height()

            # Groove: vertical line at widget horizontal center
            mid_x = w // 2
            painter.setPen(QPen(QColor("#BDC3C7"), 3))
            painter.drawLine(mid_x, pad, mid_x, h - pad)

            # Thumb position:
            # value=max (100%) → cy = pad       (top)
            # value=min (  0%) → cy = h - pad   (bottom)
            raw_ratio = (self.value() - self.minimum()) / max(self.maximum() - self.minimum(), 1)
            cy = pad + (1.0 - raw_ratio) * (h - 2 * pad)
            cx = w / 2

            diamond = QPolygonF([
                QPointF(cx,        cy - half),
                QPointF(cx + half, cy),
                QPointF(cx,        cy + half),
                QPointF(cx - half, cy),
            ])
            painter.setBrush(QBrush(QColor("#3498DB")))
            painter.setPen(QPen(QColor("white"), 2))
            painter.drawPolygon(diamond)

        # ── Manual mouse handling ─────────────────────────────────────────

        def mousePressEvent(self, event) -> None:  # type: ignore[override]
            from PySide6.QtCore import Qt as _Qt
            if event.button() == _Qt.MouseButton.LeftButton:
                self._apply_pos(event.position().y())
                event.accept()
            else:
                super().mousePressEvent(event)

        def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
            from PySide6.QtCore import Qt as _Qt
            if event.buttons() & _Qt.MouseButton.LeftButton:
                self._apply_pos(event.position().y())
                event.accept()
            else:
                super().mouseMoveEvent(event)

        def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
            event.accept()

        def _apply_pos(self, y: float) -> None:
            """Convert widget Y coordinate to slider value and emit."""
            pad = self._HALF + 2
            track = self.height() - 2 * pad
            if track <= 0:
                return
            # y=pad (top) → value=max; y=height-pad (bottom) → value=min
            ratio = (y - pad) / track          # 0.0 at top, 1.0 at bottom
            ratio = max(0.0, min(1.0, ratio))
            span = self.maximum() - self.minimum()
            value = int(round(self.maximum() - ratio * span))
            self.setValue(value)

else:
    # Headless fallback – never instantiated in practice
    _CircleSlider = object  # type: ignore[assignment,misc]
    _DiamondSlider = object  # type: ignore[assignment,misc]


# ═══════════════════════════════════════════════════════════════════════════════
# Interactive Chart Canvas
# ═══════════════════════════════════════════════════════════════════════════════


class _RegressionCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Matplotlib canvas with interactive trend line (drag + rotate)."""

    line_changed = Signal() if _QT else None  # type: ignore[assignment]
    point_clicked = Signal(int) if _QT else None  # type: ignore[assignment]

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._figure = Figure(figsize=(9, 5), dpi=100)
        self._ax = self._figure.add_subplot(111)
        self._canvas = FigureCanvas(self._figure)
        layout.addWidget(self._canvas)

        # Data
        self._x: np.ndarray | None = None
        self._y: np.ndarray | None = None

        # Trend line: y = b0 + b1 * x
        self._b0: float = 0.0
        self._b1: float = 0.0
        self._has_trend: bool = False
        self._show_errors: bool = False
        self._highlight_idx: int = -1  # -1 = none
        self._equation_text: str = ""

        # Drag state
        self._dragging: str | None = None  # 'body', 'left', 'right'
        self._drag_start_xy: tuple[float, float] | None = None
        self._drag_start_b0: float = 0.0
        self._drag_start_b1: float = 0.0

        # Connect events
        self._canvas.mpl_connect("button_press_event", self._on_press)
        self._canvas.mpl_connect("motion_notify_event", self._on_motion)
        self._canvas.mpl_connect("button_release_event", self._on_release)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_data(self, x: np.ndarray, y: np.ndarray) -> None:
        self._x = x
        self._y = y
        self._has_trend = False
        self._show_errors = False
        self._highlight_idx = -1
        self._equation_text = ""
        self._redraw()

    def add_trend_line(self) -> None:
        if self._x is None or self._y is None:
            return
        self._has_trend = True
        self._b0 = float(np.mean(self._y))
        self._b1 = 0.0
        self._redraw()
        if self.line_changed is not None:
            self.line_changed.emit()

    def set_trend_coefficients(self, b0: float, b1: float,
                               equation: str = "") -> None:
        self._b0 = b0
        self._b1 = b1
        self._has_trend = True
        self._equation_text = equation
        self._redraw()
        if self.line_changed is not None:
            self.line_changed.emit()

    def set_show_errors(self, show: bool) -> None:
        self._show_errors = show
        self._redraw()

    def toggle_highlight(self, idx: int) -> None:
        if self._highlight_idx == idx:
            self._highlight_idx = -1
        else:
            self._highlight_idx = idx
        self._redraw()

    def get_b0_b1(self) -> tuple[float, float]:
        return self._b0, self._b1

    def get_y_hat(self) -> np.ndarray | None:
        if self._x is None or not self._has_trend:
            return None
        return self._b0 + self._b1 * self._x

    def export_png(self) -> bytes:
        buf = io.BytesIO()
        self._figure.savefig(buf, format="png", dpi=150, bbox_inches="tight")
        buf.seek(0)
        return buf.read()

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _redraw(self) -> None:
        ax = self._ax
        ax.clear()

        if self._x is None or self._y is None:
            ax.set_xlabel("X")
            ax.set_ylabel("Y")
            ax.set_title("Biểu đồ phân tán")
            ax.grid(True, alpha=0.3)
            self._canvas.draw_idle()
            return

        x, y = self._x, self._y
        x_margin = (x.max() - x.min()) * 0.15 if x.max() != x.min() else 1.0
        y_margin = (y.max() - y.min()) * 0.15 if y.max() != y.min() else 1.0

        # Scatter points
        ax.scatter(x, y, c="#2C3E50", s=70, zorder=5, edgecolors="white",
                   linewidths=1.2, label="Quan sát")

        # Trend line
        if self._has_trend:
            x_line = np.array([x.min() - x_margin, x.max() + x_margin])
            y_line = self._b0 + self._b1 * x_line
            ax.plot(x_line, y_line, color="#E74C3C", linewidth=2.2,
                    label="Đường xu hướng", zorder=3)

            # Endpoint handles
            ax.plot(x_line[0], y_line[0], "s", color="#E74C3C",
                    markersize=9, zorder=6)
            ax.plot(x_line[1], y_line[1], "s", color="#E74C3C",
                    markersize=9, zorder=6)

            # Error lines
            if self._show_errors:
                y_hat = self._b0 + self._b1 * x
                sse = float(np.sum((y - y_hat) ** 2))
                for i in range(len(x)):
                    color = "#F39C12" if i == self._highlight_idx else "#95A5A6"
                    lw = 2.0 if i == self._highlight_idx else 1.2
                    ax.annotate(
                        "", xy=(x[i], y[i]), xytext=(x[i], y_hat[i]),
                        arrowprops=dict(arrowstyle="<->", color=color,
                                        lw=lw, linestyle="--"),
                        zorder=4,
                    )
                    if i == self._highlight_idx:
                        mid_y = (y[i] + y_hat[i]) / 2
                        ax.text(x[i] + x_margin * 0.08, mid_y,
                                f"e{i+1}",
                                fontsize=11, fontweight="bold",
                                color="#E67E22", zorder=7)
                        # Mark Y_i and Ŷ_i on Y-axis
                        ax.annotate(
                            f"Y{i+1}={y[i]:.2f}",
                            xy=(ax.get_xlim()[0], y[i]),
                            fontsize=9, color="#2C3E50", fontweight="bold",
                            ha="right", va="center",
                            xytext=(-5, 0), textcoords="offset points",
                            zorder=7,
                        )
                        ax.annotate(
                            f"Ŷ{i+1}={y_hat[i]:.2f}",
                            xy=(ax.get_xlim()[0], y_hat[i]),
                            fontsize=9, color="#E74C3C", fontweight="bold",
                            ha="right", va="center",
                            xytext=(-5, 0), textcoords="offset points",
                            zorder=7,
                        )
                # SSE annotation box
                ax.text(
                    0.98, 0.02, f"Σeᵢ² = {sse:.2f}",
                    transform=ax.transAxes, fontsize=12, fontweight="bold",
                    color="#8E44AD", ha="right", va="bottom",
                    bbox=dict(boxstyle="round,pad=0.4", facecolor="#F5EEF8",
                              edgecolor="#8E44AD", alpha=0.9),
                    zorder=10,
                )

            # Equation text
            if self._equation_text:
                ax.set_title(self._equation_text, fontsize=13,
                             fontweight="bold", color="#2980B9", pad=12)
            else:
                ax.set_title("Biểu đồ phân tán", pad=12)
        else:
            ax.set_title("Biểu đồ phân tán", pad=12)

        ax.set_xlabel("X", fontsize=12)
        ax.set_ylabel("Y", fontsize=12)
        ax.set_xlim(x.min() - x_margin, x.max() + x_margin)

        # Y-axis range should include trend line too
        all_y = list(y)
        if self._has_trend:
            y_hat = self._b0 + self._b1 * x
            all_y.extend(y_hat)
        y_lo, y_hi = min(all_y), max(all_y)
        y_pad = (y_hi - y_lo) * 0.15 if y_hi != y_lo else 1.0
        ax.set_ylim(y_lo - y_pad, y_hi + y_pad)

        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper left", fontsize=10)
        self._figure.tight_layout()
        self._canvas.draw_idle()

    # ── Mouse interaction ─────────────────────────────────────────────────────

    def _on_press(self, event) -> None:
        if event.inaxes != self._ax or not self._has_trend:
            # Check if user clicked on a data point
            if event.inaxes == self._ax and self._x is not None and self._show_errors:
                self._check_point_click(event)
            return

        if self._x is None:
            return

        mx, my = event.xdata, event.ydata
        x = self._x
        x_margin = (x.max() - x.min()) * 0.15 if x.max() != x.min() else 1.0

        # Check endpoints first
        xl = x.min() - x_margin
        xr = x.max() + x_margin
        yl = self._b0 + self._b1 * xl
        yr = self._b0 + self._b1 * xr

        # Tolerance in data coords
        tol_x = (xr - xl) * 0.04
        tol_y = (max(yl, yr) - min(yl, yr) + 1) * 0.08

        if abs(mx - xl) < tol_x and abs(my - yl) < max(tol_y, 0.5):
            self._dragging = "left"
        elif abs(mx - xr) < tol_x and abs(my - yr) < max(tol_y, 0.5):
            self._dragging = "right"
        else:
            # Check body (proximity to line)
            y_on_line = self._b0 + self._b1 * mx
            if abs(my - y_on_line) < max(tol_y, 0.5):
                self._dragging = "body"
            else:
                # Check point click for highlight
                if self._show_errors:
                    self._check_point_click(event)
                return

        self._drag_start_xy = (mx, my)
        self._drag_start_b0 = self._b0
        self._drag_start_b1 = self._b1

    def _on_motion(self, event) -> None:
        if self._dragging is None or event.inaxes != self._ax:
            return
        if event.xdata is None or event.ydata is None:
            return

        mx, my = event.xdata, event.ydata
        sx, sy = self._drag_start_xy  # type: ignore[misc]
        dx, dy = mx - sx, my - sy

        if self._dragging == "body":
            # Translate: shift b0 by dy
            self._b0 = self._drag_start_b0 + dy
            self._redraw()
            if self.line_changed is not None:
                self.line_changed.emit()

        elif self._dragging in ("left", "right"):
            # Rotate around pivot
            x = self._x
            assert x is not None
            x_margin = (x.max() - x.min()) * 0.15 if x.max() != x.min() else 1.0
            xl = x.min() - x_margin
            xr = x.max() + x_margin

            if self._dragging == "left":
                # Pivot at right end
                yr_pivot = self._drag_start_b0 + self._drag_start_b1 * xr
                yl_new = (self._drag_start_b0 + self._drag_start_b1 * xl) + dy
                if abs(xr - xl) > 1e-9:
                    self._b1 = (yr_pivot - yl_new) / (xr - xl)
                    self._b0 = yl_new - self._b1 * xl
            else:
                # Pivot at left end
                yl_pivot = self._drag_start_b0 + self._drag_start_b1 * xl
                yr_new = (self._drag_start_b0 + self._drag_start_b1 * xr) + dy
                if abs(xr - xl) > 1e-9:
                    self._b1 = (yr_new - yl_pivot) / (xr - xl)
                    self._b0 = yl_pivot - self._b1 * xl

            self._redraw()
            if self.line_changed is not None:
                self.line_changed.emit()

    def _on_release(self, event) -> None:
        self._dragging = None
        self._drag_start_xy = None

    def _check_point_click(self, event) -> None:
        if self._x is None or event.xdata is None:
            return
        x, y = self._x, self._y
        assert y is not None
        x_range = x.max() - x.min() if x.max() != x.min() else 1.0
        y_range = y.max() - y.min() if y.max() != y.min() else 1.0
        best_i = -1
        best_d = float("inf")
        for i in range(len(x)):
            dx = (event.xdata - x[i]) / x_range
            dy = (event.ydata - y[i]) / y_range
            d = dx * dx + dy * dy
            if d < best_d:
                best_d = d
                best_i = i
        if best_d < 0.01:  # close enough
            self.toggle_highlight(best_i)
            if self.point_clicked is not None:
                self.point_clicked.emit(best_i)


# ═══════════════════════════════════════════════════════════════════════════════
# Computation Table
# ═══════════════════════════════════════════════════════════════════════════════


class _ComputationTable(_CanvasBase):  # type: ignore[valid-type]
    """Table displaying Y_i, Ŷ_i, e_i, e_i² with sum row."""

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget()
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setStyleSheet(
            "QTableWidget { gridline-color: #DDE2E8; font-size: 14px; }"
            "QHeaderView::section { background-color: #2C3E50; color: #FFF;"
            " padding: 8px; font-weight: bold; font-size: 15px; }"
        )
        layout.addWidget(self._table)

        self._n = 0

    def update_data(
        self,
        y: np.ndarray | None = None,
        y_hat: np.ndarray | None = None,
        show_errors: bool = False,
        highlight_idx: int = -1,
    ) -> None:
        if y is None:
            self._table.setRowCount(0)
            self._table.setColumnCount(0)
            return

        n = len(y)
        self._n = n
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(
            ["i", "Yᵢ", "Ŷᵢ", "eᵢ = Yᵢ − Ŷᵢ", "eᵢ²"]
        )
        self._table.setRowCount(n + 1)  # +1 for sum row

        sum_y = 0.0
        sum_yh = 0.0
        sum_e = 0.0
        sum_e2 = 0.0

        for i in range(n):
            # Column 0: index
            idx_item = QTableWidgetItem(str(i + 1))
            idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 0, idx_item)

            # Column 1: Y_i
            yi_item = QTableWidgetItem(f"{y[i]:.2f}")
            yi_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 1, yi_item)
            sum_y += y[i]

            # Column 2: Y_hat_i
            if y_hat is not None:
                yhi = y_hat[i]
                yh_item = QTableWidgetItem(f"{yhi:.2f}")
                yh_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self._table.setItem(i, 2, yh_item)
                sum_yh += yhi

                # Column 3 & 4: errors
                if show_errors:
                    ei = y[i] - yhi
                    ei2 = ei * ei
                    e_item = QTableWidgetItem(f"{ei:.2f}")
                    e_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self._table.setItem(i, 3, e_item)

                    e2_item = QTableWidgetItem(f"{ei2:.2f}")
                    e2_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    self._table.setItem(i, 4, e2_item)
                    sum_e += ei
                    sum_e2 += ei2
                else:
                    self._table.setItem(i, 3, QTableWidgetItem(""))
                    self._table.setItem(i, 4, QTableWidgetItem(""))
            else:
                self._table.setItem(i, 2, QTableWidgetItem(""))
                self._table.setItem(i, 3, QTableWidgetItem(""))
                self._table.setItem(i, 4, QTableWidgetItem(""))

            # Highlight row
            if i == highlight_idx:
                for c in range(5):
                    item = self._table.item(i, c)
                    if item:
                        item.setBackground(Qt.GlobalColor.yellow)

        # Sum row
        sum_label = QTableWidgetItem("Σ")
        sum_label.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        f = QFont()
        f.setBold(True)
        sum_label.setFont(f)
        self._table.setItem(n, 0, sum_label)

        sum_y_item = QTableWidgetItem(f"{sum_y:.2f}")
        sum_y_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        sum_y_item.setFont(f)
        self._table.setItem(n, 1, sum_y_item)

        if y_hat is not None:
            syh = QTableWidgetItem(f"{sum_yh:.2f}")
            syh.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            syh.setFont(f)
            self._table.setItem(n, 2, syh)

            if show_errors:
                se = QTableWidgetItem(f"{sum_e:.2f}")
                se.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                se.setFont(f)
                self._table.setItem(n, 3, se)

                se2 = QTableWidgetItem(f"{sum_e2:.2f}")
                se2.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                se2.setFont(f)
                se2.setForeground(Qt.GlobalColor.red)
                self._table.setItem(n, 4, se2)
            else:
                self._table.setItem(n, 3, QTableWidgetItem(""))
                self._table.setItem(n, 4, QTableWidgetItem(""))
        else:
            self._table.setItem(n, 2, QTableWidgetItem(""))
            self._table.setItem(n, 3, QTableWidgetItem(""))
            self._table.setItem(n, 4, QTableWidgetItem(""))

        # Bold sum row background
        for c in range(5):
            item = self._table.item(n, c)
            if item:
                item.setBackground(Qt.GlobalColor.lightGray)


# ═══════════════════════════════════════════════════════════════════════════════
# Main Module View
# ═══════════════════════════════════════════════════════════════════════════════


class _LinearRegressionView(_CanvasBase):  # type: ignore[valid-type]
    """Root widget assembling toolbar, chart and computation table."""

    open_module_signal = Signal(str) if _QT else None  # type: ignore[assignment]

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        if not _QT:
            return

        self._x: np.ndarray | None = None
        self._y: np.ndarray | None = None
        self._show_errors = False
        self._highlight_idx = -1

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        # ── Toolbar ───────────────────────────────────────────────────────────
        toolbar = QFrame()
        toolbar.setObjectName("lr_toolbar")
        toolbar.setStyleSheet(
            "#lr_toolbar { background-color: #FFF; border: 1px solid #DDE2E8;"
            " border-radius: 6px; padding: 4px 8px; }"
        )
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(8, 6, 8, 6)
        tb_layout.setSpacing(8)

        self._btn_input = QPushButton("📊 Nhập dữ liệu")
        self._btn_input.setStyleSheet(
            "background-color: #3498DB; color: #FFF; padding: 7px 14px;"
            " font-weight: 600; border-radius: 4px;"
        )
        tb_layout.addWidget(self._btn_input)

        self._btn_trend = QPushButton("📈 Thêm đường xu hướng")
        self._btn_trend.setEnabled(False)
        self._btn_trend.setStyleSheet(
            "background-color: #E67E22; color: #FFF; padding: 7px 14px;"
            " font-weight: 600; border-radius: 4px;"
        )
        tb_layout.addWidget(self._btn_trend)

        tb_layout.addStretch()

        self._btn_sse = QPushButton("Σeᵢ²")
        self._btn_sse.setEnabled(False)
        self._btn_sse.setStyleSheet(
            "background-color: #8E44AD; color: #FFF; padding: 7px 14px;"
            " font-weight: 600; border-radius: 4px;"
        )
        tb_layout.addWidget(self._btn_sse)

        self._btn_solve = QPushButton("Giải")
        self._btn_solve.setEnabled(False)
        self._btn_solve.setStyleSheet(
            "background-color: #27AE60; color: #FFF; padding: 7px 14px;"
            " font-weight: 600; border-radius: 4px;"
        )
        tb_layout.addWidget(self._btn_solve)

        self._btn_r2 = QPushButton("R²")
        self._btn_r2.setVisible(False)
        self._btn_r2.setStyleSheet(
            "background-color: #8E44AD; color: #FFF; padding: 7px 14px;"
            " font-weight: 600; border-radius: 4px;"
        )
        tb_layout.addWidget(self._btn_r2)

        self._btn_forecast = QPushButton("Dự báo")
        self._btn_forecast.setVisible(False)
        self._btn_forecast.setStyleSheet(
            "background-color: #16A085; color: #FFF; padding: 7px 14px;"
            " font-weight: 600; border-radius: 4px;"
        )
        tb_layout.addWidget(self._btn_forecast)

        root.addWidget(toolbar)

        # ── Chart ─────────────────────────────────────────────────────────────
        self._canvas = _RegressionCanvas()
        root.addWidget(self._canvas, stretch=5)

        # ── Computation table ─────────────────────────────────────────────────
        self._comp_table = _ComputationTable()
        # Show ~5 data rows + header + sum row
        row_h = 30
        visible_rows = 5
        header_h = 34
        self._comp_table.setMaximumHeight(header_h + (visible_rows + 1) * row_h + 4)
        root.addWidget(self._comp_table, stretch=0)

    def _connect_signals(self) -> None:
        self._btn_input.clicked.connect(self._on_input_data)
        self._btn_trend.clicked.connect(self._on_add_trend)
        self._btn_sse.clicked.connect(self._on_toggle_sse)
        self._btn_solve.clicked.connect(self._on_solve)
        self._btn_r2.clicked.connect(self._on_r2)
        self._btn_forecast.clicked.connect(self._on_forecast)
        assert self._canvas.line_changed is not None
        assert self._canvas.point_clicked is not None
        self._canvas.line_changed.connect(self._on_line_changed)
        self._canvas.point_clicked.connect(self._on_point_clicked)

    # ── Handlers ──────────────────────────────────────────────────────────────

    def _on_input_data(self) -> None:
        old_x = list(self._x) if self._x is not None else []
        old_y = list(self._y) if self._y is not None else []
        dlg = _DataInputDialog(old_x, old_y, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            xs, ys = dlg.get_data()
            self._x = np.array(xs, dtype=float)
            self._y = np.array(ys, dtype=float)
            self._show_errors = False
            self._highlight_idx = -1
            self._canvas.set_data(self._x, self._y)
            self._comp_table.update_data(y=self._y)
            self._btn_trend.setEnabled(True)
            self._btn_sse.setEnabled(False)
            self._btn_solve.setEnabled(False)
            self._btn_r2.setVisible(False)
            self._btn_forecast.setVisible(False)

    def _on_add_trend(self) -> None:
        self._canvas.add_trend_line()
        self._btn_sse.setEnabled(True)
        self._btn_solve.setEnabled(True)
        self._on_line_changed()

    def _on_toggle_sse(self) -> None:
        self._show_errors = not self._show_errors
        self._highlight_idx = -1
        self._canvas.set_show_errors(self._show_errors)
        self._update_table()

    def _on_solve(self) -> None:
        if self._x is None or self._y is None:
            return
        dlg = _SolveDialog(self._x, self._y, self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            b0, b1 = dlg.get_coefficients()
            eq = f"Ŷ = {b0:.4f} + {b1:.4f}·X"
            self._canvas.set_trend_coefficients(b0, b1, equation=eq)
            self._update_table()
            self._btn_r2.setVisible(True)
            self._btn_forecast.setVisible(True)

    def _on_r2(self) -> None:
        if self._x is None or self._y is None:
            return
        b0, b1 = self._canvas.get_b0_b1()
        dlg = _R2Dialog(self._x, self._y, b0, b1, self)
        dlg.exec()

    def _on_forecast(self) -> None:
        if self._x is None or self._y is None:
            return
        b0, b1 = self._canvas.get_b0_b1()
        dlg = _ForecastDialog(self._x, self._y, b0, b1, self)
        dlg.exec()

    def _on_line_changed(self) -> None:
        self._update_table()

    def _on_point_clicked(self, idx: int) -> None:
        if self._highlight_idx == idx:
            self._highlight_idx = -1
        else:
            self._highlight_idx = idx
        self._update_table()

    def _update_table(self) -> None:
        y_hat = self._canvas.get_y_hat()
        self._comp_table.update_data(
            y=self._y,
            y_hat=y_hat,
            show_errors=self._show_errors,
            highlight_idx=self._highlight_idx,
        )

    # ── State ─────────────────────────────────────────────────────────────────

    def get_state(self) -> dict:
        state: dict[str, Any] = {}
        if self._x is not None and self._y is not None:
            state["x"] = self._x.tolist()
            state["y"] = self._y.tolist()
        b0, b1 = self._canvas.get_b0_b1()
        state["b0"] = b0
        state["b1"] = b1
        state["has_trend"] = self._canvas._has_trend
        state["show_errors"] = self._show_errors
        return state

    def restore_state(self, state: dict) -> None:
        if "x" in state and "y" in state:
            self._x = np.array(state["x"], dtype=float)
            self._y = np.array(state["y"], dtype=float)
            self._canvas.set_data(self._x, self._y)
            self._btn_trend.setEnabled(True)

            if state.get("has_trend"):
                b0 = state.get("b0", 0.0)
                b1 = state.get("b1", 0.0)
                self._canvas.set_trend_coefficients(b0, b1)
                self._btn_sse.setEnabled(True)
                self._btn_solve.setEnabled(True)

            self._show_errors = state.get("show_errors", False)
            self._canvas.set_show_errors(self._show_errors)
            self._update_table()

    def export_png(self) -> bytes:
        return self._canvas.export_png()


# ═══════════════════════════════════════════════════════════════════════════════
# Module Class
# ═══════════════════════════════════════════════════════════════════════════════


class LinearRegressionModule(BaseModule):
    """IIMP module: Phân tích Hồi quy Tuyến tính Đơn."""

    def __init__(self, manifest: dict, context: ModuleContext) -> None:
        super().__init__(manifest, context)
        self._view: _LinearRegressionView | None = None

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def on_load(self) -> None:
        self.context.logger.info("LinearRegressionModule loaded.")

    def build_view(self) -> QWidget:
        self._view = _LinearRegressionView()
        return self._view

    def on_activate(self) -> None:
        self.context.logger.info("LinearRegressionModule activated.")

    def on_deactivate(self) -> None:
        self.context.logger.info("LinearRegressionModule deactivated.")

    def on_unload(self) -> None:
        self._view = None
        self.context.logger.info("LinearRegressionModule unloaded.")

    # ── State persistence ─────────────────────────────────────────────────────

    def get_state(self) -> dict:
        if self._view is None:
            return {}
        state = self._view.get_state()
        state["_state_version"] = self.manifest.get("data_contract_version", "1.0.0")
        return state

    def restore_state(self, state: dict) -> None:
        if self._view is not None and state:
            self._view.restore_state(state)

    # ── Export ────────────────────────────────────────────────────────────────

    def export(self, target_path: str, export_type: str = "default") -> None:
        if self._view is None:
            raise RuntimeError("No view to export.")
        data = self._view.export_png()
        with open(target_path, "wb") as f:
            f.write(data)
        self.context.logger.info(f"Exported chart to {target_path}")
