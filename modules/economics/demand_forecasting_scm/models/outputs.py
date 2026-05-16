"""Output data models for demand_forecasting_scm.

ErrorMetricsResult — các chỉ số đánh giá sai số
ForecastResult     — kết quả dự báo đầy đủ (bảng chi tiết + metrics)
SuggestionResult   — kết quả phân tích Smart Suggestion
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ErrorMetricsResult:
    """Các chỉ số đánh giá sai số dự báo.

    Tất cả metric được tính trên n điểm có giá trị e_t hợp lệ.

    Attributes:
        n:      Số điểm được tính (n_train hoặc n_holdout).
        mae:    Mean Absolute Error = sum(|e_t|) / n
        rmse:   Root Mean Square Error = sqrt(sum(e_t^2) / n)
        mape:   Mean Absolute Percentage Error = (1/n)*sum(|e_t|/Y_t)*100
                None nếu có Y_t = 0 (tránh chia 0).
        bias:   Cumulative Error = sum(e_t)
        bias_pct: Bias% = bias / sum(Y_t) * 100
        fva:    Forecast Value Added so với benchmark (%).
                FVA = (1 - MAE_model / MAE_benchmark) * 100
                None nếu benchmark chưa được tính.
    """

    n: int
    mae: float
    rmse: float
    mape: float | None
    bias: float
    bias_pct: float | None
    fva: float | None = None


@dataclass
class DetailRow:
    """Một hàng trong bảng chi tiết tính toán.

    Columns: t, Y_t, F_t, e_t, e_t_sq, abs_et_over_yt, cum_bias
    """

    t: int
    y_t: float
    f_t: float | None           # None ở các kỳ chưa có forecast (ví dụ: MA warmup)
    e_t: float | None           # None nếu f_t là None
    e_t_sq: float | None        # e_t^2
    abs_et_over_yt: float | None  # |e_t| / Y_t  (None nếu Y_t = 0 hoặc f_t là None)
    cum_bias: float | None      # cumulative sum of e_t


@dataclass
class ForecastResult:
    """Kết quả đầy đủ của một lần chạy dự báo.

    Attributes:
        method:        Tên phương pháp.
        detail_rows:   Bảng chi tiết t, Yt, Ft, et, et², |et|/Yt, CumBias.
        train_metrics: Metrics trên tập huấn luyện.
        holdout_metrics: Metrics trên tập hold-out (None nếu không có).
        model_params:  Dict các tham số đã dùng (alpha, beta, k, ...).
        fit_info:      Thông tin fit bổ sung tuỳ phương pháp
                       (ví dụ: slope/intercept cho LinReg).
    """

    method: str
    detail_rows: list[DetailRow] = field(default_factory=list)
    train_metrics: ErrorMetricsResult | None = None
    holdout_metrics: ErrorMetricsResult | None = None
    model_params: dict = field(default_factory=dict)
    fit_info: dict = field(default_factory=dict)

    @property
    def f_values(self) -> list[float | None]:
        """Danh sách F_t theo thứ tự t."""
        return [row.f_t for row in self.detail_rows]

    @property
    def e_values(self) -> list[float | None]:
        """Danh sách e_t theo thứ tự t."""
        return [row.e_t for row in self.detail_rows]

    @property
    def cum_bias_values(self) -> list[float | None]:
        """Danh sách cumulative bias theo thứ tự t."""
        return [row.cum_bias for row in self.detail_rows]


# Mức độ gợi ý cho một mẫu hình
SuggestionStrength = Literal["strong", "possible", "none"]


@dataclass
class PatternSuggestion:
    """Gợi ý một mẫu hình cụ thể.

    Attributes:
        pattern:    Tên mẫu hình: "stationary", "trend", "seasonal" (Phase 2).
        strength:   Mức độ gợi ý: "strong" / "possible" / "none".
        evidence:   Mô tả bằng chứng thống kê (để hiển thị tooltip).
        stat_value: Giá trị thống kê chính (p-value ADF, R², ...).
    """

    pattern: str
    strength: SuggestionStrength
    evidence: str
    stat_value: float | None = None


@dataclass
class SuggestionResult:
    """Kết quả phân tích Smart Suggestion cho toàn bộ dataset.

    Attributes:
        suggestions:        Danh sách gợi ý theo từng mẫu hình.
        outlier_indices:    Chỉ số (0-based) các điểm bị phát hiện là outlier.
        outlier_threshold:  Ngưỡng σ đã dùng để phát hiện outlier.
        n_analyzed:         Số điểm đã phân tích.
        warnings:           Cảnh báo nếu n quá nhỏ hoặc dữ liệu bất thường.
    """

    suggestions: list[PatternSuggestion] = field(default_factory=list)
    outlier_indices: list[int] = field(default_factory=list)
    outlier_threshold: float | None = None
    n_analyzed: int = 0
    warnings: list[str] = field(default_factory=list)

    def get(self, pattern: str) -> PatternSuggestion | None:
        """Lấy gợi ý cho một pattern cụ thể."""
        for s in self.suggestions:
            if s.pattern == pattern:
                return s
        return None

    def is_strong(self, pattern: str) -> bool:
        """True nếu gợi ý mẫu hình này là 'strong'."""
        s = self.get(pattern)
        return s is not None and s.strength == "strong"
