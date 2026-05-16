"""Safe import utilities for IIMP modules.

Provides a standardised way to probe optional dependencies at import
time so every module uses the same pattern instead of ad-hoc
``try / except ImportError`` blocks.
"""
from __future__ import annotations

import importlib
import importlib.util
from typing import Any

from core.utils.logger import get_logger

_log = get_logger("iimp.imports")


def safe_import(module_name: str) -> tuple[Any, bool]:
    """Try to import *module_name* and return ``(module, True)`` on success.

    On ``ImportError`` returns ``(None, False)`` and logs a debug message.

    Usage::

        np, HAS_NUMPY = safe_import("numpy")
        if HAS_NUMPY:
            arr = np.array([1, 2, 3])
    """
    try:
        mod = importlib.import_module(module_name)
        return mod, True
    except ImportError:
        _log.debug("Optional dependency '%s' is not installed.", module_name)
        return None, False


def check_dependencies(dep_list: list[str]) -> list[str]:
    """Return the subset of *dep_list* that cannot be found on ``sys.path``.

    Uses ``importlib.util.find_spec`` for a lightweight probe — the
    packages are **not** actually imported.

    Example::

        missing = check_dependencies(["numpy", "scipy", "nonexistent"])
        # missing == ["nonexistent"]
    """
    missing: list[str] = []
    for name in dep_list:
        try:
            if importlib.util.find_spec(name) is None:
                missing.append(name)
        except (ModuleNotFoundError, ValueError):
            missing.append(name)
    return missing
