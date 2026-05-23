"""ConfigDialog — cấu hình benchmark và ngưỡng Tracking Signal.

QDialog modal, mở từ nút "Cấu hình" trên toolbar của MainView hoặc DataHubTab.
Kết quả trả về qua exec() + get_config().
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractSpinBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QComboBox,
    QVBoxLayout,
    QWidget,
)


# Các lựa chọn benchmark hợp lệ (hiển thị → giá trị nội bộ)
_BENCHMARK_CHOICES: list[tuple[str, str]] = [
    ("Naive (Fₜ = Yₜ₋₁)", "naive"),
    ("MA(2) — Trung bình 2 kỳ", "ma2"),
    ("MA(3) — Trung bình 3 kỳ", "ma3"),
]

_DEFAULT_BENCHMARK = "naive"
_DEFAULT_TS_THRESHOLD = 4.0
_TS_MIN = 1.0
_TS_MAX = 10.0


class ConfigDialog(QDialog):
    """Dialog cấu hình tham số toàn module.

    Attributes:
        _benchmark_combo:  QComboBox chọn benchmark.
        _ts_spinbox:       QDoubleSpinBox cho ngưỡng ±TS.
    """

    def __init__(
        self,
        parent: QWidget | None = None,
        benchmark: str = _DEFAULT_BENCHMARK,
        ts_threshold: float = _DEFAULT_TS_THRESHOLD,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cấu hình module")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setStyleSheet("font-size: 12px;")
        self.setWindowFlags(
            self.windowFlags() & ~Qt.WindowContextHelpButtonHint  # type: ignore[operator]
        )

        self._build_ui()
        self._set_values(benchmark, ts_threshold)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 12)
        root.setSpacing(12)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # Benchmark selector
        self._benchmark_combo = QComboBox()
        for label, _ in _BENCHMARK_CHOICES:
            self._benchmark_combo.addItem(label)
        self._benchmark_combo.setMaxVisibleItems(3)
        self._benchmark_combo.setMinimumContentsLength(24)
        self._benchmark_combo.setSizeAdjustPolicy(
            QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon
        )
        form.addRow("Benchmark mặc định:", self._benchmark_combo)

        # Tracking Signal threshold
        self._ts_spinbox = QDoubleSpinBox()
        self._ts_spinbox.setRange(_TS_MIN, _TS_MAX)
        self._ts_spinbox.setSingleStep(0.5)
        self._ts_spinbox.setDecimals(1)
        self._ts_spinbox.setSuffix("  (±)")
        self._ts_spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
        self._ts_spinbox.setToolTip(
            "Ngưỡng Tracking Signal. Thường dùng ±4.0.\n"
            "TS vượt ngưỡng → mô hình cần điều chỉnh."
        )
        form.addRow("Ngưỡng Tracking Signal:", self._ts_spinbox)

        root.addLayout(form)

        # Standard OK / Cancel buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Lưu")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _set_values(self, benchmark: str, ts_threshold: float) -> None:
        """Thiết lập giá trị ban đầu."""
        idx = next(
            (i for i, (_, v) in enumerate(_BENCHMARK_CHOICES) if v == benchmark),
            0,
        )
        self._benchmark_combo.setCurrentIndex(idx)
        ts = max(_TS_MIN, min(_TS_MAX, ts_threshold))
        self._ts_spinbox.setValue(ts)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_config(self) -> dict:
        """Trả về dict cấu hình sau khi user bấm Lưu.

        Returns:
            {"benchmark": str, "ts_threshold": float}
        """
        combo_idx = self._benchmark_combo.currentIndex()
        benchmark = _BENCHMARK_CHOICES[combo_idx][1]
        return {
            "benchmark": benchmark,
            "ts_threshold": round(self._ts_spinbox.value(), 1),
        }

    @staticmethod
    def open_and_get(
        parent: QWidget | None,
        current_config: dict,
    ) -> dict | None:
        """Mở dialog và trả về config mới nếu user bấm Lưu, None nếu Hủy.

        Args:
            parent:         Widget cha.
            current_config: Config hiện tại {"benchmark": ..., "ts_threshold": ...}.

        Returns:
            dict config mới, hoặc None nếu user hủy.
        """
        dlg = ConfigDialog(
            parent=parent,
            benchmark=current_config.get("benchmark", _DEFAULT_BENCHMARK),
            ts_threshold=current_config.get("ts_threshold", _DEFAULT_TS_THRESHOLD),
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            return dlg.get_config()
        return None
