"""Centralized logger configuration for IIMP using loguru.

All application code and modules should obtain their logger via
``get_logger()``. Modules should use the module_id as the name.
"""
import sys
from pathlib import Path

from loguru import logger as _loguru_logger

from config.paths import LOGS_DIR


def configure_logging(debug: bool = False) -> None:
    """Set up loguru sinks: stderr + rotating file.

    Must be called once during application bootstrap before any other
    component tries to log.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    _loguru_logger.remove()  # remove default sink

    level = "DEBUG" if debug else "INFO"

    # Console sink — only when stderr is available (not pythonw.exe)
    if sys.stderr is not None:
        _loguru_logger.add(
            sys.stderr,
            level=level,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
                   "<level>{level: <8}</level> | "
                   "<cyan>{extra[name]}</cyan> | "
                   "{message}",
            colorize=True,
        )

    # Rotating file sink
    _loguru_logger.add(
        LOGS_DIR / "iimp_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        rotation="10 MB",
        retention="14 days",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[name]} | {message}",
    )


def get_logger(name: str = "iimp"):
    """Return a loguru logger bound to *name*.

    Usage::

        log = get_logger("my_module_id")
        log.info("Module loaded")
    """
    return _loguru_logger.bind(name=name)
