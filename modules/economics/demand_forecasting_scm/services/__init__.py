"""Services package for demand_forecasting_scm module."""
from .chart_builder import (
    build_control_chart,
    build_error_chart,
    build_forecast_chart,
    build_tracking_signal_chart,
    build_yt_chart,
)
from .data_analyzer import analyze, detect_outliers
from .error_metrics import compute_control_bands, compute_metrics, compute_tracking_signal
from .forecasting_engine import run, supported_methods

__all__ = [
    # error_metrics
    "compute_metrics",
    "compute_tracking_signal",
    "compute_control_bands",
    # forecasting_engine
    "run",
    "supported_methods",
    # data_analyzer
    "analyze",
    "detect_outliers",
    # chart_builder
    "build_yt_chart",
    "build_forecast_chart",
    "build_error_chart",
    "build_tracking_signal_chart",
    "build_control_chart",
]
