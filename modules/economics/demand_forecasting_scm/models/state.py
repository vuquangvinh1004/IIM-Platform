"""State model for demand_forecasting_scm module.

DemandForecastingState được lưu/phục hồi qua StateManager của IIMP.
Version hóa rõ ràng để đảm bảo backward compatibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# Version của schema state — tăng lên nếu cấu trúc thay đổi không tương thích
STATE_VERSION = "1.0.0"


@dataclass
class DemandForecastingState:
    """Trạng thái đầy đủ của module demand_forecasting_scm.

    Attributes:
        version:              Phiên bản schema state — dùng để migration.
        dataset:              Dữ liệu chuỗi thời gian [{t, y, is_outlier}, ...].
        dataset_source:       Nguồn dữ liệu: "manual" / "csv" / "excel".
        active_tab_index:     Tab đang active trong QTabWidget chính (0-5).
        active_subtab_indices: Sub-tab đang active cho từng pattern tab.
        method_params:        Tham số đã thiết lập cho từng phương pháp.
        config:               Cấu hình module (benchmark, ts_threshold).
        unlocked_tabs:        Các tab đã được mở khóa theo tên.
    """

    version: str = STATE_VERSION

    # Dataset
    dataset: list[dict] = field(default_factory=list)
    dataset_source: str = "manual"

    # Navigation state
    active_tab_index: int = 0
    active_subtab_indices: dict[str, int] = field(default_factory=dict)
    # Ví dụ: {"stationary": 0, "trend": 0}

    # Tham số từng phương pháp — key là method name
    method_params: dict[str, dict] = field(default_factory=dict)
    # Ví dụ:
    # {
    #   "naive":              {"n_train": 10},
    #   "moving_average":     {"n_train": 10, "k": 3},
    #   "ses":                {"n_train": 10, "alpha": 0.3},
    #   "linear_regression":  {"n_train": 10},
    #   "holt":               {"n_train": 10, "alpha": 0.3, "beta": 0.1},
    # }

    # Cấu hình module
    config: dict = field(default_factory=lambda: {
        "benchmark": "naive",
        "ts_threshold": 4.0,
    })

    # Tabs đã được mở khóa (Smart Suggestion đã xác nhận)
    unlocked_tabs: list[str] = field(default_factory=list)
    # Ví dụ: ["stationary", "trend"]

    def to_dict(self) -> dict:
        """Serialize sang dict để StateManager lưu vào SQLite."""
        return {
            "version": self.version,
            "dataset": self.dataset,
            "dataset_source": self.dataset_source,
            "active_tab_index": self.active_tab_index,
            "active_subtab_indices": self.active_subtab_indices,
            "method_params": self.method_params,
            "config": self.config,
            "unlocked_tabs": self.unlocked_tabs,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "DemandForecastingState":
        """Phục hồi state từ dict đã lưu.

        Nếu version không khớp, trả về state mặc định để tránh lỗi.
        """
        if data.get("version") != STATE_VERSION:
            # Migration chưa triển khai ở Phase 1 — reset về mặc định
            return cls()

        return cls(
            version=data.get("version", STATE_VERSION),
            dataset=data.get("dataset", []),
            dataset_source=data.get("dataset_source", "manual"),
            active_tab_index=data.get("active_tab_index", 0),
            active_subtab_indices=data.get("active_subtab_indices", {}),
            method_params=data.get("method_params", {}),
            config=data.get("config", {"benchmark": "naive", "ts_threshold": 4.0}),
            unlocked_tabs=data.get("unlocked_tabs", []),
        )

    def get_method_params(self, method: str) -> dict:
        """Lấy tham số đã lưu của một phương pháp, trả về dict rỗng nếu chưa có."""
        return self.method_params.get(method, {})

    def update_method_params(self, method: str, params: dict) -> None:
        """Cập nhật tham số cho một phương pháp."""
        self.method_params[method] = params

    def unlock_tab(self, tab_name: str) -> None:
        """Mở khóa một tab nếu chưa được mở."""
        if tab_name not in self.unlocked_tabs:
            self.unlocked_tabs.append(tab_name)

    def is_tab_unlocked(self, tab_name: str) -> bool:
        return tab_name in self.unlocked_tabs
