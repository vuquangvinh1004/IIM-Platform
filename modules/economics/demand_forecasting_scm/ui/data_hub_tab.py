"""DataHubTab — Tab 0: Thiết lập chung / Nhập dữ liệu.

Chứa:
- DataInputDialog  : QDialog nhập tay hoặc tải CSV/Excel
- DataHubTab       : QWidget chính của Tab 0

DataHubTab phát signal dataset_changed(DataSet) mỗi khi dữ liệu thay đổi.
MainView lắng nghe signal này để điều phối unlock tab.
"""
from __future__ import annotations

import csv
import os
from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg

from ..models.inputs import DataPoint, DataSet
from ..services.chart_builder import build_yt_chart
from ..services.data_analyzer import analyze

if TYPE_CHECKING:
    from ..models.outputs import SuggestionResult


# ---------------------------------------------------------------------------
# DataInputDialog
# ---------------------------------------------------------------------------

class DataInputDialog(QDialog):
    """Dialog nhập dữ liệu — nhập tay hoặc tải CSV/Excel.

    Trả về DataSet khi user bấm Xác nhận.
    """

    def __init__(self, parent: QWidget | None = None, existing: DataSet | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nhập / Chỉnh sửa dữ liệu")
        self.setModal(True)
        self.setMinimumSize(540, 420)
        self.setStyleSheet("font-size: 12px;")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint  # type: ignore[operator]
        )

        self._existing = existing
        self._imported_rows: list[tuple[int, float]] | None = None
        self._build_ui()
        if existing:
            self._populate_table(existing)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 10)

        self._tab_widget = QTabWidget()
        self._tab_widget.addTab(self._build_manual_tab(), "Nhập tay")
        self._tab_widget.addTab(self._build_file_tab(), "Tải file (CSV)")
        root.addWidget(self._tab_widget)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Xác nhận")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_manual_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        # Bảng nhập liệu
        self._table = QTableWidget(0, 2)
        self._table.setHorizontalHeaderLabels(["Kỳ (t)", "Nhu cầu Yₜ"])
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self._table.setMinimumHeight(200)
        layout.addWidget(self._table)

        # Số hàng ban đầu
        if not self._existing:
            self._add_rows(12)

        # Buttons thêm / xóa hàng
        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Thêm hàng")
        btn_add.clicked.connect(lambda: self._add_rows(1))
        btn_remove = QPushButton("− Xóa hàng cuối")
        btn_remove.clicked.connect(self._remove_last_row)
        btn_add_col = QPushButton("+ Thêm cột")
        btn_add_col.setToolTip(
            "Thêm cột biến ngoại sinh (X₁, X₂, ...) cho phân tích nhân quả.\n"
            "Hiện tại chỉ cột t và Yₜ được dùng cho dự báo."
        )
        btn_add_col.clicked.connect(self._add_column)
        btn_row.addWidget(btn_add)
        btn_row.addWidget(btn_remove)
        btn_row.addWidget(btn_add_col)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        hint = QLabel("Để trống các hàng không dùng. Kỳ t phải là số nguyên ≥ 1.")
        hint.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(hint)
        return w

    def _build_file_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        btn_open = QPushButton("Chọn file CSV…")
        btn_open.setMaximumWidth(180)
        btn_open.clicked.connect(self._load_csv)
        layout.addWidget(btn_open)

        self._file_label = QLabel("Chưa chọn file.")
        self._file_label.setStyleSheet("color: #888;")
        layout.addWidget(self._file_label)

        hint = QLabel(
            "Định dạng CSV: cột 1 = kỳ (t), cột 2 = nhu cầu (Yₜ).\n"
            "Hàng đầu tiên có thể là header — sẽ bị bỏ qua nếu không phải số."
        )
        hint.setStyleSheet("color: #888; font-size: 12px;")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        layout.addStretch()
        return w

    # ------------------------------------------------------------------
    # Helpers — table
    # ------------------------------------------------------------------

    def _add_rows(self, n: int) -> None:
        current = self._table.rowCount()
        self._table.setRowCount(current + n)

        # Pre-fill t using the max existing t value to avoid duplicates
        max_t = 0
        for r in range(current):
            item = self._table.item(r, 0)
            if item:
                try:
                    max_t = max(max_t, int(item.text().strip()))
                except (ValueError, AttributeError):
                    pass
        # Fallback: if no existing t values, use row index
        if max_t == 0:
            max_t = current

        for offset, i in enumerate(range(current, current + n)):
            t_item = QTableWidgetItem(str(max_t + offset + 1))
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(i, 0, t_item)

    def _remove_last_row(self) -> None:
        n = self._table.rowCount()
        if n > 1:
            self._table.setRowCount(n - 1)

    def _add_column(self) -> None:
        """Thêm cột biến ngoại sinh X₁, X₂, ... cho phân tích nhân quả."""
        col_count = self._table.columnCount()
        extra_idx = col_count - 1  # số thứ tự biến X (1-based)
        self._table.setColumnCount(col_count + 1)
        # Tạo header Xₙ với Unicode subscript (1-9) hoặc Xₙ dạng thường
        subscripts = "₁₂₃₄₅₆₇₈₉"
        label = f"X{subscripts[extra_idx - 1]}" if extra_idx <= len(subscripts) else f"X{extra_idx}"
        self._table.setHorizontalHeaderItem(col_count, QTableWidgetItem(label))
        self._table.horizontalHeader().setSectionResizeMode(
            col_count, QHeaderView.ResizeMode.Stretch
        )

    def _populate_table(self, ds: DataSet) -> None:
        self._table.setRowCount(len(ds.points))
        for row, pt in enumerate(ds.points):
            t_item = QTableWidgetItem(str(pt.t))
            t_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            y_item = QTableWidgetItem(str(pt.y))
            y_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, t_item)
            self._table.setItem(row, 1, y_item)

    # ------------------------------------------------------------------
    # CSV loading
    # ------------------------------------------------------------------

    def _load_csv(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn file CSV",
            "",
            "CSV files (*.csv);;All files (*)",
        )
        if not path:
            return

        try:
            rows = self._parse_csv(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.warning(self, "Lỗi đọc file", str(exc))
            return

        if not rows:
            QMessageBox.warning(self, "File trống", "File CSV không có dữ liệu hợp lệ.")
            return

        self._imported_rows = rows
        self._file_label.setText(
            f"✓ Đã tải: {os.path.basename(path)}  ({len(rows)} hàng)"
        )

    @staticmethod
    def _parse_csv(path: str) -> list[tuple[int, float]]:
        """Đọc CSV, cột 1 = t, cột 2 = Y_t. Bỏ qua header nếu không phải số."""
        rows: list[tuple[int, float]] = []
        with open(path, newline="", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            for line_no, row in enumerate(reader, start=1):
                if len(row) < 2:
                    continue
                try:
                    t_val = int(float(row[0].strip()))
                    y_val = float(row[1].strip())
                except ValueError:
                    if line_no == 1:
                        continue  # skip header
                    raise ValueError(
                        f"Dòng {line_no}: không thể chuyển '{row[0]}', '{row[1]}' "
                        "thành số nguyên và số thực."
                    )
                rows.append((t_val, y_val))
        return rows

    # ------------------------------------------------------------------
    # Validation & accept
    # ------------------------------------------------------------------

    def _on_accept(self) -> None:
        """Validate và build DataSet trước khi accept."""
        try:
            ds = self._build_dataset()
        except ValueError as exc:
            QMessageBox.warning(self, "Dữ liệu không hợp lệ", str(exc))
            return
        self._result_dataset = ds
        self.accept()

    def _build_dataset(self) -> DataSet:
        """Thu thập dữ liệu từ tab đang active và tạo DataSet."""
        active_tab = self._tab_widget.currentIndex()

        if active_tab == 1 and self._imported_rows is not None:
            raw = self._imported_rows
        else:
            raw = self._collect_table_rows()

        if not raw:
            raise ValueError("Chưa có dữ liệu. Vui lòng nhập ít nhất 3 điểm.")

        if len(raw) < 3:
            raise ValueError(f"Cần tối thiểu 3 điểm dữ liệu (hiện có {len(raw)}).")

        # Kiểm tra trùng t
        t_list = [r[0] for r in raw]
        if len(t_list) != len(set(t_list)):
            raise ValueError("Tồn tại kỳ t trùng nhau. Mỗi kỳ phải là duy nhất.")

        points = [DataPoint(t=t, y=y) for t, y in sorted(raw)]
        return DataSet(points=points, source="manual" if active_tab == 0 else "csv")

    def _collect_table_rows(self) -> list[tuple[int, float]]:
        """Thu thập các hàng hợp lệ từ bảng nhập tay."""
        rows: list[tuple[int, float]] = []
        for row in range(self._table.rowCount()):
            t_item = self._table.item(row, 0)
            y_item = self._table.item(row, 1)
            if t_item is None or y_item is None:
                continue
            t_str = t_item.text().strip()
            y_str = y_item.text().strip()
            if not t_str or not y_str:
                continue
            try:
                t_val = int(t_str)
                y_val = float(y_str)
            except ValueError:
                raise ValueError(
                    f"Hàng {row + 1}: '{t_str}', '{y_str}' không phải số hợp lệ."
                )
            if t_val < 1:
                raise ValueError(f"Hàng {row + 1}: kỳ t phải ≥ 1, nhận được {t_val}.")
            rows.append((t_val, y_val))
        return rows

    def get_dataset(self) -> DataSet | None:
        """Trả về DataSet đã được xác nhận, hoặc None nếu chưa."""
        return getattr(self, "_result_dataset", None)


# ---------------------------------------------------------------------------
# DataHubTab
# ---------------------------------------------------------------------------

_BADGE_STRONG = (
    "background:#2ecc71; color:white; border-radius:4px; "
    "padding:2px 6px; font-size:12px;"
)
_BADGE_POSSIBLE = (
    "background:#f39c12; color:white; border-radius:4px; "
    "padding:2px 6px; font-size:12px;"
)
_BADGE_NONE = (
    "background:#bdc3c7; color:#555; border-radius:4px; "
    "padding:2px 6px; font-size:12px;"
)


class DataHubTab(QWidget):
    """Tab 0 — Thiết lập chung.

    Signals:
        dataset_changed(DataSet): phát ra mỗi khi user xác nhận dữ liệu mới.
        tab_unlock_requested(str): phát ra khi Smart Suggestion khuyến nghị mở tab.
            Giá trị: "stationary" hoặc "trend".
    """

    dataset_changed = Signal(object)        # DataSet
    tab_unlock_requested = Signal(str)      # "stationary" | "trend"

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._dataset: DataSet | None = None
        self._suggestion: SuggestionResult | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 8, 12, 8)
        root.setSpacing(8)

        # Header row
        header = QHBoxLayout()
        header.addWidget(QLabel("<b>Thiết lập chung — Dữ liệu nhu cầu</b>"))
        header.addStretch()
        self._btn_input = QPushButton("Nhập dữ liệu…")
        self._btn_input.setFixedWidth(130)
        self._btn_input.clicked.connect(self._open_input_dialog)
        header.addWidget(self._btn_input)
        root.addLayout(header)

        # Info bar
        self._info_label = QLabel("Chưa có dữ liệu. Bấm 'Nhập dữ liệu' để bắt đầu.")
        self._info_label.setStyleSheet("color: #666; font-size: 12px;")
        root.addWidget(self._info_label)

        # Chart area — ẩn cho đến khi có data
        self._chart_canvas: FigureCanvasQTAgg | None = None
        self._chart_container = QWidget()
        self._chart_container.setMinimumHeight(200)
        self._chart_container.setVisible(False)
        self._chart_layout = QVBoxLayout(self._chart_container)
        self._chart_layout.setContentsMargins(0, 0, 0, 0)
        root.addWidget(self._chart_container)

        # Outlier detection group
        self._outlier_group = QGroupBox("Làm sạch dữ liệu")
        self._outlier_group.setVisible(False)
        outlier_layout = QHBoxLayout(self._outlier_group)
        self._outlier_check = QCheckBox("Phát hiện và đánh dấu ngoại lệ (z-score)")
        self._outlier_check.setChecked(True)
        self._outlier_check.toggled.connect(self._refresh_analysis)
        outlier_layout.addWidget(self._outlier_check)
        outlier_layout.addWidget(QLabel("Ngưỡng σ:"))
        self._sigma_spinbox = QDoubleSpinBox()
        self._sigma_spinbox.setRange(1.0, 5.0)
        self._sigma_spinbox.setSingleStep(0.5)
        self._sigma_spinbox.setValue(2.5)
        self._sigma_spinbox.setDecimals(1)
        self._sigma_spinbox.setFixedWidth(70)
        self._sigma_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._sigma_spinbox.valueChanged.connect(self._refresh_analysis)
        outlier_layout.addWidget(self._sigma_spinbox)
        outlier_layout.addStretch()
        root.addWidget(self._outlier_group)

        # Smart Suggestion panel
        self._suggestion_group = QGroupBox("Gợi ý mẫu hình (Smart Suggestion)")
        self._suggestion_group.setVisible(False)
        sugg_layout = QFormLayout(self._suggestion_group)
        sugg_layout.setSpacing(8)

        # Row Ổn định
        stat_row = QHBoxLayout()
        self._stat_badge = QLabel("—")
        self._stat_badge.setFixedWidth(160)
        self._btn_analyze_stat = QPushButton("Phân tích Ổn định →")
        self._btn_analyze_stat.setFixedWidth(170)
        self._btn_analyze_stat.setEnabled(False)
        self._btn_analyze_stat.clicked.connect(
            lambda: self.tab_unlock_requested.emit("stationary")
        )
        stat_row.addWidget(self._stat_badge)
        stat_row.addWidget(self._btn_analyze_stat)
        stat_row.addStretch()
        sugg_layout.addRow("Tính dừng (ADF):", stat_row)

        # Row Xu hướng
        trend_row = QHBoxLayout()
        self._trend_badge = QLabel("—")
        self._trend_badge.setFixedWidth(160)
        self._btn_analyze_trend = QPushButton("Phân tích Xu hướng →")
        self._btn_analyze_trend.setFixedWidth(170)
        self._btn_analyze_trend.setEnabled(False)
        self._btn_analyze_trend.clicked.connect(
            lambda: self.tab_unlock_requested.emit("trend")
        )
        trend_row.addWidget(self._trend_badge)
        trend_row.addWidget(self._btn_analyze_trend)
        trend_row.addStretch()
        sugg_layout.addRow("Xu hướng (R²):", trend_row)

        root.addWidget(self._suggestion_group)
        root.addStretch()

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _open_input_dialog(self) -> None:
        dlg = DataInputDialog(parent=self, existing=self._dataset)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            ds = dlg.get_dataset()
            if ds is not None:
                self._apply_dataset(ds)

    def _apply_dataset(self, ds: DataSet) -> None:
        """Cập nhật UI với dataset mới."""
        self._dataset = ds
        self._update_info_bar()
        self._refresh_chart()
        self._refresh_analysis()
        self._outlier_group.setVisible(True)
        self._suggestion_group.setVisible(True)
        self._chart_container.setVisible(True)
        self.dataset_changed.emit(ds)

    def _update_info_bar(self) -> None:
        if self._dataset is None:
            self._info_label.setText("Chưa có dữ liệu.")
            return
        ds = self._dataset
        n = ds.n
        if n == 0:
            self._info_label.setText("Dataset rỗng.")
            return
        t_min = ds.points[0].t
        t_max = ds.points[-1].t
        # Dùng outlier_indices từ kết quả phân tích mới nhất (chính xác hơn p.is_outlier)
        n_out = len(self._suggestion.outlier_indices) if self._suggestion else 0
        out_txt = f"Ngoại lệ: {n_out} điểm" if n_out else "Không có ngoại lệ"
        self._info_label.setText(
            f"{n} điểm  |  Kỳ {t_min} đến {t_max}  |  {out_txt}  "
            f"|  Nguồn: {ds.source}"
        )

    def _refresh_chart(self) -> None:
        if self._dataset is None:
            return

        # Thu thập outlier indices nếu outlier check đang bật
        outlier_idxs: list[int] = []
        if self._outlier_check.isChecked():
            from ..services.data_analyzer import detect_outliers as _detect  # noqa: PLC0415
            outlier_idxs = _detect(self._dataset, self._sigma_spinbox.value())

        ds = self._dataset
        t_vals = [p.t for p in ds.points]
        y_vals = [p.y for p in ds.points]

        fig = build_yt_chart(t_vals, y_vals, outlier_indices=outlier_idxs)

        # Xóa canvas cũ nếu có
        if self._chart_canvas is not None:
            self._chart_layout.removeWidget(self._chart_canvas)
            self._chart_canvas.setParent(None)  # type: ignore[call-arg]
            self._chart_canvas.deleteLater()

        self._chart_canvas = FigureCanvasQTAgg(fig)
        self._chart_canvas.setMinimumHeight(180)
        self._chart_layout.addWidget(self._chart_canvas)

    def _refresh_analysis(self) -> None:
        if self._dataset is None:
            return

        sigma = self._sigma_spinbox.value() if self._outlier_check.isChecked() else 99.0
        self._suggestion = analyze(self._dataset, sigma_threshold=sigma)
        self._update_badges()
        self._refresh_chart()
        self._update_info_bar()

    def _update_badges(self) -> None:
        if self._suggestion is None:
            return
        has_data = self._dataset is not None

        # Stationarity badge
        stat = self._suggestion.get("stationary")
        if stat:
            self._stat_badge.setText(
                "Ổn định" if stat.strength == "strong"
                else ("Ổn định (khả năng)" if stat.strength == "possible" else "Không ổn định")
            )
            self._stat_badge.setStyleSheet(
                _BADGE_STRONG if stat.strength == "strong"
                else (_BADGE_POSSIBLE if stat.strength == "possible" else _BADGE_NONE)
            )
            self._btn_analyze_stat.setEnabled(has_data)
            self._btn_analyze_stat.setToolTip(stat.evidence)

        # Trend badge
        trend = self._suggestion.get("trend")
        if trend:
            self._trend_badge.setText(
                "Có xu hướng" if trend.strength == "strong"
                else ("Xu hướng (khả năng)" if trend.strength == "possible" else "Không xu hướng")
            )
            self._trend_badge.setStyleSheet(
                _BADGE_STRONG if trend.strength == "strong"
                else (_BADGE_POSSIBLE if trend.strength == "possible" else _BADGE_NONE)
            )
            self._btn_analyze_trend.setEnabled(has_data)
            self._btn_analyze_trend.setToolTip(trend.evidence)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_dataset(self) -> DataSet | None:
        """Trả về dataset hiện tại (None nếu chưa có)."""
        return self._dataset

    def set_dataset(self, ds: DataSet) -> None:
        """Phục hồi dataset từ state (gọi bởi module.restore_state)."""
        self._apply_dataset(ds)

    def get_suggestion(self) -> SuggestionResult | None:
        """Trả về kết quả phân tích Smart Suggestion gần nhất."""
        return self._suggestion
