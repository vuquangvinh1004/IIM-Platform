"""Graceful shutdown manager for IIMP.

Handlers registered here are called in LIFO order when the application
exits, ensuring resources are released before the process terminates.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from core.utils.logger import get_logger

if TYPE_CHECKING:
    from PySide6.QtWidgets import QApplication

_log = get_logger("iimp.shutdown")


class ShutdownManager:
    """Collects and executes cleanup callbacks on application exit."""

    def __init__(self) -> None:
        self._handlers: list[tuple[str, Callable[[], None]]] = []

    def connect_to_app(self, app: "QApplication") -> None:
        """Wire the Qt application's aboutToQuit signal to run_shutdown.

        Call once after creating the QApplication so all registered handlers
        are executed when the user closes the window or the event loop exits.
        """
        app.aboutToQuit.connect(self.run_shutdown)
        _log.debug("Shutdown handler connected to QApplication.aboutToQuit.")

    def register(self, name: str, handler: Callable[[], None]) -> None:
        """Register a named shutdown callback."""
        self._handlers.append((name, handler))
        _log.debug(f"Registered shutdown handler: {name}")

    def run_shutdown(self) -> None:
        """Execute all registered handlers in reverse registration order."""
        _log.info("Running shutdown sequence.")
        for name, handler in reversed(self._handlers):
            try:
                _log.debug(f"Calling shutdown handler: {name}")
                handler()
            except Exception:
                _log.exception(f"Error in shutdown handler '{name}' — continuing.")
        _log.info("Shutdown complete.")
