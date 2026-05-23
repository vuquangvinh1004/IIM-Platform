"""TrendTab — Tab 2: Mẫu hình Xu hướng.

Sub-tabs: Thông tin | Linear Regression | Holt's Model
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QLabel,
    QScrollArea,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
import matplotlib
matplotlib.use("Agg")

from ..models.inputs import DataSet
from ..services.chart_builder import build_yt_chart
from .method_view import MethodView

if TYPE_CHECKING:
    from ..models.outputs import PatternSuggestion

_TREND_METHODS = [
    ("linear_regression", "Linear Regression"),
    ("holt",              "Holt's Model"),
]

_INFO_TEXT = """<b>Mẫu hình Xu hướng (Trend)</b>

<p>Chuỗi thời gian có xu hướng khi nhu cầu có chiều hướng tăng hoặc giảm có hệ thống theo thời gian.
Phát hiện xu hướng: R² của OLS bậc 1 — giá trị ≥ 0.5 cho thấy xu hướng rõ ràng.</p>

<p><b>Các phương pháp phù hợp:</b></p>

<p><b>1. Hồi quy tuyến tính (Linear Regression)</b><br>
<b>Mô hình:</b> Ŷ<sub>t</sub> = a + b·t + ε<sub>t</sub><br>
Giá trị dự báo được mô tả như một hàm tuyến tính theo thời gian.
a là hệ số chặn, b là độ dốc xu hướng, ε<sub>t</sub> là sai số ngẫu nhiên.
Tham số a và b được ước lượng bằng phương pháp OLS (bình phương tối thiểu).<br>
<i>Lưu ý:</i> Hiệu quả khi quan hệ với thời gian là tương đối tuyến tính.
Nếu xu hướng thay đổi theo thời gian hoặc dữ liệu có mùa vụ/chu kỳ phức tạp, sai số sẽ tăng.</p>

<p><b>2. Mô hình Holt (Holt’s Double Exponential Smoothing)</b><br>
<b>Mô hình:</b><br>
  Mức: L<sub>t</sub> = α·Y<sub>t</sub> + (1−α)[L<sub>t−1</sub> + T<sub>t−1</sub>]<br>
  Xu hướng: T<sub>t</sub> = β[L<sub>t</sub>−L<sub>t−1</sub>] + (1−β)T<sub>t−1</sub><br>
  Dự báo: Ŷ<sub>t+h</sub> = L<sub>t</sub> + h·T<sub>t</sub><br>
Holt mở rộng SES bằng cách bổ sung thành phần <b>xu hướng</b>.
L<sub>t</sub> là mức, T<sub>t</sub> là xu hướng, h là số kỳ dự báo trước.<br>
<i>Lưu ý:</i> Thích hợp hơn SES khi chuỗi có xu hướng rõ. Cần ước lượng hai tham số α và β.
Nếu dữ liệu có mùa vụ, nên dùng Holt-Winters thay vì Holt.</p>

"""

# Metric data: (label, LaTeX formula, description)
_METRICS_DATA: list[tuple[str, str, str]] = [
    (
        "MAE",
        r"\frac{1}{n} \cdot \sum |e_t|",
        "Sai số tuyệt đối bình quân theo đơn vị gốc. Càng nhỏ càng tốt. Không phản ánh hướng lệch (+/−).",
    ),
    (
        "RMSE",
        r"\sqrt{\frac{1}{n} \cdot \sum e_t^2}",
        "Khuếch đại sai số lọn hơn MAE. Cùng đơn vị dữ liệu, nhạy với ngoại lệ.",
    ),
    (
        "MAPE",
        r"\frac{1}{n} \cdot \sum \frac{|e_t|}{Y_t} \times 100\%",
        "Sai số bình quân theo %. Dễ so sánh giữa các chuỗi khác quy mô. Không dùng khi Y_t \u2248 0.",
    ),
    (
        "Cum. Bias",
        r"\frac{1}{n} \cdot \sum e_t",
        "Sai số bình quân có hướng. Dương: xu hướng dự báo thấp; âm: dự báo cao. Gần 0 → ít thiên lệch hệ thống.",
    ),
    (
        "Cum. Bias(%)",
        r"\frac{\sum e_t}{\sum Y_t} \times 100\%",
        "Bias tương đối so với tổng nhu cầu. Gần 0 → ít thiên lệch hệ thống.",
    ),
    (
        "FVA",
        r"\frac{E_{baseline} - E_{model}}{E_{baseline}} \times 100\%",
        "Dương: mô hình tốt hơn baseline. Âm: mô hình tệ hơn baseline.",
    ),
]


# Module-level pixmap cache: avoids re-rendering identical formulas
_FORMULA_CACHE: "dict[tuple[str, float], QPixmap]" = {}


def _formula_pixmap(latex: str, fontsize: float = 12) -> "QPixmap":
    """Render a LaTeX mathtext string to a transparent QPixmap via matplotlib.

    Renders at 2× DPI and sets devicePixelRatio(2.0) for crisp HiDPI display.
    Results are cached by (latex, fontsize) to avoid redundant re-renders.
    """
    cache_key = (latex, fontsize)
    if cache_key in _FORMULA_CACHE:
        return _FORMULA_CACHE[cache_key]

    import io
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from PySide6.QtGui import QPixmap

    RENDER_SCALE = 2  # render at 2× physical pixels for crispness

    fig = Figure(facecolor="none")
    canvas = FigureCanvasAgg(fig)
    ax = fig.add_axes([0, 0, 1, 1], facecolor="none")
    ax.set_axis_off()
    txt = ax.text(
        0.5, 0.5, f"${latex}$",
        fontsize=fontsize, color="#1a1a2e",
        ha="center", va="center",
        math_fontfamily="cm",
        transform=ax.transAxes,
    )
    canvas.draw()
    renderer = canvas.get_renderer()
    bbox = txt.get_window_extent(renderer)
    pad = 6
    dpi = fig.dpi
    w = max(int(bbox.width) + pad * 2, 50)
    h = max(int(bbox.height) + pad * 2, 28)
    fig.set_size_inches(w / dpi, h / dpi)
    fig.texts.clear()
    fig.text(
        0.5, 0.5, f"${latex}$",
        fontsize=fontsize, color="#1a1a2e",
        ha="center", va="center",
        math_fontfamily="cm",
    )
    canvas.draw()
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=dpi * RENDER_SCALE, transparent=True)
    buf.seek(0)
    pix = QPixmap()
    pix.loadFromData(buf.read())
    pix.setDevicePixelRatio(float(RENDER_SCALE))
    _FORMULA_CACHE[cache_key] = pix
    return pix


def _build_metrics_widget() -> "QWidget":
    """Build a 3-column table widget with matplotlib-rendered LaTeX formulas."""
    from PySide6.QtWidgets import QGridLayout, QVBoxLayout as _QVBox, QWidget as _QW
    from PySide6.QtCore import Qt as _Qt

    HDR = (
        "background-color:#dde8f8; font-weight:bold;"
        " padding:4px 8px; border:1px solid #b0c4de;"
    )
    CELL_BASE = "padding:5px 8px; border:1px solid #d0d8e8;"
    ROW_ODD  = "background-color:#ffffff;"
    ROW_EVEN = "background-color:#f4f7fc;"

    def _hdr(text: str) -> "QLabel":
        lb = QLabel(text)
        lb.setStyleSheet(HDR)
        lb.setAlignment(_Qt.AlignmentFlag.AlignVCenter | _Qt.AlignmentFlag.AlignLeft)
        return lb

    container = _QW()
    grid = QGridLayout(container)
    grid.setContentsMargins(0, 0, 0, 0)
    grid.setSpacing(0)
    grid.setColumnStretch(2, 1)

    grid.addWidget(_hdr("Tiêu chí"),          0, 0)
    grid.addWidget(_hdr("Công thức"),          0, 1)
    grid.addWidget(_hdr("Hướng dẫn sử dụng"), 0, 2)

    for row_idx, (name, formula, desc) in enumerate(_METRICS_DATA, 1):
        bg = ROW_EVEN if row_idx % 2 == 0 else ROW_ODD
        cell = CELL_BASE + bg

        name_lbl = QLabel(f"<b>{name}</b>")
        name_lbl.setStyleSheet(cell)
        name_lbl.setTextFormat(_Qt.TextFormat.RichText)
        name_lbl.setAlignment(
            _Qt.AlignmentFlag.AlignVCenter | _Qt.AlignmentFlag.AlignLeft
        )
        grid.addWidget(name_lbl, row_idx, 0)

        formula_lbl = QLabel()
        formula_lbl.setPixmap(_formula_pixmap(formula))
        formula_lbl.setAlignment(_Qt.AlignmentFlag.AlignCenter)
        formula_lbl.setStyleSheet(CELL_BASE + bg + " padding:4px 14px;")
        grid.addWidget(formula_lbl, row_idx, 1)

        desc_lbl = QLabel(desc)
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet(cell)
        grid.addWidget(desc_lbl, row_idx, 2)

    # wrapper with title + table + footer
    outer = _QW()
    vbox = _QVBox(outer)
    vbox.setContentsMargins(0, 0, 0, 0)
    vbox.setSpacing(4)

    title = QLabel(
        "<b>Các tiêu chí đánh giá mô hình dự báo</b>"
    )
    title.setTextFormat(_Qt.TextFormat.RichText)
    vbox.addWidget(title)
    vbox.addWidget(container)

    footer = QLabel(
        "<i>Nên kết hợp nhiều tiêu chí: MAE/RMSE đánh giá "
        "độ lớn sai số; Cum. Bias phát hiện thiên lệch hệ "
        "thống; FVA so sánh hiệu quả so với mức chuẩn.</i>"
    )
    footer.setWordWrap(True)
    footer.setTextFormat(_Qt.TextFormat.RichText)
    footer.setStyleSheet("color:#555; padding-top:2px;")
    vbox.addWidget(footer)

    return outer


_STRENGTH_STYLE = {
    "strong":   "color: #27ae60; font-weight: bold;",
    "possible": "color: #e67e22; font-weight: bold;",
    "none":     "color: #7f8c8d;",
}
_STRENGTH_TEXT = {
    "strong":   "✔ Xu hướng rõ ràng (R² ≥ 0.50)",
    "possible": "~ Có thể có xu hướng (0.25 ≤ R² < 0.50)",
    "none":     "✗ Không phát hiện xu hướng (R² < 0.25)",
}


class TrendTab(QWidget):
    """Tab 2 — Mẫu hình Xu hướng với 3 sub-tabs."""

    def __init__(
        self,
        dataset: DataSet,
        ts_threshold: float = 4.0,
        benchmark: str = "naive",
        suggestion: "PatternSuggestion | None" = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._dataset = dataset
        self._ts_threshold = ts_threshold
        self._benchmark = benchmark
        self._suggestion = suggestion
        self._method_views: dict[str, MethodView] = {}
        self._info_canvas: FigureCanvasQTAgg | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        self._sub_tabs = QTabWidget()
        self._sub_tabs.addTab(self._build_info_tab(), "Thông tin")

        for method_id, method_label in _TREND_METHODS:
            view = MethodView(
                method_name=method_id,
                dataset=self._dataset,
                ts_threshold=self._ts_threshold,
                benchmark=self._benchmark,
            )
            self._method_views[method_id] = view
            self._sub_tabs.addTab(view, method_label)

        root.addWidget(self._sub_tabs)

    def _build_info_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)

        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # --- Chart container (dynamic) ---
        self._info_chart_container = QWidget()
        self._info_chart_container.setMaximumHeight(230)
        self._info_chart_layout = QVBoxLayout(self._info_chart_container)
        self._info_chart_layout.setContentsMargins(0, 0, 0, 0)
        self._rebuild_info_chart()
        layout.addWidget(self._info_chart_container)

        # --- Trend result group ---
        trend_group = QGroupBox("Kết quả phân tích Xu hướng (OLS R²)")
        trend_form = QFormLayout(trend_group)
        trend_form.setSpacing(6)
        trend_form.setContentsMargins(10, 8, 10, 8)
        self._trend_result_lbl = QLabel("—")
        self._trend_evidence_lbl = QLabel("Chưa có dữ liệu phân tích.")
        self._trend_evidence_lbl.setWordWrap(True)
        self._trend_stat_lbl = QLabel("—")
        trend_form.addRow("Kết quả:", self._trend_result_lbl)
        trend_form.addRow("Chi tiết:", self._trend_evidence_lbl)
        trend_form.addRow("Giá trị thống kê:", self._trend_stat_lbl)
        layout.addWidget(trend_group)
        self._update_trend_display()

        # --- Info text (method descriptions) ---
        lbl = QLabel(_INFO_TEXT)
        lbl.setWordWrap(True)
        lbl.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(lbl)

        # --- Metrics table (LaTeX formulas via matplotlib) ---
        layout.addWidget(_build_metrics_widget())
        layout.addStretch()

        scroll.setWidget(w)
        return scroll

    def _rebuild_info_chart(self) -> None:
        """Xây dựng lại canvas chart Yₜ từ dataset hiện tại."""
        if self._info_canvas is not None:
            self._info_chart_layout.removeWidget(self._info_canvas)
            self._info_canvas.setParent(None)  # type: ignore[call-arg]
            self._info_canvas.deleteLater()

        t_vals = [p.t for p in self._dataset.points]
        y_vals = [p.y for p in self._dataset.points]
        fig = build_yt_chart(t_vals, y_vals, title="Chuỗi thời gian nhu cầu")
        self._info_canvas = FigureCanvasQTAgg(fig)
        self._info_chart_layout.addWidget(self._info_canvas)

    def _update_trend_display(self) -> None:
        """Cập nhật nhãn kết quả xu hướng từ suggestion hiện tại."""
        if self._suggestion is None:
            return
        s = self._suggestion
        style = _STRENGTH_STYLE.get(s.strength, "")
        text = _STRENGTH_TEXT.get(s.strength, "—")
        self._trend_result_lbl.setText(text)
        self._trend_result_lbl.setStyleSheet(style)
        self._trend_evidence_lbl.setText(s.evidence)
        if s.stat_value is not None:
            self._trend_stat_lbl.setText(f"R² = {s.stat_value:.4f}")
        else:
            self._trend_stat_lbl.setText("Không có")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update_dataset(self, dataset: DataSet) -> None:
        """Truyền dataset mới xuống tất cả MethodViews và cập nhật chart."""
        self._dataset = dataset
        self._rebuild_info_chart()
        for view in self._method_views.values():
            view.update_dataset(dataset)

    def update_suggestion(self, suggestion: "PatternSuggestion | None") -> None:
        """Cập nhật kết quả xu hướng từ Smart Suggestion của DataHubTab."""
        self._suggestion = suggestion
        self._update_trend_display()

    def update_config(self, ts_threshold: float, benchmark: str) -> None:
        self._ts_threshold = ts_threshold
        self._benchmark = benchmark
        for view in self._method_views.values():
            view.update_config(ts_threshold, benchmark)

    def get_method_view(self, method_id: str) -> MethodView | None:
        return self._method_views.get(method_id)

    def get_all_params(self) -> dict:
        return {m: v.get_params() for m, v in self._method_views.items()}

    def restore_all_params(self, params_dict: dict) -> None:
        for m, params in params_dict.items():
            if m in self._method_views:
                self._method_views[m].restore_params(params)
