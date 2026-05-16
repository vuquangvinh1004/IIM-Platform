"""Tests for services/forecasting_engine.py — tất cả 5 phương pháp Phase 1."""
from __future__ import annotations

import pytest

from modules.economics.demand_forecasting_scm.models.inputs import (
    DataPoint,
    DataSet,
    ForecastingInput,
)
from modules.economics.demand_forecasting_scm.services.forecasting_engine import (
    run,
    supported_methods,
)


# ---------------------------------------------------------------------------
# Fixtures dùng chung
# ---------------------------------------------------------------------------


def _make_dataset(values: list[float]) -> DataSet:
    return DataSet(points=[DataPoint(t=i + 1, y=v) for i, v in enumerate(values)])


# Dữ liệu ổn định — không có xu hướng rõ ràng
STATIONARY_DATA = [120.0, 130.0, 125.0, 115.0, 128.0, 122.0, 127.0, 119.0, 124.0, 121.0]

# Dữ liệu có xu hướng tuyến tính tăng
TREND_DATA = [100.0, 105.0, 110.0, 115.0, 120.0, 125.0, 130.0, 135.0, 140.0, 145.0]


# ---------------------------------------------------------------------------
# supported_methods
# ---------------------------------------------------------------------------


def test_supported_methods_returns_phase1_list():
    methods = supported_methods()
    for expected in ["naive", "moving_average", "ses", "linear_regression", "holt"]:
        assert expected in methods


def test_unsupported_method_raises():
    ds = _make_dataset(STATIONARY_DATA)
    inp = ForecastingInput(dataset=ds, method="arima")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="không được hỗ trợ"):
        run(inp)


# ---------------------------------------------------------------------------
# Naive
# ---------------------------------------------------------------------------


class TestNaive:
    def _run(self, values: list[float], n_train: int | None = None) -> object:
        ds = _make_dataset(values)
        inp = ForecastingInput(dataset=ds, method="naive", n_train=n_train)
        return run(inp)

    def test_first_period_has_no_forecast(self):
        result = self._run(STATIONARY_DATA)
        assert result.detail_rows[0].f_t is None

    def test_naive_equals_previous_yt(self):
        result = self._run(STATIONARY_DATA)
        rows = result.detail_rows
        for i in range(1, len(rows)):
            assert rows[i].f_t == pytest.approx(rows[i - 1].y_t)

    def test_train_metrics_computed(self):
        result = self._run(STATIONARY_DATA)
        m = result.train_metrics
        assert m is not None
        assert m.n == len(STATIONARY_DATA) - 1   # kỳ 1 không có forecast
        assert m.mae >= 0

    def test_holdout_metrics_when_n_train_less(self):
        result = self._run(STATIONARY_DATA, n_train=7)
        assert result.holdout_metrics is not None
        assert result.holdout_metrics.n > 0

    def test_no_holdout_when_n_train_full(self):
        result = self._run(STATIONARY_DATA)
        assert result.holdout_metrics is None

    def test_result_method_name(self):
        result = self._run(STATIONARY_DATA)
        assert result.method == "naive"


# ---------------------------------------------------------------------------
# Moving Average
# ---------------------------------------------------------------------------


class TestMovingAverage:
    def _run(self, values: list[float], k: int = 3, n_train: int | None = None) -> object:
        ds = _make_dataset(values)
        inp = ForecastingInput(dataset=ds, method="moving_average", k=k, n_train=n_train)
        return run(inp)

    def test_warmup_periods_have_no_forecast(self):
        result = self._run(STATIONARY_DATA, k=3)
        rows = result.detail_rows
        for i in range(3):
            assert rows[i].f_t is None

    def test_forecast_equals_mean_of_k_previous(self):
        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        result = self._run(values, k=3)
        rows = result.detail_rows
        # F_4 = mean(Y1, Y2, Y3) = mean(10, 20, 30) = 20
        assert rows[3].f_t == pytest.approx(20.0)
        # F_5 = mean(Y2, Y3, Y4) = mean(20, 30, 40) = 30
        assert rows[4].f_t == pytest.approx(30.0)

    def test_k1_equivalent_to_naive_shifted(self):
        """MA(1) = F_t = Y_(t-1), tương đương Naive nhưng không bắt đầu từ None."""
        values = [100.0, 110.0, 120.0, 130.0]
        result = self._run(values, k=1)
        rows = result.detail_rows
        assert rows[0].f_t is None
        assert rows[1].f_t == pytest.approx(100.0)

    def test_metrics_only_on_valid_rows(self):
        result = self._run(STATIONARY_DATA, k=3)
        m = result.train_metrics
        assert m is not None
        assert m.n == len(STATIONARY_DATA) - 3   # 3 warmup rows

    def test_model_params_recorded(self):
        result = self._run(STATIONARY_DATA, k=4)
        assert result.model_params["k"] == 4


# ---------------------------------------------------------------------------
# Simple Exponential Smoothing (SES)
# ---------------------------------------------------------------------------


class TestSES:
    def _run(self, values: list[float], alpha: float = 0.3, n_train: int | None = None):
        ds = _make_dataset(values)
        inp = ForecastingInput(dataset=ds, method="ses", alpha=alpha, n_train=n_train)
        return run(inp)

    def test_first_period_no_forecast(self):
        result = self._run(STATIONARY_DATA)
        assert result.detail_rows[0].f_t is None

    def test_second_period_equals_y1(self):
        """F_2 được khởi tạo = Y_1 (init convention)."""
        values = [100.0, 200.0, 150.0]
        result = self._run(values, alpha=0.3)
        # F_2 = alpha*Y_1 + (1-alpha)*F_1 = 0.3*100 + 0.7*100 = 100
        assert result.detail_rows[1].f_t == pytest.approx(100.0)

    def test_alpha_1_makes_ses_equal_naive(self):
        """alpha=1 → F_t = Y_(t-1) → identical to naive."""
        values = [50.0, 60.0, 70.0, 80.0]
        result_ses = self._run(values, alpha=1.0)
        ds = _make_dataset(values)
        inp_naive = ForecastingInput(dataset=ds, method="naive")
        result_naive = run(inp_naive)
        for i in range(1, len(values)):
            ses_ft = result_ses.detail_rows[i].f_t
            naive_ft = result_naive.detail_rows[i].f_t
            if ses_ft is not None and naive_ft is not None:
                assert ses_ft == pytest.approx(naive_ft)

    def test_model_params_recorded(self):
        result = self._run(STATIONARY_DATA, alpha=0.25)
        assert result.model_params["alpha"] == pytest.approx(0.25)

    def test_holdout_computed(self):
        result = self._run(STATIONARY_DATA, n_train=7)
        assert result.holdout_metrics is not None


# ---------------------------------------------------------------------------
# Linear Regression
# ---------------------------------------------------------------------------


class TestLinearRegression:
    def _run(self, values: list[float], n_train: int | None = None):
        ds = _make_dataset(values)
        inp = ForecastingInput(dataset=ds, method="linear_regression", n_train=n_train)
        return run(inp)

    def test_perfect_linear_data(self):
        """Dữ liệu tuyến tính hoàn hảo → sai số = 0."""
        values = [10.0 * i for i in range(1, 11)]  # y = 10t
        result = self._run(values)
        for row in result.detail_rows:
            assert row.f_t == pytest.approx(row.y_t, abs=1e-6)

    def test_fit_info_contains_slope_intercept_r2(self):
        result = self._run(TREND_DATA)
        fi = result.fit_info
        assert "slope" in fi
        assert "intercept" in fi
        assert "r2" in fi

    def test_r2_near_1_for_trend_data(self):
        result = self._run(TREND_DATA)
        assert result.fit_info["r2"] == pytest.approx(1.0, abs=1e-4)

    def test_all_periods_have_forecast(self):
        """Linear Regression không có warmup — tất cả kỳ đều có F_t."""
        result = self._run(TREND_DATA)
        for row in result.detail_rows:
            assert row.f_t is not None

    def test_holdout_computed(self):
        result = self._run(TREND_DATA, n_train=7)
        assert result.holdout_metrics is not None
        assert result.holdout_metrics.n == 3


# ---------------------------------------------------------------------------
# Holt's Model
# ---------------------------------------------------------------------------


class TestHolt:
    def _run(self, values: list[float], alpha: float = 0.3, beta: float = 0.1,
             n_train: int | None = None):
        ds = _make_dataset(values)
        inp = ForecastingInput(dataset=ds, method="holt", alpha=alpha, beta=beta, n_train=n_train)
        return run(inp)

    def test_first_period_no_forecast(self):
        result = self._run(TREND_DATA)
        assert result.detail_rows[0].f_t is None

    def test_second_period_equals_y1_plus_initial_trend(self):
        """F_2 = L_1 + T_1 = Y_1 + (Y_2 - Y_1) = Y_2."""
        values = [100.0, 110.0, 120.0]
        result = self._run(values, alpha=0.3, beta=0.1)
        # F_2 = L_1 + T_1 = 100 + (110-100) = 110
        assert result.detail_rows[1].f_t == pytest.approx(110.0)

    def test_holt_tracks_trend_data_better_than_ses(self):
        """Trên dữ liệu có xu hướng, Holt nên có MAE thấp hơn SES (alpha=0.3)."""
        ds = _make_dataset(TREND_DATA)
        result_holt = run(ForecastingInput(dataset=ds, method="holt", alpha=0.5, beta=0.5))
        result_ses = run(ForecastingInput(dataset=ds, method="ses", alpha=0.3))
        holt_mae = result_holt.train_metrics.mae  # type: ignore[union-attr]
        ses_mae = result_ses.train_metrics.mae    # type: ignore[union-attr]
        assert holt_mae < ses_mae

    def test_model_params_recorded(self):
        result = self._run(TREND_DATA, alpha=0.4, beta=0.2)
        assert result.model_params["alpha"] == pytest.approx(0.4)
        assert result.model_params["beta"] == pytest.approx(0.2)

    def test_single_data_point_falls_back(self):
        """Holt với 1 điểm dữ liệu không đủ — không được crash."""
        result = self._run([100.0])
        assert result is not None

    def test_holdout_computed(self):
        result = self._run(TREND_DATA, n_train=7)
        assert result.holdout_metrics is not None


# ---------------------------------------------------------------------------
# Kiểm tra chung: detail_rows
# ---------------------------------------------------------------------------


class TestDetailRows:
    def _naive_result(self):
        ds = _make_dataset(STATIONARY_DATA)
        inp = ForecastingInput(dataset=ds, method="naive")
        return run(inp)

    def test_cum_bias_cumulative(self):
        """CumBias tại kỳ k phải bằng sum(e_t, t=1..k) cho các kỳ có F_t."""
        result = self._naive_result()
        cum = 0.0
        for row in result.detail_rows:
            if row.e_t is not None:
                cum += row.e_t
                assert row.cum_bias == pytest.approx(cum)

    def test_e_t_square_equals_e_t_squared(self):
        result = self._naive_result()
        for row in result.detail_rows:
            if row.e_t is not None:
                assert row.e_t_sq == pytest.approx(row.e_t ** 2)

    def test_abs_et_over_yt_formula(self):
        result = self._naive_result()
        for row in result.detail_rows:
            if row.e_t is not None and row.y_t != 0:
                expected = abs(row.e_t) / row.y_t
                assert row.abs_et_over_yt == pytest.approx(expected)

    def test_detail_rows_length_equals_dataset(self):
        result = self._naive_result()
        assert len(result.detail_rows) == len(STATIONARY_DATA)
