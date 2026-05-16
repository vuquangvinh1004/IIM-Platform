"""Startup validation checks for IIMP.

Each check returns a string error message on failure, or None on success.
``run_startup_checks`` collects failures and returns them to bootstrap.
"""
from __future__ import annotations

import sys
from typing import Callable

from core.utils.constants import MIN_PYTHON_VERSION


def _check_python_version() -> str | None:
    if sys.version_info < MIN_PYTHON_VERSION:
        required = ".".join(str(v) for v in MIN_PYTHON_VERSION)
        current = ".".join(str(v) for v in sys.version_info[:2])
        return f"Python {required}+ required, current is {current}"
    return None


def _check_pyside6() -> str | None:
    try:
        import PySide6  # noqa: F401
        return None
    except ImportError:
        return "PySide6 is not installed. Run: pip install -r requirements.txt"


def _check_sqlalchemy() -> str | None:
    try:
        import sqlalchemy  # noqa: F401
        return None
    except ImportError:
        return "SQLAlchemy is not installed."


_CHECKS: list[Callable[[], str | None]] = [
    _check_python_version,
    _check_pyside6,
    _check_sqlalchemy,
]


def run_startup_checks() -> list[str]:
    """Run all startup checks and return a list of error messages.

    An empty list means all checks passed.
    """
    errors: list[str] = []
    for check in _CHECKS:
        result = check()
        if result is not None:
            errors.append(result)
    return errors
