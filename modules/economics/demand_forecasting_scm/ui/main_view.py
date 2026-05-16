"""MainView — QWidget gốc của module demand_forecasting_scm.

Cấu trúc:
  QWidget (root)
  └── QVBoxLayout
      ├── toolbar (nút "Cấu hình")
      └── QTabWidget — 6 tabs
          ├── Tab 0: DataHubTab         — luôn enabled
          ├── Tab 1: StationaryTab      — unlock khi có dữ liệu + phân tích
          ├── Tab 2: TrendTab           — unlock khi có dữ liệu + phân tích
          ├── Tab 3–5: placeholder Phase 2 (disabled)

Luồng dữ liệu:
  DataHubTab.dataset_changed → MainView._on_dataset_changed
  DataHubTab.tab_unlock_requested → MainView._unlock_tab
  ConfigDialog → MainView._apply_config → broadcast xuống tất cả tabs
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..models.inputs import DataSet
from ..models.state import DemandForecastingState
from .config_dialog import ConfigDialog
from .data_hub_tab import DataHubTab

# Tab indices
_TAB_DATA_HUB      = 0
_TAB_STATIONARY    = 1
_TAB_TREND         = 2
_TAB_PHASE2_SEASON = 3
_TAB_PHASE2_CYCLE  = 4
_TAB_PHASE2_ADV    = 5

_DEFAULT_CONFIG = {
    "benchmark": "naive",
    "ts_threshold": 4.0,
}

# Nhãn các tab Phase 2 (chưa triển khai)
_PHASE2_LABELS = [
    "Mùa vụ [Phase 2]",
    "Chu kỳ [Phase 2]",
    "Nâng cao [Phase 2]",
]


class MainView(QWidget):
    """Root widget của module demand_forecasting_scm.

    Args:
        context: ModuleContext từ IIMP host (có thể None khi test headless).
    """

    def __init__(self, context=None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._context = context
        self._config: dict = dict(_DEFAULT_CONFIG)
        self._dataset: DataSet | None = None

        # Tabs pattern sẽ được khởi tạo khi dataset đến
        self._stationary_tab: "StationaryTab | None" = None
        self._trend_tab: "TrendTab | None" = None

        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # Toolbar
        toolbar = QWidget()
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(4, 2, 4, 2)
        tb_layout.addWidget(
            QLabel("<b>Dự báo nhu cầu chuỗi cung ứng</b> — Demand Forecasting SCM")
        )
        tb_layout.addStretch()
        btn_config = QPushButton("⚙ Cấu hình")
        btn_config.setFixedWidth(100)
        btn_config.clicked.connect(self._open_config)
        tb_layout.addWidget(btn_config)
        root.addWidget(toolbar)

        # Main tab widget
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)

        # Tab 0 — Data Hub
        self._data_hub = DataHubTab()
        self._data_hub.dataset_changed.connect(self._on_dataset_changed)
        self._data_hub.tab_unlock_requested.connect(self._unlock_tab)
        self._tabs.addTab(self._data_hub, "Thiết lập chung")

        # Tab 1 — Stationary placeholder
        self._tab1_placeholder = self._make_placeholder(
            "Mẫu hình Ổn định",
            "Nhập dữ liệu ở tab 'Thiết lập chung', sau đó bấm\n"
            "'Phân tích Ổn định →' để mở phân tích.",
        )
        self._tabs.addTab(self._tab1_placeholder, "Mẫu hình Ổn định")
        self._tabs.setTabEnabled(_TAB_STATIONARY, False)

        # Tab 2 — Trend placeholder
        self._tab2_placeholder = self._make_placeholder(
            "Mẫu hình Xu hướng",
            "Nhập dữ liệu ở tab 'Thiết lập chung', sau đó bấm\n"
            "'Phân tích Xu hướng →' để mở phân tích.",
        )
        self._tabs.addTab(self._tab2_placeholder, "Mẫu hình Xu hướng")
        self._tabs.setTabEnabled(_TAB_TREND, False)

        # Tab 3-5 — Phase 2 placeholders (disabled)
        for label in _PHASE2_LABELS:
            ph = self._make_placeholder(label, "Sẽ có trong Phase 2.")
            self._tabs.addTab(ph, label)
            idx = self._tabs.indexOf(ph)
            self._tabs.setTabEnabled(idx, False)

        root.addWidget(self._tabs)

    @staticmethod
    def _make_placeholder(title: str, msg: str) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl = QLabel(f"<center><b>{title}</b><br><br>{msg}</center>")
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #888;")
        layout.addWidget(lbl)
        return w

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    def _on_dataset_changed(self, dataset: DataSet) -> None:
        """Nhận dataset mới từ DataHubTab — broadcast xuống các pattern tabs."""
        self._dataset = dataset
        sugg = self._data_hub.get_suggestion()
        if self._stationary_tab is not None:
            self._stationary_tab.update_dataset(dataset)
            if sugg is not None:
                self._stationary_tab.update_suggestion(sugg.get("stationary"))
        if self._trend_tab is not None:
            self._trend_tab.update_dataset(dataset)
            if sugg is not None:
                self._trend_tab.update_suggestion(sugg.get("trend"))

    def _unlock_tab(self, pattern: str) -> None:
        """Mở khóa tab tương ứng và khởi tạo nếu chưa có."""
        if self._dataset is None:
            return

        if pattern == "stationary":
            if self._stationary_tab is None:
                self._init_stationary_tab()
            self._tabs.setTabEnabled(_TAB_STATIONARY, True)
            self._tabs.setCurrentIndex(_TAB_STATIONARY)

        elif pattern == "trend":
            if self._trend_tab is None:
                self._init_trend_tab()
            self._tabs.setTabEnabled(_TAB_TREND, True)
            self._tabs.setCurrentIndex(_TAB_TREND)

    def _init_stationary_tab(self) -> None:
        from .stationary_tab import StationaryTab  # noqa: PLC0415
        sugg = self._data_hub.get_suggestion()
        self._stationary_tab = StationaryTab(
            dataset=self._dataset,  # type: ignore[arg-type]
            ts_threshold=self._config.get("ts_threshold", 4.0),
            benchmark=self._config.get("benchmark", "naive"),
            suggestion=sugg.get("stationary") if sugg else None,
        )
        # Thay placeholder bằng tab thật
        self._tabs.removeTab(_TAB_STATIONARY)
        self._tabs.insertTab(_TAB_STATIONARY, self._stationary_tab, "Mẫu hình Ổn định")

    def _init_trend_tab(self) -> None:
        from .trend_tab import TrendTab  # noqa: PLC0415
        sugg = self._data_hub.get_suggestion()
        self._trend_tab = TrendTab(
            dataset=self._dataset,  # type: ignore[arg-type]
            ts_threshold=self._config.get("ts_threshold", 4.0),
            benchmark=self._config.get("benchmark", "naive"),
            suggestion=sugg.get("trend") if sugg else None,
        )
        self._tabs.removeTab(_TAB_TREND)
        self._tabs.insertTab(_TAB_TREND, self._trend_tab, "Mẫu hình Xu hướng")

    def _open_config(self) -> None:
        new_config = ConfigDialog.open_and_get(self, self._config)
        if new_config is not None:
            self._apply_config(new_config)
            if self._context is not None:
                try:
                    self._context.settings_service.set(
                        "demand_forecasting_scm.config", new_config
                    )
                except Exception:  # noqa: BLE001
                    pass

    def _apply_config(self, config: dict) -> None:
        self._config = config
        ts = config.get("ts_threshold", 4.0)
        bm = config.get("benchmark", "naive")
        if self._stationary_tab is not None:
            self._stationary_tab.update_config(ts, bm)
        if self._trend_tab is not None:
            self._trend_tab.update_config(ts, bm)

    # ------------------------------------------------------------------
    # State management (gọi từ module.py)
    # ------------------------------------------------------------------

    def get_state(self) -> DemandForecastingState:
        """Thu thập state hiện tại để lưu."""
        state = DemandForecastingState()

        if self._dataset is not None:
            state.dataset = self._dataset.to_dict_list()
            state.dataset_source = self._dataset.source

        state.active_tab_index = self._tabs.currentIndex()
        state.config = dict(self._config)

        # Method params
        if self._stationary_tab is not None:
            state.method_params.update(self._stationary_tab.get_all_params())
            state.unlock_tab("stationary")
        if self._trend_tab is not None:
            state.method_params.update(self._trend_tab.get_all_params())
            state.unlock_tab("trend")

        return state

    def restore_state(self, state: DemandForecastingState) -> None:
        """Phục hồi state đã lưu."""
        # Config
        if state.config:
            self._apply_config(state.config)

        # Dataset
        if state.dataset:
            from ..models.inputs import DataSet as _DS  # noqa: PLC0415
            ds = _DS.from_dict_list(state.dataset, source=state.dataset_source)
            self._data_hub.set_dataset(ds)
            self._dataset = ds

        # Unlock tabs
        for tab_name in state.unlocked_tabs:
            self._unlock_tab(tab_name)

        # Restore params
        if self._stationary_tab is not None:
            s_params = {
                m: p for m, p in state.method_params.items()
                if m in ("naive", "moving_average", "ses")
            }
            if s_params:
                self._stationary_tab.restore_all_params(s_params)

        if self._trend_tab is not None:
            t_params = {
                m: p for m, p in state.method_params.items()
                if m in ("linear_regression", "holt")
            }
            if t_params:
                self._trend_tab.restore_all_params(t_params)

        # Active tab
        if 0 <= state.active_tab_index < self._tabs.count():
            if self._tabs.isTabEnabled(state.active_tab_index):
                self._tabs.setCurrentIndex(state.active_tab_index)
