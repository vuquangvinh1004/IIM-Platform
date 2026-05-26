"""Hồi quy tuyến tính bội với 2 biến độc lập (3D) — v1.0.0.

Mô hình:
    Ŷ = b₀ + b₁X₁ + b₂X₂

Tính hệ số bằng OLS với ma trận thiết kế:
  beta = (X^T X)^(-1) X^T y  (thực thi bằng numpy.linalg.lstsq)
"""
from __future__ import annotations

import io
from typing import Any

import numpy as np

try:
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QAbstractItemView,
        QCheckBox,
        QDialog,
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

_DialogBase = QDialog if _QT else object  # type: ignore[misc]
_WidgetBase = QWidget if _QT else object  # type: ignore[misc]
_CanvasBase = QWidget if _QT else object  # type: ignore[misc]


def _solve_ols_two_predictors(x1: np.ndarray, x2: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Solve OLS coefficients for Y = b₀ + b₁X₁ + b₂X₂.

    Raises ValueError when the design matrix is rank-deficient.
    """
    x_mat = np.column_stack([np.ones(len(y)), x1, x2])
    beta, _, rank, _ = np.linalg.lstsq(x_mat, y, rcond=None)
    if rank < 3:
        raise ValueError("Dữ liệu suy biến, không thể giải đầy đủ hệ số.")
    return beta


def _regression_metrics(
    y: np.ndarray,
    y_hat: np.ndarray,
    predictor_count: int = 2,
) -> tuple[float, float, float, float]:
    """Return SSE, SST, R2, adjusted R2 for the fitted model."""
    y_mean = float(np.mean(y))
    sse = float(np.sum((y - y_hat) ** 2))
    sst = float(np.sum((y - y_mean) ** 2))

    if sst <= 1e-12:
        r2 = 1.0 if sse <= 1e-12 else 0.0
    else:
        r2 = 1.0 - (sse / sst)

    n = len(y)
    if n <= predictor_count + 1:
        adj_r2 = r2
    else:
        adj_r2 = 1.0 - ((1.0 - r2) * (n - 1) / (n - predictor_count - 1))

    return sse, sst, r2, adj_r2


class _DataInputDialog(_DialogBase):  # type: ignore[valid-type]
    """Dialog nhập bảng quan sát (X₁, X₂, Y)."""

    def __init__(
        self,
        x1_data: list[float],
        x2_data: list[float],
        y_data: list[float],
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        if not _QT:
            return
        self.setWindowTitle("Nhập dữ liệu quan sát (X₁, X₂, Y)")
        self.setMinimumSize(520, 460)
        self._x1_result: list[float] = []
        self._x2_result: list[float] = []
        self._y_result: list[float] = []
        self._build_ui(x1_data, x2_data, y_data)

    def _build_ui(
        self,
        x1_data: list[float],
        x2_data: list[float],
        y_data: list[float],
    ) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        hint = QLabel("Nhập dữ liệu quan sát tối đa 30 điểm (X₁, X₂, Y):")
        layout.addWidget(hint)

        row_hl = QHBoxLayout()
        row_hl.addWidget(QLabel("Số quan sát:"))
        self._row_spin = QSpinBox()
        self._row_spin.setRange(3, 30)
        self._row_spin.setValue(max(3, len(y_data)))
        self._row_spin.setButtonSymbols(QSpinBox.ButtonSymbols.NoButtons)
        self._row_spin.valueChanged.connect(self._resize_table)
        row_hl.addWidget(self._row_spin)
        row_hl.addStretch()
        layout.addLayout(row_hl)

        self._table = QTableWidget()
        self._table.setColumnCount(3)
        self._table.setHorizontalHeaderLabels(["X₁", "X₂", "Y"])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        layout.addWidget(self._table, stretch=1)

        n = max(3, len(y_data))
        self._row_spin.setValue(n)
        self._table.setRowCount(n)
        for i in range(n):
            v1 = str(x1_data[i]) if i < len(x1_data) else ""
            v2 = str(x2_data[i]) if i < len(x2_data) else ""
            vy = str(y_data[i]) if i < len(y_data) else ""
            self._table.setItem(i, 0, QTableWidgetItem(v1))
            self._table.setItem(i, 1, QTableWidgetItem(v2))
            self._table.setItem(i, 2, QTableWidgetItem(vy))

        btn_hl = QHBoxLayout()
        btn_ok = QPushButton("Hoàn tất")
        btn_ok.setStyleSheet(
            "background-color: #8D571C; color: #FFFFFF; padding: 8px 14px;"
            " border-radius: 10px; font-weight: 600;"
        )
        btn_ok.clicked.connect(self._accept_data)

        btn_reset = QPushButton("Nhập lại")
        btn_reset.setStyleSheet(
            "background-color: transparent; color: #B0413E;"
            " border: 1px solid #B0413E; padding: 8px 14px; border-radius: 10px;"
        )
        btn_reset.clicked.connect(self._reset_table)

        btn_hl.addWidget(btn_ok)
        btn_hl.addWidget(btn_reset)
        btn_hl.addStretch()
        layout.addLayout(btn_hl)

    def _resize_table(self, n: int) -> None:
        old = self._table.rowCount()
        self._table.setRowCount(n)
        for i in range(old, n):
            self._table.setItem(i, 0, QTableWidgetItem(""))
            self._table.setItem(i, 1, QTableWidgetItem(""))
            self._table.setItem(i, 2, QTableWidgetItem(""))

    def _reset_table(self) -> None:
        for i in range(self._table.rowCount()):
            self._table.setItem(i, 0, QTableWidgetItem(""))
            self._table.setItem(i, 1, QTableWidgetItem(""))
            self._table.setItem(i, 2, QTableWidgetItem(""))

    def _accept_data(self) -> None:
        x1_list: list[float] = []
        x2_list: list[float] = []
        y_list: list[float] = []

        for i in range(self._table.rowCount()):
            c1 = self._table.item(i, 0)
            c2 = self._table.item(i, 1)
            cy = self._table.item(i, 2)
            t1 = c1.text().strip() if c1 else ""
            t2 = c2.text().strip() if c2 else ""
            ty = cy.text().strip() if cy else ""

            if not (t1 and t2 and ty):
                continue

            try:
                x1 = float(t1)
                x2 = float(t2)
                y = float(ty)
            except ValueError:
                QMessageBox.warning(self, "Lỗi", f"Hàng {i + 1}: giá trị không hợp lệ.")
                return

            x1_list.append(x1)
            x2_list.append(x2)
            y_list.append(y)

        if len(y_list) < 3:
            QMessageBox.warning(self, "Lỗi", "Cần ít nhất 3 quan sát hợp lệ.")
            return

        self._x1_result = x1_list
        self._x2_result = x2_list
        self._y_result = y_list
        self.accept()

    def get_data(self) -> tuple[list[float], list[float], list[float]]:
        return self._x1_result, self._x2_result, self._y_result


class _SolveDialog(_DialogBase):  # type: ignore[valid-type]
    """Dialog hiển thị công thức OLS và kết quả hệ số b0, b1, b2."""

    def __init__(
        self,
        x1: np.ndarray,
        x2: np.ndarray,
        y: np.ndarray,
        parent: "QWidget | None" = None,
    ) -> None:
        super().__init__(parent)
        if not _QT:
            return
        self.setWindowTitle("Giải hệ số hồi quy OLS")
        self.setMinimumSize(640, 420)
        self._coef = np.array([0.0, 0.0, 0.0], dtype=float)
        self._build_ui(x1, x2, y)

    @staticmethod
    def _solve_beta(x1: np.ndarray, x2: np.ndarray, y: np.ndarray) -> np.ndarray:
        return _solve_ols_two_predictors(x1, x2, y)

    def _build_ui(self, x1: np.ndarray, x2: np.ndarray, y: np.ndarray) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Phương pháp Bình phương Nhỏ nhất (OLS) cho hồi quy bội")
        font = QFont()
        font.setBold(True)
        title.setFont(font)
        title.setStyleSheet("font-size: 18px; color: #173A5E;")
        layout.addWidget(title)

        formula = QLabel(
            "<div style='font-size:16px;'>"
            "<b>Mô hình:</b> Y = b<sub>0</sub> + b<sub>1</sub>X<sub>1</sub> + b<sub>2</sub>X<sub>2</sub>"
            "</div>"
            "<div style='margin-top:8px; font-size:14px;'>"
            "Dạng ma trận: y = Xβ, với β = (X<sup>T</sup>X)<sup>-1</sup>X<sup>T</sup>y"
            "</div>"
        )
        formula.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(formula)

        try:
            self._coef = self._solve_beta(x1, x2, y)
        except ValueError as exc:
            QMessageBox.warning(self, "Không thể giải", str(exc))
            self.reject()
            return

        b0, b1, b2 = (float(self._coef[0]), float(self._coef[1]), float(self._coef[2]))
        result = QLabel(
            "<div style='font-size:15px; margin-top:8px;'>"
            f"<b>b<sub>0</sub> = {b0:.6f}</b><br>"
            f"<b>b<sub>1</sub> = {b1:.6f}</b><br>"
            f"<b>b<sub>2</sub> = {b2:.6f}</b><br><br>"
            f"Phương trình ước lượng: <b>Ŷ = {b0:.4f} + {b1:.4f}X₁ + {b2:.4f}X₂</b>"
            "</div>"
        )
        result.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(result)

        btn = QPushButton("Áp dụng hệ số")
        btn.setStyleSheet(
            "background-color: #1F6B5D; color: #FFFFFF; padding: 8px 14px;"
            " border-radius: 10px; font-weight: 600;"
        )
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def get_coefficients(self) -> tuple[float, float, float]:
        return float(self._coef[0]), float(self._coef[1]), float(self._coef[2])


class _PredictDialog(_DialogBase):  # type: ignore[valid-type]
    """Dialog dự báo Y theo X₁, X₂ dựa trên hệ số đã fit."""

    def __init__(self, b0: float, b1: float, b2: float, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        if not _QT:
            return
        self.setWindowTitle("Dự báo từ mô hình")
        self.setMinimumSize(420, 260)
        self._b0 = b0
        self._b1 = b1
        self._b2 = b2
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        self._x1_spin = QDoubleSpinBox()
        self._x2_spin = QDoubleSpinBox()
        for spin in (self._x1_spin, self._x2_spin):
            spin.setDecimals(4)
            spin.setRange(-1_000_000, 1_000_000)
            spin.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

        grid = QGridLayout()
        grid.addWidget(QLabel("X₁:"), 0, 0)
        grid.addWidget(self._x1_spin, 0, 1)
        grid.addWidget(QLabel("X₂:"), 1, 0)
        grid.addWidget(self._x2_spin, 1, 1)
        layout.addLayout(grid)

        self._result = QLabel("Ŷ = ?")
        self._result.setStyleSheet("font-size: 15px; color: #173A5E; font-weight: 600;")
        layout.addWidget(self._result)

        btn = QPushButton("Tính dự báo")
        btn.setStyleSheet(
            "background-color: #8D571C; color: #FFFFFF; padding: 8px 14px;"
            " border-radius: 10px; font-weight: 600;"
        )
        btn.clicked.connect(self._compute)
        layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignLeft)

    def _compute(self) -> None:
        x1 = self._x1_spin.value()
        x2 = self._x2_spin.value()
        y_hat = self._b0 + self._b1 * x1 + self._b2 * x2
        self._result.setText(
            f"Ŷ = {self._b0:.4f} + {self._b1:.4f}*{x1:.4f} + {self._b2:.4f}*{x2:.4f} = {y_hat:.6f}"
        )


class _Regression3DCanvas(_CanvasBase):  # type: ignore[valid-type]
    """Canvas matplotlib 3D: scatter points + regression plane."""

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        if not _QT:
            return

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._x1: np.ndarray | None = None
        self._x2: np.ndarray | None = None
        self._y: np.ndarray | None = None
        self._coef = np.array([0.0, 0.0, 0.0], dtype=float)
        self._has_plane = False
        self._show_slice_x1 = False
        self._show_slice_x2 = False
        self._fixed_elev = 26.0

        if not _MPL:
            layout.addWidget(QLabel("matplotlib chưa được cài. Hãy cài matplotlib để hiển thị biểu đồ 3D."))
            return

        self._fig = Figure(figsize=(11.2, 7.0), dpi=100)
        self._ax = self._fig.add_subplot(111, projection="3d")
        self._canvas = FigureCanvas(self._fig)
        self._canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._canvas.setMinimumHeight(640)
        layout.addWidget(self._canvas)
        self._canvas.mpl_connect("motion_notify_event", self._on_mouse_motion_lock_vertical)
        self._redraw()

    def _on_mouse_motion_lock_vertical(self, event) -> None:
        """Keep elevation fixed so user rotation only changes left-right azimuth."""
        if event.inaxes is not self._ax:
            return
        if event.button != 1:
            return
        if abs(self._ax.elev - self._fixed_elev) > 1e-9:
            self._ax.view_init(elev=self._fixed_elev, azim=self._ax.azim)
            self._canvas.draw_idle()

    def set_slice_visibility(self, show_slice_x1: bool, show_slice_x2: bool) -> None:
        """Toggle optional slice lines and redraw the 3D scene."""
        self._show_slice_x1 = show_slice_x1
        self._show_slice_x2 = show_slice_x2
        self._redraw()

    def set_data(self, x1: np.ndarray, x2: np.ndarray, y: np.ndarray) -> None:
        self._x1 = x1
        self._x2 = x2
        self._y = y
        self._redraw()

    def set_plane_coefficients(self, b0: float, b1: float, b2: float) -> None:
        self._coef = np.array([b0, b1, b2], dtype=float)
        self._has_plane = True
        self._redraw()

    def get_coefficients(self) -> tuple[float, float, float]:
        return float(self._coef[0]), float(self._coef[1]), float(self._coef[2])

    def get_y_hat(self) -> np.ndarray | None:
        if self._x1 is None or self._x2 is None or not self._has_plane:
            return None
        b0, b1, b2 = self._coef
        return b0 + b1 * self._x1 + b2 * self._x2

    def _redraw(self) -> None:
        if not _MPL:
            return

        ax = self._ax
        ax.clear()
        ax.set_facecolor("#FBF9F4")

        ax.set_xlabel("X₁")
        ax.set_ylabel("X₂")
        ax.set_zlabel("Y")
        ax.set_title("Mô phỏng hồi quy tuyến tính bội (3D)")

        if self._x1 is not None and self._x2 is not None and self._y is not None:
            ax.scatter(
                self._x1,
                self._x2,
                self._y,
                color="#173A5E",
                s=40,
                alpha=0.95,
                depthshade=True,
                label="Quan sát",
            )

            if self._has_plane:
                b0, b1, b2 = self._coef
                gx1 = np.linspace(float(np.min(self._x1)), float(np.max(self._x1)), 18)
                gx2 = np.linspace(float(np.min(self._x2)), float(np.max(self._x2)), 18)
                xx1, xx2 = np.meshgrid(gx1, gx2)
                yy = b0 + b1 * xx1 + b2 * xx2
                ax.plot_surface(xx1, xx2, yy, color="#1F6B5D", alpha=0.35, linewidth=0.0)

                # Draw a single representative trend line on the fitted plane.
                # Direction is taken from the first principal component in (X1, X2)
                # so the line follows the dominant spread of observed predictors.
                x_stack = np.column_stack([self._x1, self._x2])
                x_center = np.mean(x_stack, axis=0)
                centered = x_stack - x_center
                _u, _s, vh = np.linalg.svd(centered, full_matrices=False)
                direction = vh[0]
                proj = centered @ direction
                t_vals = np.linspace(float(np.min(proj)), float(np.max(proj)), 80)
                line_x1 = x_center[0] + t_vals * direction[0]
                line_x2 = x_center[1] + t_vals * direction[1]
                line_y = b0 + b1 * line_x1 + b2 * line_x2
                ax.plot(
                    line_x1,
                    line_x2,
                    line_y,
                    color="#D62728",
                    linewidth=3.2,
                    linestyle="-",
                    alpha=0.98,
                    zorder=12,
                    label="Đường xu hướng chính",
                )

                x1_mean = float(np.mean(self._x1))
                x2_mean = float(np.mean(self._x2))
                if self._show_slice_x1:
                    slice_x1 = np.linspace(float(np.min(self._x1)), float(np.max(self._x1)), 80)
                    slice_x2 = np.full_like(slice_x1, x2_mean)
                    slice_y_x1 = b0 + b1 * slice_x1 + b2 * slice_x2
                    ax.plot(
                        slice_x1,
                        slice_x2,
                        slice_y_x1,
                        color="#1E88E5",
                        linewidth=2.6,
                        linestyle=(0, (7, 4)),
                        alpha=0.98,
                        zorder=11,
                        label="Lát cắt theo X₁ (X₂ = X̄₂)",
                    )

                if self._show_slice_x2:
                    slice_x2 = np.linspace(float(np.min(self._x2)), float(np.max(self._x2)), 80)
                    slice_x1 = np.full_like(slice_x2, x1_mean)
                    slice_y_x2 = b0 + b1 * slice_x1 + b2 * slice_x2
                    ax.plot(
                        slice_x1,
                        slice_x2,
                        slice_y_x2,
                        color="#2E7D32",
                        linewidth=2.6,
                        linestyle=(0, (3, 3)),
                        alpha=0.98,
                        zorder=11,
                        label="Lát cắt theo X₂ (X₁ = X̄₁)",
                    )

                y_hat = b0 + b1 * self._x1 + b2 * self._x2
                for i in range(len(self._y)):
                    ax.plot(
                        [self._x1[i], self._x1[i]],
                        [self._x2[i], self._x2[i]],
                        [self._y[i], y_hat[i]],
                        color="#B0413E",
                        linewidth=1.0,
                        alpha=0.85,
                    )

                ax.legend(loc="upper left", fontsize=8)

        ax.grid(True, alpha=0.25)
        ax.set_box_aspect((1.25, 1.2, 0.8))
        # Camera tuned so Y (vertical axis in this chart) stays upright and
        # the fitted plane + optional slice lines are visible from first render.
        ax.view_init(elev=self._fixed_elev, azim=-128)
        self._fig.tight_layout()
        self._canvas.draw_idle()

    def export_png(self) -> bytes:
        if not _MPL:
            return b""
        buf = io.BytesIO()
        self._fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
        return buf.getvalue()


class _ComputationTable(QTableWidget):  # type: ignore[valid-type]
    """Bảng tính Y, Ŷ, phần dư và bình phương phần dư."""

    def __init__(self, parent: "QWidget | None" = None) -> None:
        super().__init__(parent)
        self._build_ui()

    def _build_ui(self) -> None:
        self.setColumnCount(8)
        self.setHorizontalHeaderLabels([
            "i",
            "X₁",
            "X₂",
            "Y",
            "Ŷ",
            "e = Y - Ŷ",
            "e²",
            "Σeᵢ² lũy kế",
        ])
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

    @staticmethod
    def _cell(text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item

    def update_data(
        self,
        x1: np.ndarray | None,
        x2: np.ndarray | None,
        y: np.ndarray | None,
        y_hat: np.ndarray | None,
    ) -> None:
        if x1 is None or x2 is None or y is None:
            self.setRowCount(0)
            return

        n = len(y)
        self.setRowCount(n + 1)
        sse_sum = 0.0

        for i in range(n):
            yi = float(y[i])
            yhi = float(y_hat[i]) if y_hat is not None else 0.0
            err = yi - yhi if y_hat is not None else 0.0
            err2 = err * err if y_hat is not None else 0.0
            sse_sum += err2

            vals = [
                str(i + 1),
                f"{float(x1[i]):.4f}",
                f"{float(x2[i]):.4f}",
                f"{yi:.4f}",
                f"{yhi:.4f}" if y_hat is not None else "-",
                f"{err:.4f}" if y_hat is not None else "-",
                f"{err2:.4f}" if y_hat is not None else "-",
                f"{sse_sum:.4f}" if y_hat is not None else "-",
            ]
            for c, val in enumerate(vals):
                self.setItem(i, c, self._cell(val))

        footer = ["Tổng", "", "", "", "", "", "", f"{sse_sum:.4f}" if y_hat is not None else "-"]
        for c, val in enumerate(footer):
            item = self._cell(val)
            if c == 0 or c == 7:
                f = item.font()
                f.setBold(True)
                item.setFont(f)
            self.setItem(n, c, item)


class _MultipleLinearRegressionView(_WidgetBase):  # type: ignore[valid-type]
    """Root widget cho module hồi quy tuyến tính bội 2 biến X."""

    def __init__(self) -> None:
        super().__init__()
        if not _QT:
            return

        self._x1: np.ndarray | None = None
        self._x2: np.ndarray | None = None
        self._y: np.ndarray | None = None

        self._build_ui()
        self._connect_signals()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        page_scroll = QScrollArea()
        page_scroll.setWidgetResizable(True)
        page_scroll.setFrameShape(QFrame.Shape.NoFrame)
        root.addWidget(page_scroll)

        content = QWidget()
        page_scroll.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 16, 16, 16)
        content_layout.setSpacing(12)

        title = QLabel("Hồi quy tuyến tính bội với 2 biến độc lập (3D)")
        title.setStyleSheet("font-size: 20px; font-weight: 700; color: #173A5E;")
        content_layout.addWidget(title)

        subtitle = QLabel(
            "Mô hình: Ŷ = b₀ + b₁X₁ + b₂X₂. "
            "Nhập dữ liệu, dựng mặt phẳng hồi quy, quan sát phần dư trên biểu đồ 3D."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #22313D;")
        content_layout.addWidget(subtitle)

        toolbar = QFrame()
        toolbar.setStyleSheet(
            "QFrame {background: #ECE6DB; border: 1px solid #D8D0C4; border-radius: 10px;}"
        )
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(10, 8, 10, 8)
        tb.setSpacing(8)

        self._btn_input = QPushButton("Nhập dữ liệu")
        self._btn_input.setStyleSheet(
            "background-color: #8D571C; color: #FFFFFF; padding: 8px 14px;"
            " border-radius: 10px; font-weight: 600;"
        )
        tb.addWidget(self._btn_input)

        self._btn_add_plane = QPushButton("Thêm mặt phẳng xu hướng")
        self._btn_add_plane.setEnabled(False)
        self._btn_add_plane.setStyleSheet(
            "background-color: #173A5E; color: #FFFFFF; padding: 8px 14px;"
            " border-radius: 10px; font-weight: 600;"
        )
        tb.addWidget(self._btn_add_plane)

        self._btn_solve = QPushButton("Giải OLS")
        self._btn_solve.setEnabled(False)
        self._btn_solve.setStyleSheet(
            "background-color: #1F6B5D; color: #FFFFFF; padding: 8px 14px;"
            " border-radius: 10px; font-weight: 600;"
        )
        tb.addWidget(self._btn_solve)

        self._btn_predict = QPushButton("Dự báo")
        self._btn_predict.setEnabled(False)
        self._btn_predict.setStyleSheet(
            "background-color: #2C618D; color: #FFFFFF; padding: 8px 14px;"
            " border-radius: 10px; font-weight: 600;"
        )
        tb.addWidget(self._btn_predict)

        self._cb_slice_x1 = QCheckBox("Lát cắt X₁ (X₂ = X̄₂)")
        self._cb_slice_x1.setChecked(False)
        tb.addWidget(self._cb_slice_x1)

        self._cb_slice_x2 = QCheckBox("Lát cắt X₂ (X₁ = X̄₁)")
        self._cb_slice_x2.setChecked(False)
        tb.addWidget(self._cb_slice_x2)

        tb.addStretch()
        content_layout.addWidget(toolbar)

        self._metrics_panel = QLabel()
        self._metrics_panel.setTextFormat(Qt.TextFormat.RichText)
        self._metrics_panel.setStyleSheet(
            "background: #F6F2EA; border: 1px solid #D8D0C4; border-radius: 10px;"
            " padding: 8px 12px; color: #22313D;"
        )
        content_layout.addWidget(self._metrics_panel)
        self._set_metrics_placeholder()

        self._canvas = _Regression3DCanvas()
        content_layout.addWidget(self._canvas)

        self._comp_table = _ComputationTable()
        self._comp_table.setMinimumHeight(360)
        content_layout.addWidget(self._comp_table)

    def _connect_signals(self) -> None:
        self._btn_input.clicked.connect(self._on_input_data)
        self._btn_add_plane.clicked.connect(self._on_add_plane)
        self._btn_solve.clicked.connect(self._on_solve)
        self._btn_predict.clicked.connect(self._on_predict)
        self._cb_slice_x1.toggled.connect(self._on_slice_toggled)
        self._cb_slice_x2.toggled.connect(self._on_slice_toggled)

    def _on_slice_toggled(self) -> None:
        self._canvas.set_slice_visibility(
            self._cb_slice_x1.isChecked(),
            self._cb_slice_x2.isChecked(),
        )

    def _on_input_data(self) -> None:
        old_x1 = self._x1.tolist() if self._x1 is not None else []
        old_x2 = self._x2.tolist() if self._x2 is not None else []
        old_y = self._y.tolist() if self._y is not None else []

        dlg = _DataInputDialog(old_x1, old_x2, old_y, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        x1, x2, y = dlg.get_data()
        self._x1 = np.array(x1, dtype=float)
        self._x2 = np.array(x2, dtype=float)
        self._y = np.array(y, dtype=float)

        self._canvas.set_data(self._x1, self._x2, self._y)
        self._comp_table.update_data(self._x1, self._x2, self._y, y_hat=None)

        self._btn_add_plane.setEnabled(True)
        self._btn_solve.setEnabled(True)
        self._btn_predict.setEnabled(False)
        self._set_metrics_placeholder()

    def _on_add_plane(self) -> None:
        if self._x1 is None or self._x2 is None or self._y is None:
            return
        try:
            beta = _solve_ols_two_predictors(self._x1, self._x2, self._y)
        except ValueError as exc:
            QMessageBox.warning(self, "Không thể tạo mặt phẳng", str(exc))
            return

        self._canvas.set_plane_coefficients(float(beta[0]), float(beta[1]), float(beta[2]))
        self._refresh_table()
        self._btn_predict.setEnabled(True)

    def _on_solve(self) -> None:
        if self._x1 is None or self._x2 is None or self._y is None:
            return

        dlg = _SolveDialog(self._x1, self._x2, self._y, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        b0, b1, b2 = dlg.get_coefficients()
        self._canvas.set_plane_coefficients(b0, b1, b2)
        self._refresh_table()
        self._btn_predict.setEnabled(True)

    def _on_predict(self) -> None:
        b0, b1, b2 = self._canvas.get_coefficients()
        dlg = _PredictDialog(b0, b1, b2, self)
        dlg.exec()

    def _set_metrics_placeholder(self) -> None:
        self._metrics_panel.setText(
            "<b>Độ phù hợp mô hình:</b> "
            "R<sup>2</sup> = <b>—</b>; Adjusted R<sup>2</sup> = <b>—</b>; "
            "SSE = <b>—</b>"
        )

    def _update_metrics_panel(self, y_hat: np.ndarray | None) -> None:
        if self._y is None or y_hat is None:
            self._set_metrics_placeholder()
            return
        sse, _sst, r2, adj_r2 = _regression_metrics(self._y, y_hat, predictor_count=2)
        self._metrics_panel.setText(
            "<b>Độ phù hợp mô hình:</b> "
            f"R<sup>2</sup> = <b>{r2:.6f}</b>; "
            f"Adjusted R<sup>2</sup> = <b>{adj_r2:.6f}</b>; "
            f"SSE = <b>{sse:.6f}</b>"
        )

    def _refresh_table(self) -> None:
        y_hat = self._canvas.get_y_hat()
        self._comp_table.update_data(
            self._x1,
            self._x2,
            self._y,
            y_hat=y_hat,
        )
        self._update_metrics_panel(y_hat)

    def get_state(self) -> dict:
        state: dict[str, Any] = {}
        if self._x1 is not None and self._x2 is not None and self._y is not None:
            state["x1"] = self._x1.tolist()
            state["x2"] = self._x2.tolist()
            state["y"] = self._y.tolist()

        b0, b1, b2 = self._canvas.get_coefficients()
        state["b0"] = b0
        state["b1"] = b1
        state["b2"] = b2
        state["has_plane"] = self._canvas._has_plane
        return state

    def restore_state(self, state: dict) -> None:
        if "x1" not in state or "x2" not in state or "y" not in state:
            return

        try:
            self._x1 = np.array(state.get("x1", []), dtype=float)
            self._x2 = np.array(state.get("x2", []), dtype=float)
            self._y = np.array(state.get("y", []), dtype=float)
        except (TypeError, ValueError):
            return

        if len(self._x1) != len(self._x2) or len(self._x1) != len(self._y) or len(self._y) < 3:
            return

        self._canvas.set_data(self._x1, self._x2, self._y)
        self._btn_add_plane.setEnabled(True)
        self._btn_solve.setEnabled(True)

        if state.get("has_plane", False):
            b0 = float(state.get("b0", 0.0))
            b1 = float(state.get("b1", 0.0))
            b2 = float(state.get("b2", 0.0))
            self._canvas.set_plane_coefficients(b0, b1, b2)
            self._btn_predict.setEnabled(True)

        self._refresh_table()

    def export_png(self) -> bytes:
        return self._canvas.export_png()


class MultipleLinearRegression3DModule(BaseModule):
    """IIMP module: Hồi quy tuyến tính bội với 2 biến độc lập và biểu đồ 3D."""

    def __init__(self, manifest: dict, context: ModuleContext) -> None:
        super().__init__(manifest, context)
        self._view: _MultipleLinearRegressionView | None = None

    def on_load(self) -> None:
        """Khởi tạo resource nhẹ và ghi log lifecycle."""
        self.context.logger.info("MultipleLinearRegression3DModule loaded.")

    def build_view(self) -> QWidget:
        """Trả về root widget duy nhất của module cho shell host."""
        self._view = _MultipleLinearRegressionView()
        return self._view

    def on_activate(self) -> None:
        """Lifecycle hook khi module được đưa vào workspace."""
        self.context.logger.info("MultipleLinearRegression3DModule activated.")

    def on_deactivate(self) -> None:
        """Lifecycle hook khi module mất focus."""
        self.context.logger.info("MultipleLinearRegression3DModule deactivated.")

    def on_unload(self) -> None:
        """Giải phóng tham chiếu UI trước khi module bị giải phóng."""
        self._view = None
        self.context.logger.info("MultipleLinearRegression3DModule unloaded.")

    def get_state(self) -> dict:
        """Trả về state JSON-serializable gồm dữ liệu và hệ số mô hình."""
        if self._view is None:
            return {}
        state = self._view.get_state()
        state["_state_version"] = self.manifest.get("data_contract_version", "1.0.0")
        return state

    def restore_state(self, state: dict) -> None:
        """Phục hồi state theo best-effort, bỏ qua state không hợp lệ."""
        if self._view is not None and state:
            self._view.restore_state(state)

    def export(self, target_path: str, export_type: str = "default") -> None:
        """Export hình biểu đồ 3D hiện tại ra file PNG."""
        if self._view is None:
            raise RuntimeError("No view to export.")
        data = self._view.export_png()
        with open(target_path, "wb") as f:
            f.write(data)
        self.context.logger.info(f"Exported 3D regression chart to {target_path}")
