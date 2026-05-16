"""Application settings for IIMP.

Settings are loaded from environment variables or .env file if present,
with sensible defaults for local development.
"""
import os
from pathlib import Path

# Load .env if present (simple manual parse — no additional dep needed)
_env_file = Path(__file__).parent.parent / ".env"
if _env_file.exists():
    with _env_file.open() as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

# ── Application metadata ──────────────────────────────────────────────────────
APP_NAME: str = "Integrated Interactive Module Platform"
APP_SHORT_NAME: str = "IIMP"
APP_VERSION: str = "0.1.0"
PLATFORM_VERSION: str = "1.0.0"
SDK_VERSION: str = "1.0.0"

# ── Runtime mode ──────────────────────────────────────────────────────────────
APP_ENV: str = os.getenv("APP_ENV", "production")
DEBUG: bool = os.getenv("APP_DEBUG", "false").lower() == "true"

# ── Window defaults ───────────────────────────────────────────────────────────
WINDOW_MIN_WIDTH: int = 1024
WINDOW_MIN_HEIGHT: int = 640
WINDOW_DEFAULT_WIDTH: int = 1280
WINDOW_DEFAULT_HEIGHT: int = 800

# ── Theme ─────────────────────────────────────────────────────────────────────
DEFAULT_THEME: str = "light"
