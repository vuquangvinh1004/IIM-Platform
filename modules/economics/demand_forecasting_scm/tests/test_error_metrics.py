"""Tests for services/error_metrics.py."""
from __future__ import annotations

import math

import pytest

from modules.economics.demand_forecasting_scm.services.error_metrics import (
    compute_control_bands,
    compute_metrics,
    compute_tracking_signal,
)


# ---------------------------------------------------------------------------
# compute_metrics
# ---------------------------------------------------------------------------


class TestComputeMetrics:
    def test_perfect_forecast(self):
        y = [100.0, 110.0, 120.0]
        f = [100.0, 110.0, 120.0]
        m = compute_metrics(y, f)
        assert m.mae == 0.0
        assert m.rmse == 0.0
        assert m.mape == 0.0
        assert m.bias == 0.0
        assert m.fva is None  # no benchmark

    def test_constant_error(self):
        """e_t = 10 tại mọi kỳ."""
        y = [100.0, 200.0, 300.0]
        f = [90.0, 190.0, 290.0]
        m = compute_metrics(y, f)

        assert m.mae == pytest.approx(10.0)
        assert m.rmse == pytest.approx(10.0)
        assert m.bias == pytest.approx(30.0)   # 3 * 10
        # MAPE = (10/100 + 10/200 + 10/300) / 3 * 100
        expected_mape = ((10 / 100 + 10 / 200 + 10 / 300) / 3) * 100
        assert m.mape == pytest.approx(expected_mape)

    def test_mixed_sign_errors(self):
        """errors: +5, -5 → bias = 0, MAE = 5."""
        y = [100.0, 100.0]
        f = [95.0, 105.0]
        m = compute_metrics(y, f)
        assert m.mae == pytest.approx(5.0)
        assert m.bias == pytest.approx(0.0)

    def test_none_forecasts_skipped(self):
        """Kỳ đầu f = None → chỉ tính trên 2 kỳ còn lại."""
        y = [100.0, 200.0, 300.0]
        f = [None, 190.0, 290.0]
        m = compute_metrics(y, f)
        assert m.n == 2
        assert m.mae == pytest.approx(10.0)

    def test_all_none_returns_zeros(self):
        y = [100.0, 200.0]
        f = [None, None]
        m = compute_metrics(y, f)
        assert m.n == 0
        assert m.mae == 0.0

    def test_mape_none_when_yt_zero(self):
        y = [100.0, 0.0, 200.0]
        f = [90.0, 10.0, 180.0]
        m = compute_metrics(y, f)
        assert m.mape is None

    def test_fva_positive_when_better_than_benchmark(self):
        y = [100.0, 200.0, 300.0]
        f = [99.0, 199.0, 299.0]       # MAE = 1
        m = compute_metrics(y, f, benchmark_mae=10.0)
        # FVA = (1 - 1/10) * 100 = 90%
        assert m.fva == pytest.approx(90.0)

    def test_fva_negative_when_worse_than_benchmark(self):
        y = [100.0, 200.0]
        f = [80.0, 180.0]              # MAE = 20
        m = compute_metrics(y, f, benchmark_mae=5.0)
        # FVA = (1 - 20/5) * 100 = -300%
        assert m.fva == pytest.approx(-300.0)

    def test_bias_pct(self):
        y = [100.0, 200.0]
        f = [90.0, 190.0]    # e = 10, 10 → bias = 20, sum_y = 300
        m = compute_metrics(y, f)
        assert m.bias_pct == pytest.approx(20.0 / 300.0 * 100)

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError, match="(?i)độ dài"):
            compute_metrics([1.0, 2.0], [1.0])

    def test_rmse_formula(self):
        """RMSE = sqrt(sum(e^2)/n): e = [3, 4] → sqrt((9+16)/2) = sqrt(12.5)."""
        y = [103.0, 104.0]
        f = [100.0, 100.0]
        m = compute_metrics(y, f)
        assert m.rmse == pytest.approx(math.sqrt(12.5))


# ---------------------------------------------------------------------------
# compute_tracking_signal
# ---------------------------------------------------------------------------


class TestComputeTrackingSignal:
    def test_positive_bias_ts_increases(self):
        """Khi Yt > Ft liên tục → TS dương và tăng."""
        y = [110.0, 120.0, 130.0]
        f = [100.0, 100.0, 100.0]
        ts = compute_tracking_signal(y, f)
        valid = [v for v in ts if v is not None]
        assert all(v > 0 for v in valid)

    def test_none_propagates(self):
        y = [100.0, 200.0, 300.0]
        f = [None, 190.0, 290.0]
        ts = compute_tracking_signal(y, f)
        assert ts[0] is None
        assert ts[1] is not None
        assert ts[2] is not None

    def test_zero_error_ts_zero(self):
        y = [100.0, 200.0]
        f = [100.0, 200.0]
        ts = compute_tracking_signal(y, f)
        assert all(v == pytest.approx(0.0) for v in ts if v is not None)

    def test_same_length_as_input(self):
        y = [1.0, 2.0, 3.0, 4.0, 5.0]
        f = [1.0, 2.0, 3.0, 4.0, 5.0]
        ts = compute_tracking_signal(y, f)
        assert len(ts) == 5

    def test_mismatched_lengths_raise(self):
        with pytest.raises(ValueError):
            compute_tracking_signal([1.0, 2.0], [1.0])


# ---------------------------------------------------------------------------
# compute_control_bands
# ---------------------------------------------------------------------------


class TestComputeControlBands:
    def test_default_sigma_bands(self):
        """RMSE = 10 → bands = {1.0: 10, 2.0: 20, 3.0: 30}."""
        # e_t = 10 mọi kỳ → RMSE = 10
        e = [10.0] * 10
        bands = compute_control_bands(e)
        assert bands[1.0] == pytest.approx(10.0)
        assert bands[2.0] == pytest.approx(20.0)
        assert bands[3.0] == pytest.approx(30.0)

    def test_empty_errors_returns_zeros(self):
        bands = compute_control_bands([None, None])
        assert all(v == 0.0 for v in bands.values())

    def test_custom_sigmas(self):
        e = [5.0] * 4   # RMSE = 5
        bands = compute_control_bands(e, sigmas=(1.5, 2.5))
        assert bands[1.5] == pytest.approx(7.5)
        assert bands[2.5] == pytest.approx(12.5)

    def test_none_values_skipped(self):
        e = [None, 10.0, 10.0, None]  # 2 valid → RMSE = 10
        bands = compute_control_bands(e)
        assert bands[1.0] == pytest.approx(10.0)
