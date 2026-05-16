"""Compatibility shim — connect_shutdown has moved to ShutdownManager.

Use ``shutdown_manager.connect_to_app(app)`` directly instead.
This module is kept only for backward compatibility and will be removed.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication
    from core.app_kernel.shutdown_manager import ShutdownManager


def connect_shutdown(app: "QApplication", shutdown_manager: "ShutdownManager") -> None:
    """Deprecated: call ``shutdown_manager.connect_to_app(app)`` directly."""
    shutdown_manager.connect_to_app(app)
