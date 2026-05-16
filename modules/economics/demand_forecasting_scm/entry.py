"""Entry point cho module demand_forecasting_scm.

IIMP loader tìm symbol được khai báo trong entry_point của module.json.
"""
from .module import DemandForecastingModule

__all__ = ["DemandForecastingModule"]
