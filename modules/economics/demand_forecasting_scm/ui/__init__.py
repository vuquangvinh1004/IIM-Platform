"""UI package for demand_forecasting_scm module."""
from .config_dialog import ConfigDialog
from .control_dialog import ControlDialog
from .data_hub_tab import DataHubTab, DataInputDialog
from .forecast_dialog import ForecastDialog
from .main_view import MainView
from .method_view import MethodView
from .stationary_tab import StationaryTab
from .trend_tab import TrendTab

__all__ = [
    "ConfigDialog",
    "ControlDialog",
    "DataHubTab",
    "DataInputDialog",
    "ForecastDialog",
    "MainView",
    "MethodView",
    "StationaryTab",
    "TrendTab",
]
