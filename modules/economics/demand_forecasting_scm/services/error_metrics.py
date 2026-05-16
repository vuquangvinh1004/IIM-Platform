"""Error metrics calculator for demand_forecasting_scm.

Tính toán các chỉ số sai số dự báo theo công thức chuẩn SCM:

  e_t       = Y_t - F_t
  MAE       = sum(|e_t|) / n
  RMSE       = sqrt(sum(e_t^2) / n)
  MAPE      = (1/n) * sum(|e_t| / Y_t) * 100
  Bias      = sum(e_t)
  Bias%     = Bias / sum(Y_t) * 100
  TS_t      = sum(e_i, i=1..t) / MAD_t  (MAD ≈ MAE tại thời điểm t)
  FVA       = (1 - MAE_model / MAE_benchmark) * 100%

Module này là pure Python — không phụ thuộc Qt, có thể test headless.
"""
from __future__ import annotations

import math
from typing import Sequence

from ..models.outputs import ErrorMetricsResult


def compute_metrics(
    y: Sequence[float],
    f: Sequence[float | None],
    benchmark_mae: float | None = None,
) -> ErrorMetricsResult:
    """Tính các chỉ số sai số trên một tập dữ liệu.

    Args:
        y:             Danh sách giá trị thực tế Y_t.
        f:             Danh sách giá trị dự báo F_t. None tại các vị trí
                       chưa có dự báo (ví dụ: MA warmup).
        benchmark_mae: MAE của phương pháp benchmark để tính FVA.
                       None → FVA không được tính.

    Returns:
        ErrorMetricsResult với các chỉ số đã tính.

    Raises:
        ValueError: Nếu y và f có độ dài khác nhau.
    """
    if len(y) != len(f):
        raise ValueError(
            f"Độ dài y ({len(y)}) và f ({len(f)}) phải bằng nhau."
        )

    # Chỉ tính trên các kỳ có cả Y_t và F_t hợp lệ
    valid_pairs = [
        (yi, fi)
        for yi, fi in zip(y, f)
        if fi is not None
    ]

    n = len(valid_pairs)
    if n == 0:
        return ErrorMetricsResult(
            n=0,
            mae=0.0,
            rmse=0.0,
            mape=None,
            bias=0.0,
            bias_pct=None,
            fva=None,
        )

    errors = [yi - fi for yi, fi in valid_pairs]
    abs_errors = [abs(e) for e in errors]
    sq_errors = [e * e for e in errors]
    y_valid = [yi for yi, _ in valid_pairs]

    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(sq_errors) / n)
    bias = sum(errors)

    # MAPE — bỏ qua nếu bất kỳ Y_t = 0
    if any(yi == 0 for yi in y_valid):
        mape = None
    else:
        mape = (sum(abs(e) / yi for e, yi in zip(errors, y_valid)) / n) * 100

    # Bias%
    sum_y = sum(y_valid)
    bias_pct = (bias / sum_y * 100) if sum_y != 0 else None

    # FVA
    fva: float | None = None
    if benchmark_mae is not None and benchmark_mae != 0:
        fva = (1 - mae / benchmark_mae) * 100

    return ErrorMetricsResult(
        n=n,
        mae=mae,
        rmse=rmse,
        mape=mape,
        bias=bias,
        bias_pct=bias_pct,
        fva=fva,
    )


def compute_tracking_signal(
    y: Sequence[float],
    f: Sequence[float | None],
) -> list[float | None]:
    """Tính Tracking Signal (TS) tích luỹ theo từng kỳ t.

    TS_t = CumError_t / MAD_t
    trong đó MAD_t ≈ MAE_t = sum(|e_i|, i=1..t) / t

    Returns:
        Danh sách TS_t cùng độ dài với y. None tại kỳ chưa có F_t.
    """
    if len(y) != len(f):
        raise ValueError(f"Độ dài y ({len(y)}) và f ({len(f)}) phải bằng nhau.")

    result: list[float | None] = []
    cum_error = 0.0
    cum_abs_error = 0.0
    count = 0

    for yi, fi in zip(y, f):
        if fi is None:
            result.append(None)
            continue

        e = yi - fi
        cum_error += e
        cum_abs_error += abs(e)
        count += 1

        mad = cum_abs_error / count
        ts = cum_error / mad if mad != 0 else 0.0
        result.append(ts)

    return result


def compute_control_bands(
    e: Sequence[float | None],
    sigmas: tuple[float, ...] = (1.0, 2.0, 3.0),
) -> dict[float, float]:
    """Tính các mức RMSE dùng cho Control Chart.

    Args:
        e:      Danh sách sai số e_t (None được bỏ qua).
        sigmas: Bội số RMSE cần tính, mặc định (1σ, 2σ, 3σ).

    Returns:
        Dict {sigma_multiplier: giá trị ngưỡng tuyệt đối}
        Ví dụ: {1.0: 12.5, 2.0: 25.0, 3.0: 37.5}
    """
    valid_e = [ei for ei in e if ei is not None]
    if not valid_e:
        return {s: 0.0 for s in sigmas}

    n = len(valid_e)
    rmse = math.sqrt(sum(ei * ei for ei in valid_e) / n)
    return {s: s * rmse for s in sigmas}
