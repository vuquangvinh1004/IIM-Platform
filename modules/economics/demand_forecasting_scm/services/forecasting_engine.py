"""Forecasting engine for demand_forecasting_scm — Phase 1.

Triển khai 5 phương pháp dự báo cho Phase 1:
  - Naive
  - Moving Average (MA)
  - Simple Exponential Smoothing (SES)
  - Linear Regression
  - Holt's Double Exponential Smoothing

Mỗi phương pháp trả về ForecastResult đầy đủ bao gồm:
  - Bảng chi tiết (DetailRow mỗi kỳ)
  - Train metrics (ErrorMetricsResult)
  - Holdout metrics nếu n_train < n_total

Module này là pure Python — không phụ thuộc Qt, có thể test headless.
"""
from __future__ import annotations

import math
from typing import Callable

from ..models.inputs import DataSet, ForecastingInput
from ..models.outputs import DetailRow, ForecastResult
from .error_metrics import compute_metrics

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_detail_rows(
    dataset: DataSet,
    f_values: list[float | None],
) -> list[DetailRow]:
    """Tạo danh sách DetailRow từ dataset và danh sách F_t.

    f_values phải có cùng độ dài với dataset.points.
    None trong f_values tại các kỳ chưa có forecast (warmup).
    """
    rows: list[DetailRow] = []
    cum_bias: float = 0.0

    for point, f_t in zip(dataset.points, f_values):
        yi = point.y

        if f_t is None:
            rows.append(DetailRow(
                t=point.t,
                y_t=yi,
                f_t=None,
                e_t=None,
                e_t_sq=None,
                abs_et_over_yt=None,
                cum_bias=None,
            ))
            continue

        e_t = yi - f_t
        cum_bias += e_t

        abs_et_over_yt: float | None
        if yi != 0:
            abs_et_over_yt = abs(e_t) / yi
        else:
            abs_et_over_yt = None

        rows.append(DetailRow(
            t=point.t,
            y_t=yi,
            f_t=f_t,
            e_t=e_t,
            e_t_sq=e_t * e_t,
            abs_et_over_yt=abs_et_over_yt,
            cum_bias=cum_bias,
        ))

    return rows


def _split_train_holdout(
    f_all: list[float | None], inp: ForecastingInput
) -> tuple[list[float | None], list[float | None]]:
    """Tách f_values thành phần train và holdout."""
    n_train = inp.n_train  # type: ignore[assignment]
    return f_all[:n_train], f_all[n_train:]


def _build_result(
    inp: ForecastingInput,
    f_all: list[float | None],
    method_params: dict,
    fit_info: dict | None = None,
) -> ForecastResult:
    """Tạo ForecastResult đầy đủ từ f_all và input."""
    y_all = inp.dataset.y_values
    n_train = inp.n_train  # type: ignore[assignment]

    # Detail rows trên toàn bộ dataset
    detail_rows = _build_detail_rows(inp.dataset, f_all)

    # Train metrics
    y_train = y_all[:n_train]
    f_train = f_all[:n_train]

    # Tính benchmark MAE để tính FVA
    benchmark_mae: float | None = None
    if inp.benchmark != inp.method:
        try:
            benchmark_result = run(ForecastingInput(
                dataset=inp.dataset,
                method=inp.benchmark,
                n_train=n_train,
                alpha=inp.alpha,
                beta=inp.beta,
                k=inp.k,
                benchmark="naive",  # tránh đệ quy vô hạn
            ))
            bm = benchmark_result.train_metrics
            if bm:
                benchmark_mae = bm.mae
        except Exception:
            pass  # benchmark không tính được → FVA = None

    train_metrics = compute_metrics(y_train, f_train, benchmark_mae=benchmark_mae)

    # Holdout metrics
    holdout_metrics = None
    if inp.has_holdout:
        y_holdout = y_all[n_train:]
        f_holdout = f_all[n_train:]
        holdout_metrics = compute_metrics(y_holdout, f_holdout)

    return ForecastResult(
        method=inp.method,
        detail_rows=detail_rows,
        train_metrics=train_metrics,
        holdout_metrics=holdout_metrics,
        model_params=method_params,
        fit_info=fit_info or {},
    )


# ---------------------------------------------------------------------------
# Phương pháp 1: Naive
# ---------------------------------------------------------------------------


def _naive(inp: ForecastingInput) -> ForecastResult:
    """Naive: F_t = Y_(t-1).

    Kỳ đầu tiên không có forecast (f_t = None).
    """
    y = inp.dataset.y_values
    n = len(y)
    n_train = inp.n_train  # type: ignore[assignment]

    f_all: list[float | None] = [None]  # kỳ 1 không có forecast
    for i in range(1, n):
        f_all.append(y[i - 1])

    # Trên tập holdout: tiếp tục dùng Y_(t-1) — tức last known value
    return _build_result(
        inp, f_all,
        method_params={"n_train": n_train},
    )


# ---------------------------------------------------------------------------
# Phương pháp 2: Moving Average
# ---------------------------------------------------------------------------


def _moving_average(inp: ForecastingInput) -> ForecastResult:
    """Moving Average bậc k: F_t = mean(Y_(t-k), ..., Y_(t-1)).

    k kỳ đầu không có forecast (warmup period).
    """
    y = inp.dataset.y_values
    n = len(y)
    k = inp.k
    n_train = inp.n_train  # type: ignore[assignment]

    f_all: list[float | None] = [None] * k  # warmup
    for i in range(k, n):
        window = y[i - k: i]
        f_all.append(sum(window) / k)

    return _build_result(
        inp, f_all,
        method_params={"n_train": n_train, "k": k},
    )


# ---------------------------------------------------------------------------
# Phương pháp 3: Simple Exponential Smoothing (SES)
# ---------------------------------------------------------------------------


def _ses(inp: ForecastingInput) -> ForecastResult:
    """Simple Exponential Smoothing: F_t+1 = α*Y_t + (1-α)*F_t.

    Khởi tạo: F_1 = Y_1 (không có forecast tại kỳ 1).
    F_2 = α*Y_1 + (1-α)*F_1 = Y_1 (bằng nhau ở bước đầu).

    Theo约定thông thường trong giáo dục SCM:
    - Kỳ 1: F_1 = None (không có dự báo trước khi bắt đầu)
    - Kỳ 2 trở đi: F_t = α*Y_(t-1) + (1-α)*F_(t-1)
    - F_2 được khởi tạo = Y_1
    """
    y = inp.dataset.y_values
    n = len(y)
    alpha = inp.alpha
    n_train = inp.n_train  # type: ignore[assignment]

    f_all: list[float | None] = [None]  # kỳ 1 không có forecast

    # Khởi tạo F_2 = Y_1
    f_prev = y[0]
    for i in range(1, n):
        f_t = alpha * y[i - 1] + (1 - alpha) * f_prev
        f_all.append(f_t)
        f_prev = f_t

    return _build_result(
        inp, f_all,
        method_params={"n_train": n_train, "alpha": alpha},
    )


# ---------------------------------------------------------------------------
# Phương pháp 4: Linear Regression
# ---------------------------------------------------------------------------


def _linear_regression(inp: ForecastingInput) -> ForecastResult:
    """Linear Regression: Y = a*t + b, fit trên n_train điểm đầu.

    Sử dụng numpy.polyfit bậc 1 (OLS bình thường). Sau khi fit, áp dụng
    phương trình để dự báo trên toàn bộ dataset (kể cả holdout).
    """
    import numpy as np  # numpy đã có trong platform stack

    y = inp.dataset.y_values
    t = inp.dataset.t_values
    n = len(y)
    n_train = inp.n_train  # type: ignore[assignment]

    # Fit trên tập train
    t_train = np.array(t[:n_train], dtype=float)
    y_train = np.array(y[:n_train], dtype=float)

    coeffs = np.polyfit(t_train, y_train, 1)  # [slope, intercept]
    a = float(coeffs[0])
    b = float(coeffs[1])

    # Dự báo trên toàn bộ t
    t_all = np.array(t, dtype=float)
    f_all_arr = a * t_all + b
    f_all: list[float | None] = [float(v) for v in f_all_arr]

    # R² trên train
    y_mean_train = float(y_train.mean())
    ss_res = float(((y_train - (a * t_train + b)) ** 2).sum())
    ss_tot = float(((y_train - y_mean_train) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot != 0 else 0.0

    return _build_result(
        inp, f_all,
        method_params={"n_train": n_train},
        fit_info={"slope": a, "intercept": b, "r2": r2},
    )


# ---------------------------------------------------------------------------
# Phương pháp 5: Holt's Double Exponential Smoothing
# ---------------------------------------------------------------------------


def _holt(inp: ForecastingInput) -> ForecastResult:
    """Holt's Double Exponential Smoothing (Trend-adjusted).

    Phương trình:
      L_t = α * Y_t + (1-α) * (L_(t-1) + T_(t-1))   [mức độ]
      T_t = β * (L_t - L_(t-1)) + (1-β) * T_(t-1)    [xu hướng]
      F_{t+1} = L_t + T_t                              [dự báo kỳ tiếp]

    Khởi tạo:
      L_1 = Y_1
      T_1 = Y_2 - Y_1  (nếu n >= 2), ngược lại T_1 = 0

    Kỳ 1 không có forecast (tương tự SES).
    """
    y = inp.dataset.y_values
    n = len(y)
    alpha = inp.alpha
    beta = inp.beta
    n_train = inp.n_train  # type: ignore[assignment]

    if n < 2:
        # Không đủ dữ liệu để khởi tạo Holt — fallback về naive
        return _naive(inp)

    # Khởi tạo
    L = y[0]
    T = y[1] - y[0]

    f_all: list[float | None] = [None]  # kỳ 1 không có forecast

    for i in range(1, n):
        # Dự báo kỳ i (được tính từ L, T của kỳ i-1)
        f_t = L + T
        f_all.append(f_t)

        # Cập nhật L, T dùng Y_i
        yi = y[i]
        L_prev = L
        L = alpha * yi + (1 - alpha) * (L + T)
        T = beta * (L - L_prev) + (1 - beta) * T

    return _build_result(
        inp, f_all,
        method_params={"n_train": n_train, "alpha": alpha, "beta": beta},
    )


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

_METHODS: dict[str, Callable[[ForecastingInput], ForecastResult]] = {
    "naive": _naive,
    "moving_average": _moving_average,
    "ses": _ses,
    "linear_regression": _linear_regression,
    "holt": _holt,
}


def run(inp: ForecastingInput) -> ForecastResult:
    """Chạy phương pháp dự báo được chỉ định trong ForecastingInput.

    Args:
        inp: ForecastingInput đã được validate.

    Returns:
        ForecastResult đầy đủ.

    Raises:
        ValueError: Nếu tên phương pháp không được hỗ trợ.
    """
    method_fn = _METHODS.get(inp.method)
    if method_fn is None:
        supported = ", ".join(sorted(_METHODS.keys()))
        raise ValueError(
            f"Phương pháp '{inp.method}' không được hỗ trợ. "
            f"Các phương pháp hợp lệ: {supported}"
        )
    return method_fn(inp)


def supported_methods() -> list[str]:
    """Danh sách tên phương pháp được hỗ trợ."""
    return sorted(_METHODS.keys())
