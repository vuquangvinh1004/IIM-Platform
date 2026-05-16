"""Application bootstrap for IIMP.

Bootstrap is the single entry point that initialises all infrastructure
in the correct order before the main window is created.
"""
from __future__ import annotations

import sys

from config.settings import DEBUG, APP_VERSION
from config.paths import ensure_runtime_dirs
from core.utils.logger import configure_logging, get_logger
from core.storage.connection import init_db
from core.app_kernel.startup_checks import run_startup_checks
from core.module_runtime.state_manager import clear_all_sessions

_log = get_logger("iimp.bootstrap")


def bootstrap() -> None:
    """Initialise all application infrastructure.

    Call order is intentional:
    1. Paths  — must exist before anything tries to write
    2. Logging — must be ready before other components log
    3. DB      — schema creation / migration
    4. Checks  — Python version, dependencies
    """
    ensure_runtime_dirs()
    configure_logging(debug=DEBUG)
    _log.info(f"IIMP v{APP_VERSION} starting up.")

    init_db()
    _log.info("Database initialised.")

    clear_all_sessions()
    _log.info("Module session state cleared for new session.")

    errors = run_startup_checks()
    if errors:
        for err in errors:
            _log.error(f"Startup check failed: {err}")
        _log.critical("Critical startup checks failed. Exiting.")
        sys.exit(1)

    _log.info("Bootstrap complete.")
