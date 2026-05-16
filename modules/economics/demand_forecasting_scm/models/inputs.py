"""Input data models for demand_forecasting_scm.

DataPoint   — một điểm dữ liệu (kỳ t, nhu cầu y)
DataSet     — tập dữ liệu chuỗi thời gian đã được xác nhận
ForecastingInput — tham số chạy một phương pháp dự báo cụ thể
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DataPoint:
    """Một điểm dữ liệu chuỗi thời gian.

    Attributes:
        t: Chỉ số kỳ (1-based, integer).
        y: Giá trị nhu cầu thực tế tại kỳ t (phải > 0 để MAPE hợp lệ).
        is_outlier: True nếu điểm này đã bị đánh dấu là ngoại lệ.
    """

    t: int
    y: float
    is_outlier: bool = False

    def __post_init__(self) -> None:
        if self.t < 1:
            raise ValueError(f"t phải >= 1, nhận được: {self.t}")
        if not isinstance(self.y, (int, float)):
            raise TypeError(f"y phải là số, nhận được: {type(self.y)}")


@dataclass
class DataSet:
    """Tập dữ liệu chuỗi thời gian đã được xác nhận và sẵn sàng dùng.

    Attributes:
        points: Danh sách các DataPoint theo thứ tự tăng dần của t.
        source: Nguồn gốc dữ liệu, dùng để hiển thị thông tin.
    """

    points: list[DataPoint] = field(default_factory=list)
    source: str = "manual"  # "manual" | "csv" | "excel"

    def __post_init__(self) -> None:
        if self.points:
            self._validate_sequence()

    def _validate_sequence(self) -> None:
        ts = [p.t for p in self.points]
        if ts != sorted(ts):
            raise ValueError("DataPoint phải được sắp xếp tăng dần theo t.")
        if len(ts) != len(set(ts)):
            raise ValueError("Tồn tại các giá trị t trùng nhau trong DataSet.")

    @property
    def n(self) -> int:
        """Số điểm dữ liệu."""
        return len(self.points)

    @property
    def y_values(self) -> list[float]:
        """Danh sách giá trị y theo thứ tự."""
        return [p.y for p in self.points]

    @property
    def t_values(self) -> list[int]:
        """Danh sách giá trị t theo thứ tự."""
        return [p.t for p in self.points]

    @property
    def active_points(self) -> list[DataPoint]:
        """Chỉ trả về các điểm không bị đánh dấu là outlier."""
        return [p for p in self.points if not p.is_outlier]

    def is_empty(self) -> bool:
        return self.n == 0

    def to_dict_list(self) -> list[dict]:
        """Serialize sang list[dict] để StateManager lưu."""
        return [{"t": p.t, "y": p.y, "is_outlier": p.is_outlier} for p in self.points]

    @classmethod
    def from_dict_list(cls, data: list[dict], source: str = "manual") -> "DataSet":
        """Phục hồi từ list[dict] đã lưu."""
        points = [DataPoint(t=d["t"], y=d["y"], is_outlier=d.get("is_outlier", False)) for d in data]
        return cls(points=points, source=source)


# Kiểu phương pháp dự báo được hỗ trợ trong Phase 1
MethodName = Literal["naive", "moving_average", "ses", "linear_regression", "holt"]


@dataclass
class ForecastingInput:
    """Tham số đầu vào để chạy một phương pháp dự báo.

    Attributes:
        dataset:     Tập dữ liệu đầu vào.
        method:      Tên phương pháp.
        n_train:     Số kỳ dùng để huấn luyện (1 <= n_train <= dataset.n).
                     Nếu n_train < dataset.n → hold-out validation được kích hoạt.
        alpha:       Tham số san bằng cho SES và Holt (0 < alpha <= 1).
        beta:        Tham số xu hướng cho Holt (0 < beta <= 1).
        k:           Số kỳ cho Moving Average (k >= 1).
        benchmark:   Phương pháp benchmark để tính FVA.
    """

    dataset: DataSet
    method: MethodName
    n_train: int | None = None          # None → dùng toàn bộ dataset
    alpha: float = 0.3                  # SES, Holt
    beta: float = 0.1                   # Holt
    k: int = 3                          # Moving Average
    benchmark: MethodName = "naive"

    def __post_init__(self) -> None:
        if self.dataset.is_empty():
            raise ValueError("Dataset không được rỗng.")
        if self.n_train is None:
            object.__setattr__(self, "n_train", self.dataset.n)
        if not (1 <= self.n_train <= self.dataset.n):  # type: ignore[operator]
            raise ValueError(
                f"n_train={self.n_train} phải nằm trong [1, {self.dataset.n}]."
            )
        if not (0 < self.alpha <= 1):
            raise ValueError(f"alpha={self.alpha} phải nằm trong (0, 1].")
        if not (0 < self.beta <= 1):
            raise ValueError(f"beta={self.beta} phải nằm trong (0, 1].")
        if self.k < 1:
            raise ValueError(f"k={self.k} phải >= 1.")

    @property
    def has_holdout(self) -> bool:
        """True nếu có tập validation (hold-out)."""
        return self.n_train < self.dataset.n  # type: ignore[operator]
