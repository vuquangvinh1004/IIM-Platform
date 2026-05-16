"""MethodView — widget dùng chung cho mỗi phương pháp dự báo.

Bố cục:
- Trên: QSplitter [chart Yt+Ft | controls + metrics]
- Dưới: QSplitter [chart et | bảng chi tiết]

Realtime: thay đổi tham số → _recalculate() → cập nhật ngay.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QDialog,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import matplotlib
matplotlib.use("Agg")

from ..models.inputs import DataSet, ForecastingInput
from ..models.outputs import ForecastResult
from ..services.forecasting_engine import run as engine_run
from ..services.chart_builder import build_error_chart, build_forecast_chart

_RECALC_DELAY_MS = 200   # debounce: chờ 200ms sau khi user ngừng kéo slider

# Biểu thức công thức mô hình — hiển thị nổi bật trước tham số
_METHOD_FORMULA: dict[str, str] = {
    "naive":             "F̂<sub>t+1</sub> = Y<sub>t</sub>",
    "moving_average":    "F̂<sub>t+1</sub> = (Y<sub>t</sub> + Y<sub>t−1</sub> + ⋯ + Y<sub>t−k+1</sub>) / k",
    "ses":               "F̂<sub>t+1</sub> = α·Y<sub>t</sub> + (1−α)·F̂<sub>t</sub>",
    "linear_regression": "Ŷ<sub>t</sub> = a + b·t",
    "holt":              "Ŷ<sub>t+h</sub> = L<sub>t</sub> + h·T<sub>t</sub>",
}


class MethodView(QWidget):
    """Widget dùng chung cho một phương pháp dự báo cụ thể.

    Args:
        method_name: "naive" | "moving_average" | "ses" | "linear_regression" | "holt"
        dataset:     DataSet hiện tại.
        ts_threshold: Ngưỡng TS cho ControlDialog.
        benchmark:   Tên benchmark cho FVA.
        parent:      Widget cha.
    """

    def __init__(
        self,
        method_name: str,
        dataset: DataSet,
        ts_threshold: float = 4.0,
        benchmark: str = "naive",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._method = method_name
        self._dataset = dataset
        self._ts_threshold = ts_threshold
        self._benchmark = benchmark
        self._result: ForecastResult | None = None
        # Trạng thái: người dùng đã bấm "Dự báo" hay chưa
        self._forecast_shown: bool = False

        # Debounce timer để tránh tính toán liên tục khi kéo slider
        self._recalc_timer = QTimer(self)
        self._recalc_timer.setSingleShot(True)
        self._recalc_timer.setInterval(_RECALC_DELAY_MS)
        self._recalc_timer.timeout.connect(self._recalculate)

        self._build_ui()
        # Tính toán ngầm lần đầu (chưa hiển thị kết quả)
        self._recalculate_silent()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 6, 8, 6)
        root.setSpacing(6)

        from matplotlib.figure import Figure as _Figure  # noqa: PLC0415

        # === Main horizontal splitter: đồ thị (60%) | điều khiển+bảng (40%) ===
        # Hai đồ thị ở cùng một cột → cạnh trái/phải tự động thẳng hàng.
        self._main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- Cột trái: hai đồ thị xếp dọc ---
        self._chart_splitter = QSplitter(Qt.Orientation.Vertical)

        self._forecast_fig = _Figure(figsize=(7, 3.5))
        self._forecast_canvas = FigureCanvasQTAgg(self._forecast_fig)
        self._chart_splitter.addWidget(self._forecast_canvas)

        self._error_fig = _Figure(figsize=(7, 3.0))
        self._error_canvas = FigureCanvasQTAgg(self._error_fig)
        self._error_canvas.setVisible(False)   # ẩn cho đến khi bấm "Dự báo"
        self._chart_splitter.addWidget(self._error_canvas)
        self._chart_splitter.setStretchFactor(0, 1)
        self._chart_splitter.setStretchFactor(1, 1)

        self._main_splitter.addWidget(self._chart_splitter)

        # --- Cột phải: điều khiển (trên) + bảng chi tiết (dưới) ---
        right_widget = QWidget()
        right_widget.setMinimumWidth(460)     # đảm bảo đủ chỗ cho 7 cột bảng
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(6, 0, 0, 0)
        right_layout.setSpacing(6)

        controls = self._build_controls()
        controls.setMinimumWidth(220)
        right_layout.addWidget(controls, stretch=0)

        self._table = self._build_detail_table()
        self._table.setVisible(False)          # ẩn cho đến khi bấm "Dự báo"
        right_layout.addWidget(self._table, stretch=1)

        self._main_splitter.addWidget(right_widget)
        self._main_splitter.setStretchFactor(0, 3)   # đồ thị ~60%
        self._main_splitter.setStretchFactor(1, 2)   # bảng+điều khiển ~40%

        root.addWidget(self._main_splitter)

    def _build_controls(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # --- Tảm số nhóm ---
        param_group = QGroupBox("Tham số")
        param_layout = QVBoxLayout(param_group)
        param_layout.setContentsMargins(8, 6, 8, 6)
        param_layout.setSpacing(4)

        # Biểu thức mô hình (in đậm, màu đỏ)
        formula_html = _METHOD_FORMULA.get(self._method, "")
        if formula_html:
            formula_lbl = QLabel(
                f'<span style="font-weight:bold; color:#c0392b; font-size:12px;">{formula_html}</span>'
            )
            formula_lbl.setTextFormat(Qt.TextFormat.RichText)
            formula_lbl.setWordWrap(True)
            formula_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            param_layout.addWidget(formula_lbl)

        param_form = QFormLayout()
        param_form.setSpacing(6)
        param_layout.addLayout(param_form)

        # Số kỳ phân tích (n_train) — slider + spinbox linked
        n = self._dataset.n
        self._n_train_slider = QSlider(Qt.Orientation.Horizontal)
        self._n_train_slider.setRange(2, n)
        self._n_train_slider.setValue(n)
        self._n_train_spinbox = QSpinBox()
        self._n_train_spinbox.setRange(2, n)
        self._n_train_spinbox.setValue(n)
        self._n_train_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._n_train_slider.valueChanged.connect(self._n_train_spinbox.setValue)
        self._n_train_spinbox.valueChanged.connect(self._n_train_slider.setValue)
        self._n_train_slider.valueChanged.connect(self._schedule_recalc)

        n_row = QHBoxLayout()
        n_row.addWidget(self._n_train_slider)
        n_row.addWidget(self._n_train_spinbox)
        param_form.addRow("Số kỳ phân tích:", n_row)

        # Tham số riêng
        self._alpha_spinbox: QDoubleSpinBox | None = None
        self._beta_spinbox: QDoubleSpinBox | None = None
        self._k_spinbox: QSpinBox | None = None

        if self._method == "moving_average":
            self._k_spinbox = QSpinBox()
            self._k_spinbox.setRange(1, min(20, n - 1) if n > 1 else 1)
            self._k_spinbox.setValue(3)
            self._k_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self._k_spinbox.valueChanged.connect(self._schedule_recalc)
            param_form.addRow("k (số kỳ):", self._k_spinbox)

        elif self._method == "ses":
            self._alpha_spinbox = QDoubleSpinBox()
            self._alpha_spinbox.setRange(0.01, 1.0)
            self._alpha_spinbox.setSingleStep(0.05)
            self._alpha_spinbox.setValue(0.3)
            self._alpha_spinbox.setDecimals(2)
            self._alpha_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self._alpha_spinbox.valueChanged.connect(self._schedule_recalc)
            param_form.addRow("α (mức độ):", self._alpha_spinbox)

        elif self._method == "holt":
            self._alpha_spinbox = QDoubleSpinBox()
            self._alpha_spinbox.setRange(0.01, 1.0)
            self._alpha_spinbox.setSingleStep(0.05)
            self._alpha_spinbox.setValue(0.3)
            self._alpha_spinbox.setDecimals(2)
            self._alpha_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self._alpha_spinbox.valueChanged.connect(self._schedule_recalc)
            param_form.addRow("α (mức độ):", self._alpha_spinbox)

            self._beta_spinbox = QDoubleSpinBox()
            self._beta_spinbox.setRange(0.01, 1.0)
            self._beta_spinbox.setSingleStep(0.05)
            self._beta_spinbox.setValue(0.1)
            self._beta_spinbox.setDecimals(2)
            self._beta_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self._beta_spinbox.valueChanged.connect(self._schedule_recalc)
            param_form.addRow("β (xu hướng):", self._beta_spinbox)

        layout.addWidget(param_group)

        # --- Action buttons ---
        self._btn_forecast = QPushButton("Dự báo")
        self._btn_forecast.setEnabled(False)
        self._btn_forecast.clicked.connect(self._run_and_display)
        self._btn_control = QPushButton("Kiểm soát")
        self._btn_control.setEnabled(False)
        self._btn_control.clicked.connect(self._open_control_dialog)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._btn_forecast)
        btn_row.addWidget(self._btn_control)
        layout.addLayout(btn_row)

        # --- Metrics: train + hold-out (ẩn trước khi có kết quả) ---
        self._metrics_group = QGroupBox("Tiêu chí sai số — Kỳ phân tích (Train)")
        self._metrics_form = QFormLayout(self._metrics_group)
        self._metrics_form.setSpacing(4)
        self._lbl_mae       = QLabel("—")
        self._lbl_rmse      = QLabel("—")
        self._lbl_mape      = QLabel("—")
        self._lbl_bias      = QLabel("—")
        self._lbl_bias_pct  = QLabel("—")
        self._lbl_fva       = QLabel("—")
        self._metrics_form.addRow("MAE:",            self._lbl_mae)
        self._metrics_form.addRow("RMSE:",           self._lbl_rmse)
        self._metrics_form.addRow("MAPE:",           self._lbl_mape)
        self._metrics_form.addRow("Cum. Bias:",      self._lbl_bias)
        self._metrics_form.addRow("Cum. Bias(%):",   self._lbl_bias_pct)
        self._metrics_form.addRow("FVA (vs benchmark):", self._lbl_fva)
        self._metrics_group.setVisible(False)
        layout.addWidget(self._metrics_group)

        self._ho_group = QGroupBox("Tiêu chí sai số — Kiểm định (Hold-out)")
        self._ho_form = QFormLayout(self._ho_group)
        self._ho_form.setSpacing(4)
        self._lbl_ho_mae      = QLabel("—")
        self._lbl_ho_rmse     = QLabel("—")
        self._lbl_ho_mape     = QLabel("—")
        self._lbl_ho_bias     = QLabel("—")
        self._lbl_ho_bias_pct = QLabel("—")
        self._ho_form.addRow("MAE:",          self._lbl_ho_mae)
        self._ho_form.addRow("RMSE:",         self._lbl_ho_rmse)
        self._ho_form.addRow("MAPE:",         self._lbl_ho_mape)
        self._ho_form.addRow("Cum. Bias:",    self._lbl_ho_bias)
        self._ho_form.addRow("Cum. Bias(%):", self._lbl_ho_bias_pct)
        self._ho_group.setVisible(False)
        layout.addWidget(self._ho_group)

        layout.addStretch()
        return w

    def _build_detail_table(self) -> QTableWidget:
        headers = ["t", "Yₜ", "Fₜ", "eₜ", "eₜ²", "|eₜ|/Yₜ", "Cum. Bias"]
        tbl = QTableWidget(0, len(headers))
        tbl.setHorizontalHeaderLabels(headers)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.setAlternatingRowColors(True)
        # Interactive: user có thể kéo cột; sau khi fill data ta gọi resizeColumnsToContents()
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        tbl.horizontalHeader().setMinimumSectionSize(52)
        tbl.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        tbl.verticalHeader().setVisible(False)
        return tbl

    # ------------------------------------------------------------------
    # Calculation
    # ------------------------------------------------------------------

    def _schedule_recalc(self) -> None:
        """Khởi động lại debounce timer."""
        self._recalc_timer.start()

    def _build_input(self) -> ForecastingInput:
        n_train = self._n_train_spinbox.value()
        alpha = self._alpha_spinbox.value() if self._alpha_spinbox else 0.3
        beta  = self._beta_spinbox.value()  if self._beta_spinbox  else 0.1
        k     = self._k_spinbox.value()     if self._k_spinbox     else 3
        return ForecastingInput(
            dataset=self._dataset,
            method=self._method,  # type: ignore[arg-type]
            n_train=n_train,
            alpha=alpha,
            beta=beta,
            k=k,
            benchmark=self._benchmark,  # type: ignore[arg-type]
        )

    def _recalculate_silent(self) -> None:
        """Tính toán ngầm (không hiển thị kết quả) — dùng khi khởi tạo."""
        try:
            inp = self._build_input()
            self._result = engine_run(inp)
        except Exception:  # noqa: BLE001
            return
        self._btn_forecast.setEnabled(True)
        # Hiển thị đường Y_t ban đầu (không có F_t)
        self._draw_yt_only()

    def _recalculate(self) -> None:
        """Tính toán (do thay đổi tham số); nếu đã hiển thị dự báo thì cập nhật."""
        try:
            inp = self._build_input()
            self._result = engine_run(inp)
        except Exception:  # noqa: BLE001
            return
        self._btn_forecast.setEnabled(True)
        if self._forecast_shown:
            self._update_charts()
            self._update_metrics()
            self._update_table()
        else:
            self._draw_yt_only()

    def _run_and_display(self) -> None:
        """Người dùng bấm "Dự báo" → tính toán đầy đủ và hiển thị tất cả."""
        try:
            inp = self._build_input()
            self._result = engine_run(inp)
        except Exception:  # noqa: BLE001
            return
        self._forecast_shown = True
        self._btn_control.setEnabled(True)
        self._metrics_group.setVisible(True)
        # Hold-out group: chỉ hiện khi n_train < n
        has_holdout = (
            self._result.holdout_metrics is not None
            and self._n_train_spinbox.value() < self._dataset.n
        )
        self._ho_group.setVisible(has_holdout)
        self._error_canvas.setVisible(True)
        self._table.setVisible(True)
        # Cân bằng chiều cao hai đồ thị
        total_h = self._chart_splitter.height()
        if total_h > 0:
            half = total_h // 2
            self._chart_splitter.setSizes([half, half])
        self._update_charts()
        self._update_metrics()
        self._update_table()

    # ------------------------------------------------------------------
    # Chart updates
    # ------------------------------------------------------------------

    def _draw_yt_only(self) -> None:
        """Vẽ chỉ đường Y_t (trạng thái ban đầu trước khi bấm Dự báo)."""
        if self._result is None:
            return
        rows = self._result.detail_rows
        t_vals = [r.t for r in rows]
        y_vals = [r.y_t for r in rows]

        self._forecast_fig.clear()
        ax = self._forecast_fig.add_subplot(111)
        ax.plot(t_vals, y_vals, color="#1f2eb4", linewidth=1.5,
                marker="o", markersize=3, label=r"$Y_t$")
        ax.set_xlabel("t", fontsize=8)
        ax.set_ylabel("Nhu cầu", fontsize=8)
        ax.legend(fontsize=7)
        ax.grid(True, linestyle="--", alpha=0.4)
        self._forecast_fig.subplots_adjust(left=0.13, right=0.97, top=0.93, bottom=0.12)
        self._forecast_canvas.draw()

    def _update_charts(self) -> None:
        if self._result is None:
            return

        rows = self._result.detail_rows
        t_vals = [r.t for r in rows]
        y_vals = [r.y_t for r in rows]
        f_vals = self._result.f_values
        e_vals = self._result.e_values
        n_train = self._n_train_spinbox.value()

        # Forecast chart
        self._forecast_fig.clear()
        ax = self._forecast_fig.add_subplot(111)
        ax.plot(t_vals, y_vals, color="#1f2eb4", linewidth=1.5,
                marker="o", markersize=3, label=r"$Y_t$")
        ft_x = [t for t, f in zip(t_vals, f_vals) if f is not None]
        ft_y = [f for f in f_vals if f is not None]
        if ft_x:
            ax.plot(ft_x, ft_y, color="#ff7f0e", linewidth=1.5,
                    linestyle="--", marker="s", markersize=3,
                    label=rf"$F_t$ ({self._method})")
        if n_train < len(t_vals):
            cutoff_t = self._dataset.points[0].t + n_train - 1
            ax.axvspan(cutoff_t + 0.5, t_vals[-1] + 0.5,
                       alpha=0.08, color="#9467bd", label="Hold-out")
        ax.set_xlabel("t", fontsize=8)
        ax.set_ylabel("Nhu cầu", fontsize=8)
        ax.legend(fontsize=7)
        ax.grid(True, linestyle="--", alpha=0.4)
        # Cố định lề trái giống nhau cho cả 2 đồ thị → trục tung thẳng hàng
        self._forecast_fig.subplots_adjust(left=0.13, right=0.97, top=0.93, bottom=0.12)
        self._forecast_canvas.draw()

        # Error chart
        self._error_fig.clear()
        ax2 = self._error_fig.add_subplot(111)
        valid_t = [t for t, e in zip(t_vals, e_vals) if e is not None]
        valid_e = [e for e in e_vals if e is not None]
        if valid_t:
            # xanh (e_t > 0) / đỏ (e_t < 0) để tương phản rõ ràng
            colors = ["#d62728" if e < 0 else "#47b41f" for e in valid_e]
            ax2.bar(valid_t, valid_e, color=colors, alpha=0.80, width=0.6)
            ax2.axhline(0, color="black", linewidth=0.8)
        ax2.set_xlabel("t", fontsize=8)
        ax2.set_ylabel(r"$e_t$", fontsize=8)
        ax2.grid(True, linestyle="--", alpha=0.4, axis="y")
        # Cùng giá trị left=0.13 → hai trục y thẳng cột với nhau
        self._error_fig.subplots_adjust(left=0.13, right=0.97, top=0.93, bottom=0.12)
        self._error_canvas.draw()

    # ------------------------------------------------------------------
    # Metrics update
    # ------------------------------------------------------------------

    def _update_metrics(self) -> None:
        if self._result is None or self._result.train_metrics is None:
            return
        # --- Train metrics ---
        m = self._result.train_metrics
        n_lbl = f" (n={m.n})" if m.n else ""
        self._metrics_group.setTitle(f"Tiêu chí sai số — Kỳ phân tích (Train){n_lbl}")
        self._lbl_mae.setText(f"{m.mae:.4f}")
        self._lbl_rmse.setText(f"{m.rmse:.4f}")
        self._lbl_mape.setText(
            f"{m.mape:.2f} %" if m.mape is not None else "N/A"
        )
        self._lbl_bias.setText(f"{m.bias:.4f}")
        self._lbl_bias_pct.setText(
            f"{m.bias_pct:.2f} %" if m.bias_pct is not None else "—"
        )
        self._lbl_fva.setText(
            f"{m.fva:.2f} %" if m.fva is not None else "—"
        )
        # --- Hold-out metrics ---
        ho = self._result.holdout_metrics
        has_holdout = (
            ho is not None
            and self._n_train_spinbox.value() < self._dataset.n
        )
        self._ho_group.setVisible(has_holdout)
        if has_holdout and ho is not None:
            n_ho_lbl = f" (n={ho.n})" if ho.n else ""
            self._ho_group.setTitle(
                f"Tiêu chí sai số — Kiểm định (Hold-out){n_ho_lbl}"
            )
            self._lbl_ho_mae.setText(f"{ho.mae:.4f}")
            self._lbl_ho_rmse.setText(f"{ho.rmse:.4f}")
            self._lbl_ho_mape.setText(
                f"{ho.mape:.2f} %" if ho.mape is not None else "N/A"
            )
            self._lbl_ho_bias.setText(f"{ho.bias:.4f}")
            self._lbl_ho_bias_pct.setText(
                f"{ho.bias_pct:.2f} %" if ho.bias_pct is not None else "—"
            )

    # ------------------------------------------------------------------
    # Table update
    # ------------------------------------------------------------------

    def _update_table(self) -> None:
        if self._result is None:
            return
        rows = self._result.detail_rows
        tbl = self._table
        tbl.setRowCount(len(rows))
        for r, row in enumerate(rows):
            def cell(val: object, decimals: int = 2) -> QTableWidgetItem:
                if val is None:
                    txt = "—"
                elif isinstance(val, float):
                    txt = f"{val:.{decimals}f}"
                else:
                    txt = str(val)
                item = QTableWidgetItem(txt)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                return item

            tbl.setItem(r, 0, cell(row.t, 0))
            tbl.setItem(r, 1, cell(row.y_t))
            tbl.setItem(r, 2, cell(row.f_t))
            tbl.setItem(r, 3, cell(row.e_t))
            tbl.setItem(r, 4, cell(row.e_t_sq))
            tbl.setItem(r, 5, cell(row.abs_et_over_yt))
            tbl.setItem(r, 6, cell(row.cum_bias))
        tbl.resizeColumnsToContents()

    # ------------------------------------------------------------------
    # Dialog launchers
    # ------------------------------------------------------------------

    def _open_forecast_dialog(self) -> None:
        if self._result is None:
            return
        from .forecast_dialog import ForecastDialog  # noqa: PLC0415
        dlg = ForecastDialog(
            result=self._result,
            dataset=self._dataset,
            n_train=self._n_train_spinbox.value(),
            parent=self,
        )
        dlg.exec()

    def _open_control_dialog(self) -> None:
        if self._result is None:
            return
        from .control_dialog import ControlDialog  # noqa: PLC0415
        dlg = ControlDialog(
            result=self._result,
            ts_threshold=self._ts_threshold,
            parent=self,
        )
        dlg.exec()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_dataset(self, dataset: DataSet) -> None:
        """Cập nhật dataset khi user nhập dữ liệu mới."""
        self._dataset = dataset
        n = dataset.n
        # Block signals to prevent cascade during simultaneous range+value update
        self._n_train_slider.blockSignals(True)
        self._n_train_spinbox.blockSignals(True)
        self._n_train_slider.setRange(2, n)
        self._n_train_spinbox.setRange(2, n)
        self._n_train_spinbox.setValue(n)
        self._n_train_slider.setValue(n)
        self._n_train_slider.blockSignals(False)
        self._n_train_spinbox.blockSignals(False)
        if self._k_spinbox:
            self._k_spinbox.setRange(1, min(20, n - 1) if n > 1 else 1)
        # Reset trạng thái: ẩn đồ thị sai số + bảng, yêu cầu bấm "Dự báo" lại
        self._forecast_shown = False
        self._error_canvas.setVisible(False)
        self._table.setVisible(False)
        self._metrics_group.setVisible(False)
        self._ho_group.setVisible(False)
        self._btn_control.setEnabled(False)
        self._recalculate_silent()

    def update_config(self, ts_threshold: float, benchmark: str) -> None:
        """Cập nhật cấu hình TS threshold và benchmark."""
        self._ts_threshold = ts_threshold
        self._benchmark = benchmark
        self._recalculate()

    def get_result(self) -> ForecastResult | None:
        """Trả về kết quả dự báo hiện tại."""
        return self._result

    def get_params(self) -> dict:
        """Trả về dict tham số hiện tại để lưu vào state."""
        params: dict = {
            "n_train": self._n_train_spinbox.value(),
        }
        if self._alpha_spinbox:
            params["alpha"] = self._alpha_spinbox.value()
        if self._beta_spinbox:
            params["beta"] = self._beta_spinbox.value()
        if self._k_spinbox:
            params["k"] = self._k_spinbox.value()
        return params

    def restore_params(self, params: dict) -> None:
        """Phục hồi tham số từ saved state."""
        if "n_train" in params:
            self._n_train_spinbox.setValue(params["n_train"])
        if "alpha" in params and self._alpha_spinbox:
            self._alpha_spinbox.setValue(params["alpha"])
        if "beta" in params and self._beta_spinbox:
            self._beta_spinbox.setValue(params["beta"])
        if "k" in params and self._k_spinbox:
            self._k_spinbox.setValue(params["k"])
