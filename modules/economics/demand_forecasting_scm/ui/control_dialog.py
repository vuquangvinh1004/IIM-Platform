"""ControlDialog — Tín hiệu theo dõi + Biểu đồ kiểm soát song song.

Modal dialog mở từ nút "Kiểm soát" trong MethodView.
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure as _Figure

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from ..models.outputs import ForecastResult
from ..services.error_metrics import compute_control_bands, compute_tracking_signal


class ControlDialog(QDialog):
    """Hiển thị Tín hiệu theo dõi và Biểu đồ kiểm soát sai số.

    Args:
        result:       Kết quả dự báo.
        ts_threshold: Ngưỡng Tracking Signal (±).
        parent:       Widget cha.
    """

    def __init__(
        self,
        result: ForecastResult,
        ts_threshold: float = 4.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._result = result
        self._ts_threshold = ts_threshold

        self.setWindowTitle(f"Kiểm soát — {result.method.upper()}")
        self.setModal(True)
        self.setMinimumSize(860, 580)
        self.setStyleSheet("font-size: 12px;")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint  # type: ignore[operator]
        )
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(10)

        # Header info
        root.addWidget(
            QLabel(
                f"<b>Phương pháp:</b> {self._result.method.upper()}   "
                f"<b>Ngưỡng TS:</b> ±{self._ts_threshold}"
            )
        )

        t_values = [row.t for row in self._result.detail_rows]
        e_values = self._result.e_values
        y_all = [row.y_t for row in self._result.detail_rows]
        f_all = self._result.f_values
        ts_values = compute_tracking_signal(y_all, f_all)
        bands = compute_control_bands(e_values)

        # Hai biểu đồ cùng trục x — dùng Figure trực tiếp (không qua pyplot)
        fig = _Figure(figsize=(9, 7))
        ax_ts = fig.add_subplot(2, 1, 1)
        ax_ctrl = fig.add_subplot(2, 1, 2, sharex=ax_ts)

        # --- Subplot trên: Tín hiệu theo dõi ---
        valid_ts = [(t, v) for t, v in zip(t_values, ts_values) if v is not None]
        if valid_ts:
            ts_t, ts_v = zip(*valid_ts)
            ax_ts.plot(ts_t, ts_v, color="#1f2eb4", marker="o", markersize=4,
                       linewidth=1.5, label="TS")
            ax_ts.axhline(self._ts_threshold,  color="#d62728", linestyle="--",
                          linewidth=1.2, label=f"\u00b1{self._ts_threshold}")
            ax_ts.axhline(-self._ts_threshold, color="#d62728", linestyle="--",
                          linewidth=1.2, label="_nolegend_")
            ax_ts.axhline(0, color="gray", linewidth=0.8, label="_nolegend_")
        ax_ts.set_ylabel("TS", fontsize=9)
        ax_ts.set_title(
            f"Tín hiệu theo dõi (TS) — {self._result.method.upper()}", fontsize=10
        )
        ax_ts.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
                     borderaxespad=0, fontsize=8)
        ax_ts.grid(True, linestyle="--", alpha=0.4)

        # --- Subplot dưới: Biểu đồ kiểm soát sai số ---
        valid_e = [(t, e) for t, e in zip(t_values, e_values) if e is not None]
        if valid_e:
            e_t, e_v = zip(*valid_e)
            # xanh (e_t > 0) / đỏ (e_t < 0)
            colors = ["#d62728" if v < 0 else "#47b41f" for v in e_v]
            ax_ctrl.bar(e_t, e_v, color=colors, alpha=0.75, width=0.6)
            ax_ctrl.axhline(0, color="black", linewidth=0.8, label="_nolegend_")
            if bands:
                # bands: {1.0: 1σ, 2.0: 2σ, 3.0: 3σ}
                _BAND_STYLES = {
                    3.0: ("#2ca02c", "--", "3σ"),
                    2.0: ("#ff7f0e", ":",  "2σ"),
                    1.0: ("#aec7e8", ":",  "1σ"),
                }
                for sigma, (color, ls, lbl) in _BAND_STYLES.items():
                    val = bands.get(sigma)
                    if val is not None and val > 0:
                        # Chỉ hiển thị một mục legend cho cả hai đường ±
                        ax_ctrl.axhline( val, color=color, linestyle=ls,
                                         linewidth=1.2, label=f"±{lbl} = ±{val:.1f}")
                        ax_ctrl.axhline(-val, color=color, linestyle=ls,
                                         linewidth=1.2, label="_nolegend_")
        ax_ctrl.set_xlabel("t", fontsize=9)
        ax_ctrl.set_ylabel(r"$e_t$", fontsize=9)
        ax_ctrl.set_title(
            f"Biểu đồ kiểm soát sai số — {self._result.method.upper()}", fontsize=10
        )
        ax_ctrl.legend(loc="upper left", bbox_to_anchor=(1.01, 1.0),
                       borderaxespad=0, fontsize=8)
        ax_ctrl.grid(True, linestyle="--", alpha=0.4, axis="y")

        # Chừa khoảng bên phải cho legend (không dùng tight_layout để tránh xung đột)
        fig.subplots_adjust(left=0.08, right=0.74, top=0.93, bottom=0.08, hspace=0.40)
        canvas = FigureCanvasQTAgg(fig)
        root.addWidget(canvas)

        # Close button
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn = QPushButton("Đóng")
        btn.setFixedWidth(80)
        btn.clicked.connect(self.accept)
        btn_row.addWidget(btn)
        root.addLayout(btn_row)
