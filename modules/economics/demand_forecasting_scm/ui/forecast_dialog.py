"""ForecastDialog — hiển thị kết quả dự báo với animation QTimer.

Mỗi tick 80ms vẽ thêm 1 điểm F_t lên chart.
Có phần hold-out metrics nếu n_train < n_total.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..models.inputs import DataSet
from ..models.outputs import ForecastResult

_ANIMATION_INTERVAL_MS = 80
_COLOR_YT = "#1f77b4"
_COLOR_FT_TRAIN = "#d62728"
_COLOR_FT_HOLDOUT = "#ff7f0e"


class ForecastDialog(QDialog):
    """Hiển thị biểu đồ dự báo F_t với animation từng điểm.

    Args:
        result:    Kết quả dự báo.
        dataset:   Tập dữ liệu gốc.
        n_train:   Số kỳ huấn luyện (để phân chia hold-out).
        parent:    Widget cha.
    """

    def __init__(
        self,
        result: ForecastResult,
        dataset: DataSet,
        n_train: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._result = result
        self._dataset = dataset
        self._n_train = n_train
        self._anim_step = 0
        self._timer = QTimer(self)
        self._timer.setInterval(_ANIMATION_INTERVAL_MS)
        self._timer.timeout.connect(self._animation_tick)

        self.setWindowTitle(f"Kết quả dự báo — {result.method.upper()}")
        self.setModal(True)
        self.setMinimumSize(680, 480)
        self.setStyleSheet("font-size: 12px;")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint  # type: ignore[operator]
        )
        self._build_ui()
        self._init_chart()
        self._timer.start()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)

        # Chart
        self._fig, self._ax = plt.subplots(figsize=(9, 4))
        self._canvas = FigureCanvasQTAgg(self._fig)
        self._canvas.setMinimumHeight(280)
        root.addWidget(self._canvas)

        # Hold-out metrics group (hiện nếu có hold-out)
        if self._result.holdout_metrics is not None:
            m = self._result.holdout_metrics
            self._holdout_group = QGroupBox("Hold-out Validation")
            form = QFormLayout(self._holdout_group)
            form.addRow("MAE:", QLabel(f"{m.mae:.4f}"))
            form.addRow("RMSE:", QLabel(f"{m.rmse:.4f}"))
            mape_txt = f"{m.mape:.2f} %" if m.mape is not None else "N/A (có Y_t = 0)"
            form.addRow("MAPE:", QLabel(mape_txt))
            bias_txt = f"{m.bias:.4f}  ({m.bias_pct:.2f} %)" if m.bias_pct is not None else f"{m.bias:.4f}"
            form.addRow("Bias:", QLabel(bias_txt))
            root.addWidget(self._holdout_group)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_close = QPushButton("Đóng")
        btn_close.setFixedWidth(80)
        btn_close.clicked.connect(self._on_close)
        btn_row.addWidget(btn_close)
        root.addLayout(btn_row)

    def _init_chart(self) -> None:
        ax = self._ax
        t_all = [p.t for p in self._dataset.points]
        y_all = [p.y for p in self._dataset.points]

        ax.clear()
        ax.plot(t_all, y_all, color=_COLOR_YT, linewidth=1.5,
                marker="o", markersize=3, label=r"$Y_t$ (thực tế)")

        # Vùng hold-out
        if self._n_train < len(t_all):
            holdout_t = t_all[self._n_train]
            ax.axvspan(
                holdout_t - 0.5, t_all[-1] + 0.5,
                alpha=0.08, color="#9467bd", label="Hold-out"
            )
            ax.axvline(holdout_t - 0.5, color="#9467bd", linestyle=":", linewidth=1.0)

        ax.set_title(f"Dự báo — {self._result.method.upper()}", fontsize=10)
        ax.set_xlabel("Kỳ (t)", fontsize=9)
        ax.set_ylabel("Nhu cầu", fontsize=9)
        ax.legend(fontsize=8)
        ax.grid(True, linestyle="--", alpha=0.4)
        self._fig.tight_layout()
        self._canvas.draw()

    # ------------------------------------------------------------------
    # Animation
    # ------------------------------------------------------------------

    def _animation_tick(self) -> None:
        """Vẽ thêm 1 điểm F_t mỗi tick."""
        rows = self._result.detail_rows
        # Tìm điểm hợp lệ tiếp theo (bỏ qua None)
        valid_indices = [i for i, r in enumerate(rows) if r.f_t is not None]
        if self._anim_step >= len(valid_indices):
            self._timer.stop()
            return

        # Vẽ tất cả điểm cho đến step hiện tại
        to_draw = valid_indices[: self._anim_step + 1]
        ax = self._ax

        # Xóa các đường F_t cũ trước khi vẽ lại
        for line in list(ax.lines):
            if getattr(line, "_is_ft_line", False):
                line.remove()

        # Tách train / holdout portion
        train_t = [rows[i].t for i in to_draw if rows[i].t <= self._n_train + self._dataset.points[0].t - 1]
        train_f = [rows[i].f_t for i in to_draw if rows[i].t <= self._n_train + self._dataset.points[0].t - 1]
        hold_t  = [rows[i].t for i in to_draw if rows[i].t > self._n_train + self._dataset.points[0].t - 1]
        hold_f  = [rows[i].f_t for i in to_draw if rows[i].t > self._n_train + self._dataset.points[0].t - 1]

        # Tính ngưỡng kỳ đơn giản hơn dựa trên n_train
        cutoff_t = self._dataset.points[0].t + self._n_train - 1

        train_t_list = [rows[i].t for i in to_draw if rows[i].t <= cutoff_t]
        train_f_list = [rows[i].f_t for i in to_draw if rows[i].t <= cutoff_t]
        hold_t_list  = [rows[i].t for i in to_draw if rows[i].t > cutoff_t]
        hold_f_list  = [rows[i].f_t for i in to_draw if rows[i].t > cutoff_t]

        if train_t_list:
            line, = ax.plot(train_t_list, train_f_list, color=_COLOR_FT_TRAIN,
                            linewidth=1.5, linestyle="--", marker="s", markersize=3,
                            label=r"$F_t$ (huấn luyện)")
            line._is_ft_line = True  # type: ignore[attr-defined]

        if hold_t_list:
            line, = ax.plot(hold_t_list, hold_f_list, color=_COLOR_FT_HOLDOUT,
                            linewidth=1.5, linestyle="--", marker="s", markersize=3,
                            label=r"$F_t$ (hold-out)")
            line._is_ft_line = True  # type: ignore[attr-defined]

        # Cập nhật legend chỉ lần đầu có đường mới
        ax.legend(fontsize=9)
        self._canvas.draw()
        self._anim_step += 1

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        self._timer.stop()
        self.accept()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._timer.stop()
        super().closeEvent(event)
