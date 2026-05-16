"""Chart builder — matplotlib Figure factories cho demand_forecasting_scm.

Tất cả hàm đều trả về matplotlib.figure.Figure.
Không có dependency Qt — figure được nhúng vào Qt từ UI layer thông qua
FigureCanvasQTAgg.

Factories:
    build_yt_chart           — Biểu đồ chuỗi thời gian Y_t
    build_forecast_chart     — Y_t + F_t overlay
    build_error_chart        — Sai số e_t theo kỳ
    build_tracking_signal_chart — Tracking signal + ngưỡng
    build_control_chart      — e_t + control bands ±1σ, ±2σ, ±3σ
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
from matplotlib.figure import Figure

# Màu sắc chuẩn cho toàn module (nhất quán giữa các biểu đồ)
_COLOR_YT = "#1f77b4"       # xanh dương — dữ liệu thực tế
_COLOR_FT = "#ff7f0e"       # cam — dự báo
_COLOR_ET = "#d62728"       # đỏ — sai số
_COLOR_TS = "#2ca02c"       # xanh lá — tracking signal
_COLOR_HOLDOUT = "#9467bd"  # tím — holdout region
_COLOR_BAND_1 = "#aec7e8"   # nhạt — ±1σ
_COLOR_BAND_2 = "#ffbb78"   # nhạt cam — ±2σ
_COLOR_BAND_3 = "#ff9896"   # nhạt đỏ — ±3σ

_FIGSIZE_WIDE = (8.0, 3.5)     # biểu đồ rộng (dành cho line chart chính)
_FIGSIZE_NARROW = (8.0, 3.0)   # biểu đồ nhỏ hơn (error / TS)
_FIGSIZE_DIALOG = (9.0, 4.0)   # dành cho dialog


# ---------------------------------------------------------------------------
# build_yt_chart
# ---------------------------------------------------------------------------

def build_yt_chart(
    t_values: list[int],
    y_values: list[float],
    outlier_indices: list[int] | None = None,
    title: str = "Chuỗi thời gian nhu cầu",
) -> "Figure":
    """Biểu đồ đường Y_t, với outlier được đánh dấu bằng marker đặc biệt.

    Args:
        t_values:        Danh sách kỳ t (x-axis).
        y_values:        Danh sách Y_t tương ứng.
        outlier_indices: 0-based index trong y_values của các outlier (optional).
        title:           Tiêu đề biểu đồ.

    Returns:
        matplotlib Figure.
    """
    fig = Figure(figsize=_FIGSIZE_WIDE)
    ax = fig.add_subplot(111)
    ax.plot(t_values, y_values, color=_COLOR_YT, linewidth=1.5,
            marker="o", markersize=3, label=r"$Y_t$ (thực tế)")

    if outlier_indices:
        ox = [t_values[i] for i in outlier_indices if i < len(t_values)]
        oy = [y_values[i] for i in outlier_indices if i < len(y_values)]
        ax.scatter(ox, oy, color="red", zorder=5, s=60,
                   marker="x", linewidths=2, label="Ngoại lệ")

    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Kỳ (t)", fontsize=9)
    ax.set_ylabel("Nhu cầu", fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# build_forecast_chart
# ---------------------------------------------------------------------------

def build_forecast_chart(
    t_values: list[int],
    y_values: list[float],
    f_values: list[float | None],
    n_train: int,
    method_label: str = "Dự báo",
    title: str | None = None,
) -> "Figure":
    """Biểu đồ Y_t (xanh) + F_t (cam), vùng holdout được tô màu.

    Args:
        t_values:     Danh sách kỳ t.
        y_values:     Danh sách Y_t.
        f_values:     Danh sách F_t (có thể chứa None ở warmup).
        n_train:      Số kỳ huấn luyện. Các kỳ sau là holdout.
        method_label: Nhãn cho đường F_t.
        title:        Tiêu đề. Mặc định là "Dự báo: {method_label}".

    Returns:
        matplotlib Figure.
    """
    fig = Figure(figsize=_FIGSIZE_WIDE)
    ax = fig.add_subplot(111)

    # Y_t line
    ax.plot(t_values, y_values, color=_COLOR_YT, linewidth=1.5,
            marker="o", markersize=3, label=r"$Y_t$ (thực tế)")

    # F_t — tách các đoạn None ra để vẽ liên tục
    ft_x = [t for t, f in zip(t_values, f_values) if f is not None]
    ft_y = [f for f in f_values if f is not None]
    if ft_x:
        ax.plot(ft_x, ft_y, color=_COLOR_FT, linewidth=1.5,
                linestyle="--", marker="s", markersize=3,
                label=rf"$F_t$ ({method_label})")

    # Tô vùng holdout
    if n_train < len(t_values):
        holdout_start = t_values[n_train] if n_train < len(t_values) else t_values[-1]
        holdout_end = t_values[-1]
        ax.axvspan(holdout_start - 0.5, holdout_end + 0.5,
                   alpha=0.08, color=_COLOR_HOLDOUT, label="Hold-out")
        ax.axvline(holdout_start - 0.5, color=_COLOR_HOLDOUT,
                   linestyle=":", linewidth=1.0, alpha=0.8)

    ax.set_title(title or f"Dự báo: {method_label}", fontsize=10)
    ax.set_xlabel("Kỳ (t)", fontsize=9)
    ax.set_ylabel("Nhu cầu", fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# build_error_chart
# ---------------------------------------------------------------------------

def build_error_chart(
    t_values: list[int],
    e_values: list[float | None],
    title: str = r"Sai số dự báo ($e_t = Y_t - F_t$)",
) -> "Figure":
    """Biểu đồ thanh sai số e_t theo từng kỳ.

    Args:
        t_values: Danh sách kỳ t.
        e_values: Danh sách e_t (None cho kỳ chưa có dự báo).
        title:    Tiêu đề.

    Returns:
        matplotlib Figure.
    """
    fig = Figure(figsize=_FIGSIZE_NARROW)
    ax = fig.add_subplot(111)

    valid_t = [t for t, e in zip(t_values, e_values) if e is not None]
    valid_e = [e for e in e_values if e is not None]

    if valid_t:
        colors = [_COLOR_ET if e < 0 else _COLOR_FT for e in valid_e]
        ax.bar(valid_t, valid_e, color=colors, alpha=0.75, width=0.6)
        ax.axhline(0, color="black", linewidth=0.8, linestyle="-")

    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Kỳ (t)", fontsize=9)
    ax.set_ylabel(r"$e_t$", fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4, axis="y")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# build_tracking_signal_chart
# ---------------------------------------------------------------------------

def build_tracking_signal_chart(
    t_values: list[int],
    ts_values: list[float | None],
    upper_limit: float = 4.0,
    lower_limit: float | None = None,
    title: str = "Tracking Signal",
) -> "Figure":
    """Biểu đồ Tracking Signal với đường giới hạn.

    Args:
        t_values:    Danh sách kỳ t.
        ts_values:   Giá trị TS_t (None cho kỳ chưa có).
        upper_limit: Giới hạn trên (mặc định ±4.0 theo nguyên tắc).
        lower_limit: Giới hạn dưới. Nếu None, dùng -upper_limit.
        title:       Tiêu đề.

    Returns:
        matplotlib Figure.
    """
    lower_limit = lower_limit if lower_limit is not None else -upper_limit

    fig = Figure(figsize=_FIGSIZE_NARROW)
    ax = fig.add_subplot(111)

    valid_t = [t for t, ts in zip(t_values, ts_values) if ts is not None]
    valid_ts = [ts for ts in ts_values if ts is not None]

    if valid_t:
        ax.plot(valid_t, valid_ts, color=_COLOR_TS, linewidth=1.5,
                marker="o", markersize=3, label=r"$TS_t$")
        # Tô vùng vi phạm
        for t, ts_val in zip(valid_t, valid_ts):
            if ts_val > upper_limit or ts_val < lower_limit:
                ax.scatter([t], [ts_val], color="red", zorder=5, s=60)

    ax.axhline(upper_limit, color="red", linestyle="--",
               linewidth=1.0, label=f"+{upper_limit} (giới hạn)")
    ax.axhline(lower_limit, color="red", linestyle="--",
               linewidth=1.0, label=f"{lower_limit} (giới hạn)")
    ax.axhline(0, color="black", linewidth=0.7, linestyle="-")

    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Kỳ (t)", fontsize=9)
    ax.set_ylabel(r"$TS_t$", fontsize=9)
    ax.legend(fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.4)
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# build_control_chart
# ---------------------------------------------------------------------------

def build_control_chart(
    t_values: list[int],
    e_values: list[float | None],
    bands: dict[float, float],
    title: str = "Biểu đồ kiểm soát sai số",
) -> "Figure":
    """Biểu đồ e_t với các dải kiểm soát ±1σ, ±2σ, ±3σ.

    Args:
        t_values: Danh sách kỳ t.
        e_values: Danh sách e_t (None cho kỳ chưa có dự báo).
        bands:    Dict {sigma_level → threshold} từ compute_control_bands().
                  Ví dụ: {1.0: 5.2, 2.0: 10.4, 3.0: 15.6}
        title:    Tiêu đề.

    Returns:
        matplotlib Figure.
    """
    import matplotlib.patches as mpatches  # noqa: PLC0415

    fig = Figure(figsize=_FIGSIZE_DIALOG)
    ax = fig.add_subplot(111)

    valid_t = [t for t, e in zip(t_values, e_values) if e is not None]
    valid_e = [e for e in e_values if e is not None]

    # Dải màu — từ ngoài vào trong (3σ → 2σ → 1σ)
    band_config = [
        (3.0, _COLOR_BAND_3, "±3σ"),
        (2.0, _COLOR_BAND_2, "±2σ"),
        (1.0, _COLOR_BAND_1, "±1σ"),
    ]

    legend_patches = []
    for sigma, color, label in band_config:
        if sigma in bands:
            threshold = bands[sigma]
            ax.axhspan(-threshold, threshold, alpha=0.25,
                       color=color, zorder=0)
            ax.axhline(threshold, color=color, linewidth=0.8,
                       linestyle="--", zorder=1)
            ax.axhline(-threshold, color=color, linewidth=0.8,
                       linestyle="--", zorder=1)
            legend_patches.append(
                mpatches.Patch(color=color, alpha=0.5, label=label)
            )

    if valid_t:
        ax.plot(valid_t, valid_e, color=_COLOR_ET, linewidth=1.5,
                marker="o", markersize=3, label=r"$e_t$", zorder=2)

    ax.axhline(0, color="black", linewidth=0.8, linestyle="-", zorder=1)

    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Kỳ (t)", fontsize=9)
    ax.set_ylabel(r"$e_t = Y_t - F_t$", fontsize=9)

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles=handles + legend_patches,
              labels=labels + [p.get_label() for p in legend_patches],
              fontsize=9)
    ax.grid(True, linestyle="--", alpha=0.3, zorder=0)
    fig.tight_layout()
    return fig
