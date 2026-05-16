"""Phân tích dữ liệu và Smart Suggestion cho demand_forecasting_scm.

Cung cấp:
- detect_outliers  — phát hiện ngoại lệ bằng z-score
- analyze          — phân tích mẫu hình, trả về SuggestionResult

Không có dependency Qt. Hoàn toàn headless-testable.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from ..models.inputs import DataSet
from ..models.outputs import PatternSuggestion, SuggestionResult

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Các ngưỡng cấu hình mặc định
# ---------------------------------------------------------------------------
_DEFAULT_OUTLIER_SIGMA: float = 2.5
_ADF_P_STRONG: float = 0.05      # p < ngưỡng này → stationary strong
_ADF_P_POSSIBLE: float = 0.10    # p trong [0.05, 0.10) → possible
_TREND_R2_STRONG: float = 0.50   # R² >= 0.50 → trend strong
_TREND_R2_POSSIBLE: float = 0.25 # R² trong [0.25, 0.50) → possible
_MIN_POINTS_ADF: int = 10        # statsmodels ADF cần ít nhất ~10 điểm


# ---------------------------------------------------------------------------
# Outlier detection
# ---------------------------------------------------------------------------

def detect_outliers(
    dataset: DataSet,
    sigma_threshold: float = _DEFAULT_OUTLIER_SIGMA,
) -> list[int]:
    """Phát hiện ngoại lệ theo phương pháp z-score (standard score).

    Args:
        dataset:         Tập dữ liệu cần phân tích.
        sigma_threshold: Điểm ngoại lệ nếu |z| > sigma_threshold.

    Returns:
        Danh sách chỉ số (0-based index trong dataset.points) của các ngoại lệ.
        Trả về danh sách rỗng nếu không đủ dữ liệu (n < 2).
    """
    points = dataset.active_points
    n = len(points)
    if n < 2:
        return []

    y_vals = [p.y for p in points]
    mean = sum(y_vals) / n
    variance = sum((y - mean) ** 2 for y in y_vals) / n
    std = math.sqrt(variance)

    if std == 0.0:
        return []

    outlier_indices: list[int] = []
    for idx, y in enumerate(y_vals):
        z = (y - mean) / std
        if abs(z) > sigma_threshold:
            outlier_indices.append(idx)

    return outlier_indices


# ---------------------------------------------------------------------------
# ADF stationarity test
# ---------------------------------------------------------------------------

def _check_stationarity(y_vals: list[float]) -> PatternSuggestion:
    """Kiểm định ADF để phát hiện tính dừng (stationarity).

    Trả về PatternSuggestion với pattern="stationary".
    Nếu statsmodels không có sẵn, trả về strength="none" với warning.
    """
    n = len(y_vals)
    if n < _MIN_POINTS_ADF:
        return PatternSuggestion(
            pattern="stationary",
            strength="none",
            evidence=f"Không đủ dữ liệu để kiểm định ADF (cần ≥{_MIN_POINTS_ADF}, có {n} điểm).",
            stat_value=None,
        )

    try:
        from statsmodels.tsa.stattools import adfuller  # type: ignore[import-untyped]
    except ImportError:
        return PatternSuggestion(
            pattern="stationary",
            strength="none",
            evidence="statsmodels chưa được cài đặt — không thể kiểm định ADF.",
            stat_value=None,
        )

    try:
        result = adfuller(y_vals, autolag="AIC")
        p_value: float = float(result[1])
    except Exception as exc:  # noqa: BLE001
        return PatternSuggestion(
            pattern="stationary",
            strength="none",
            evidence=f"Không thể chạy ADF: {exc}",
            stat_value=None,
        )

    if p_value < _ADF_P_STRONG:
        strength = "strong"
        desc = f"Chuỗi có tính dừng (ADF p-value = {p_value:.4f} < {_ADF_P_STRONG})."
    elif p_value < _ADF_P_POSSIBLE:
        strength = "possible"
        desc = f"Chuỗi có thể có tính dừng (ADF p-value = {p_value:.4f}, không có ý nghĩa mạnh)."
    else:
        strength = "none"
        desc = f"Chuỗi không có tính dừng (ADF p-value = {p_value:.4f} ≥ {_ADF_P_POSSIBLE})."

    return PatternSuggestion(
        pattern="stationary",
        strength=strength,  # type: ignore[arg-type]
        evidence=desc,
        stat_value=p_value,
    )


# ---------------------------------------------------------------------------
# Trend detection (OLS linear, R²)
# ---------------------------------------------------------------------------

def _check_trend(y_vals: list[float]) -> PatternSuggestion:
    """Phát hiện xu hướng tuyến tính bằng R² của OLS bậc 1.

    Trả về PatternSuggestion với pattern="trend".
    """
    n = len(y_vals)
    if n < 3:
        return PatternSuggestion(
            pattern="trend",
            strength="none",
            evidence=f"Không đủ dữ liệu để phát hiện xu hướng (có {n} điểm).",
            stat_value=None,
        )

    try:
        import numpy as np  # noqa: PLC0415

        t_arr = np.arange(1, n + 1, dtype=float)
        y_arr = np.array(y_vals, dtype=float)
        coeffs = np.polyfit(t_arr, y_arr, 1)
        y_hat = np.polyval(coeffs, t_arr)
        ss_res = float(np.sum((y_arr - y_hat) ** 2))
        ss_tot = float(np.sum((y_arr - y_arr.mean()) ** 2))
        r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
        slope = float(coeffs[0])
    except Exception as exc:  # noqa: BLE001
        return PatternSuggestion(
            pattern="trend",
            strength="none",
            evidence=f"Không thể tính xu hướng: {exc}",
            stat_value=None,
        )

    direction = "tăng" if slope > 0 else "giảm"
    if r2 >= _TREND_R2_STRONG:
        strength = "strong"
        desc = (
            f"Xu hướng {direction} rõ ràng (R² = {r2:.3f} ≥ {_TREND_R2_STRONG}, "
            f"slope = {slope:.3f})."
        )
    elif r2 >= _TREND_R2_POSSIBLE:
        strength = "possible"
        desc = (
            f"Có thể có xu hướng {direction} (R² = {r2:.3f}, chưa đủ mạnh)."
        )
    else:
        strength = "none"
        desc = f"Không phát hiện xu hướng rõ ràng (R² = {r2:.3f} < {_TREND_R2_POSSIBLE})."

    return PatternSuggestion(
        pattern="trend",
        strength=strength,  # type: ignore[arg-type]
        evidence=desc,
        stat_value=r2,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze(
    dataset: DataSet,
    sigma_threshold: float = _DEFAULT_OUTLIER_SIGMA,
) -> SuggestionResult:
    """Phân tích toàn bộ mẫu hình của dataset, trả về SuggestionResult.

    Thực hiện:
    1. Phát hiện ngoại lệ (z-score).
    2. Kiểm định tính dừng (ADF).
    3. Phát hiện xu hướng tuyến tính (R²).

    Args:
        dataset:         Tập dữ liệu cần phân tích (dùng active_points).
        sigma_threshold: Ngưỡng z-score cho outlier detection.

    Returns:
        SuggestionResult với đầy đủ suggestions và thông tin ngoại lệ.
    """
    points = dataset.active_points
    n = len(points)
    y_vals = [p.y for p in points]
    warnings: list[str] = []

    # 1. Outlier detection
    outlier_indices = detect_outliers(dataset, sigma_threshold)
    if outlier_indices:
        warnings.append(
            f"Phát hiện {len(outlier_indices)} điểm ngoại lệ "
            f"(|z| > {sigma_threshold}): kỳ "
            + ", ".join(str(points[i].t) for i in outlier_indices)
            + "."
        )

    # 2. Tính y_vals không bao gồm outlier để phân tích mẫu hình
    clean_y = [y_vals[i] for i in range(n) if i not in set(outlier_indices)]
    analysis_y = clean_y if len(clean_y) >= _MIN_POINTS_ADF else y_vals

    if outlier_indices and len(clean_y) < _MIN_POINTS_ADF:
        warnings.append(
            "Sau khi loại bỏ ngoại lệ, số điểm còn lại quá ít — "
            "phân tích mẫu hình sẽ dùng toàn bộ dữ liệu."
        )

    # 3. Phân tích mẫu hình
    stationarity = _check_stationarity(analysis_y)
    trend = _check_trend(analysis_y)

    return SuggestionResult(
        suggestions=[stationarity, trend],
        outlier_indices=outlier_indices,
        outlier_threshold=sigma_threshold,
        n_analyzed=len(analysis_y),
        warnings=warnings,
    )
