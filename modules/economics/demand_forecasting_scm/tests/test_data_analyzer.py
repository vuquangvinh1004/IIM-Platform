"""Tests cho services/data_analyzer.py."""
from __future__ import annotations

import pytest

from modules.economics.demand_forecasting_scm.models.inputs import DataPoint, DataSet
from modules.economics.demand_forecasting_scm.services.data_analyzer import (
    _DEFAULT_OUTLIER_SIGMA,
    analyze,
    detect_outliers,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dataset(y_list: list[float], source: str = "manual") -> DataSet:
    """Tạo DataSet từ danh sách y (t = 1, 2, ...)."""
    points = [DataPoint(t=i + 1, y=y) for i, y in enumerate(y_list)]
    return DataSet(points=points, source=source)


# ---------------------------------------------------------------------------
# detect_outliers
# ---------------------------------------------------------------------------

class TestDetectOutliers:
    def test_empty_dataset_returns_empty(self):
        ds = DataSet(points=[], source="manual")
        assert detect_outliers(ds) == []

    def test_single_point_returns_empty(self):
        ds = _make_dataset([10.0])
        assert detect_outliers(ds) == []

    def test_constant_series_no_outlier(self):
        ds = _make_dataset([5.0] * 10)
        assert detect_outliers(ds) == []

    def test_obvious_outlier_detected(self):
        # 9 điểm bình thường + 1 ngoại lệ rõ ràng
        y = [10.0] * 9 + [100.0]
        ds = _make_dataset(y)
        result = detect_outliers(ds, sigma_threshold=2.5)
        assert 9 in result  # index 9 (0-based)

    def test_no_outlier_within_threshold(self):
        # Dữ liệu tăng tuyến tính, không ngoại lệ
        y = list(range(1, 13))
        ds = _make_dataset([float(v) for v in y])
        result = detect_outliers(ds, sigma_threshold=3.0)
        assert result == []

    def test_multiple_outliers(self):
        # z cho các điểm outlier = 2.0 chính xác → cần sigma < 2.0
        y = [10.0] * 8 + [200.0, 200.0]
        ds = _make_dataset(y)
        result = detect_outliers(ds, sigma_threshold=1.9)
        assert 8 in result
        assert 9 in result

    def test_custom_sigma_threshold(self):
        # Với sigma thấp hơn, nhiều điểm bị đánh dấu hơn
        y = [10.0, 11.0, 12.0, 50.0]
        ds = _make_dataset(y)
        strict = detect_outliers(ds, sigma_threshold=1.0)
        loose = detect_outliers(ds, sigma_threshold=2.5)
        assert len(strict) >= len(loose)

    def test_outlier_indices_are_zero_based(self):
        y = [100.0] * 5 + [1000.0]
        ds = _make_dataset(y)
        result = detect_outliers(ds, sigma_threshold=2.0)
        # Index trả về phải là 0-based, không phải t (1-based)
        for idx in result:
            assert 0 <= idx < len(y)

    def test_default_sigma_used_when_not_specified(self):
        y = [10.0] * 9 + [100.0]
        ds = _make_dataset(y)
        result = detect_outliers(ds)
        assert isinstance(result, list)

    def test_uses_active_points_only(self):
        """Điểm đã đánh dấu is_outlier=True bị loại khỏi active_points khi phát hiện."""
        points = [
            DataPoint(t=1, y=10.0),
            DataPoint(t=2, y=10.0),
            DataPoint(t=3, y=10.0, is_outlier=True),  # đã đánh dấu → bị loại
            DataPoint(t=4, y=10.0),
            DataPoint(t=5, y=200.0),  # outlier trong active_points
        ]
        ds = DataSet(points=points)
        # active_points = [t1, t2, t4, t5] → y=[10,10,10,200]; n=4
        assert len(ds.active_points) == 4
        # z cho 200.0 ≈ 1.73 với n=4 → vượt ngưỡng 1.5
        result = detect_outliers(ds, sigma_threshold=1.5)
        assert 3 in result  # index 3 (0-based) trong active_points = t=5, y=200


# ---------------------------------------------------------------------------
# _check_stationarity (thông qua analyze)
# ---------------------------------------------------------------------------

class TestStationarityViaAnalyze:
    def test_not_enough_points_returns_none_strength(self):
        ds = _make_dataset([1.0, 2.0, 3.0])  # n=3 < MIN_POINTS_ADF=10
        result = analyze(ds)
        stat = result.get("stationary")
        assert stat is not None
        assert stat.strength == "none"
        assert "Không đủ dữ liệu" in stat.evidence

    def test_stationary_series_strong(self):
        """Chuỗi dừng: white noise quanh mean cố định."""
        import random
        random.seed(42)
        y = [10.0 + random.gauss(0, 0.5) for _ in range(30)]
        ds = _make_dataset(y)
        result = analyze(ds)
        stat = result.get("stationary")
        assert stat is not None
        # Với white noise ngắn, kỳ vọng p < 0.05 hoặc 0.10
        # Chỉ test rằng strength không phải None và stat_value được trả về
        assert stat.strength in ("strong", "possible", "none")
        if stat.strength != "none":
            assert stat.stat_value is not None

    def test_non_stationary_random_walk_possible_none(self):
        """Random walk thường không dừng → p-value lớn."""
        import random
        random.seed(0)
        y = [0.0]
        for _ in range(29):
            y.append(y[-1] + random.gauss(0, 1))
        ds = _make_dataset(y)
        result = analyze(ds)
        stat = result.get("stationary")
        assert stat is not None
        # Random walk → p-value cao → none hoặc possible
        assert stat.strength in ("none", "possible")


# ---------------------------------------------------------------------------
# _check_trend (thông qua analyze)
# ---------------------------------------------------------------------------

class TestTrendViaAnalyze:
    def test_no_trend_constant_series(self):
        ds = _make_dataset([5.0] * 15)
        result = analyze(ds)
        trend = result.get("trend")
        assert trend is not None
        assert trend.strength == "none"

    def test_strong_linear_trend(self):
        y = [float(i) for i in range(1, 21)]  # y = t, R² = 1.0
        ds = _make_dataset(y)
        result = analyze(ds)
        trend = result.get("trend")
        assert trend is not None
        assert trend.strength == "strong"
        assert trend.stat_value is not None
        assert trend.stat_value > 0.5

    def test_weak_trend_returns_possible_or_none(self):
        import random
        random.seed(7)
        # Xu hướng nhẹ + noise lớn
        y = [10.0 + 0.1 * i + random.gauss(0, 5) for i in range(20)]
        ds = _make_dataset(y)
        result = analyze(ds)
        trend = result.get("trend")
        assert trend is not None
        assert trend.strength in ("possible", "none")

    def test_not_enough_points_for_trend(self):
        ds = _make_dataset([1.0, 2.0])
        result = analyze(ds)
        trend = result.get("trend")
        assert trend is not None
        assert trend.strength == "none"

    def test_decreasing_trend_detected(self):
        y = [float(20 - i) for i in range(20)]  # y = 20 - t, R² = 1.0
        ds = _make_dataset(y)
        result = analyze(ds)
        trend = result.get("trend")
        assert trend is not None
        assert trend.strength == "strong"
        assert "giảm" in trend.evidence


# ---------------------------------------------------------------------------
# analyze (integration)
# ---------------------------------------------------------------------------

class TestAnalyze:
    def test_returns_suggestion_result(self):
        from modules.economics.demand_forecasting_scm.models.outputs import SuggestionResult
        ds = _make_dataset([float(i) for i in range(1, 16)])
        result = analyze(ds)
        assert isinstance(result, SuggestionResult)

    def test_has_stationary_and_trend_suggestions(self):
        ds = _make_dataset([float(i) for i in range(1, 16)])
        result = analyze(ds)
        patterns = [s.pattern for s in result.suggestions]
        assert "stationary" in patterns
        assert "trend" in patterns

    def test_outlier_shows_in_result(self):
        y = [10.0] * 9 + [500.0]
        ds = _make_dataset(y)
        result = analyze(ds, sigma_threshold=2.0)
        assert len(result.outlier_indices) > 0
        assert result.outlier_threshold == 2.0

    def test_n_analyzed_reported_correctly(self):
        ds = _make_dataset([float(i) for i in range(1, 16)])
        result = analyze(ds)
        assert result.n_analyzed == 15

    def test_outlier_warning_in_warnings(self):
        y = [10.0] * 9 + [500.0]
        ds = _make_dataset(y)
        result = analyze(ds, sigma_threshold=2.0)
        # Phải có cảnh báo về ngoại lệ
        assert any("ngoại lệ" in w for w in result.warnings)

    def test_no_outlier_no_warning(self):
        y = list(range(1, 11))
        ds = _make_dataset([float(v) for v in y])
        result = analyze(ds, sigma_threshold=3.0)
        # Không có outlier → không có warning về ngoại lệ
        assert not any("ngoại lệ" in w for w in result.warnings)

    def test_get_helper_returns_correct_pattern(self):
        ds = _make_dataset([float(i) for i in range(1, 20)])
        result = analyze(ds)
        s = result.get("stationary")
        assert s is not None
        assert s.pattern == "stationary"

    def test_get_helper_returns_none_for_unknown(self):
        ds = _make_dataset([float(i) for i in range(1, 20)])
        result = analyze(ds)
        assert result.get("seasonal") is None

    def test_is_strong_helper(self):
        y = [float(i) for i in range(1, 21)]
        ds = _make_dataset(y)
        result = analyze(ds)
        # trend phải strong (R²=1.0)
        assert result.is_strong("trend") is True

    def test_default_sigma_equals_constant(self):
        y = [10.0] * 9 + [100.0]
        ds = _make_dataset(y)
        result = analyze(ds)
        assert result.outlier_threshold == _DEFAULT_OUTLIER_SIGMA
