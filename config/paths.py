"""Application-level path configuration for IIMP.

All runtime paths are derived from this module. No module or service
should construct its own paths independently.
"""
from pathlib import Path

# Root of the project (directory containing this file's parent)
ROOT_DIR: Path = Path(__file__).parent.parent.resolve()

# ── Data directories ──────────────────────────────────────────────────────────
DATA_DIR: Path = ROOT_DIR / "data"
DATABASE_DIR: Path = DATA_DIR / "database"
MODULE_DATA_DIR: Path = DATA_DIR / "module_data"
WORKSPACE_DIR: Path = DATA_DIR / "workspace"
EXPORTS_DIR: Path = DATA_DIR / "exports"
TEMP_DIR: Path = DATA_DIR / "temp"
LOGS_DIR: Path = DATA_DIR / "logs"
CACHE_DIR: Path = DATA_DIR / "cache"

# ── Asset directories ─────────────────────────────────────────────────────────
ASSETS_DIR: Path = ROOT_DIR / "assets"
ICONS_DIR: Path = ASSETS_DIR / "icons"
IMAGES_DIR: Path = ASSETS_DIR / "images"
TEMPLATES_DIR: Path = ASSETS_DIR / "templates"

# ── Module directories ────────────────────────────────────────────────────────
MODULES_DIR: Path = ROOT_DIR / "modules"

# ── Database ──────────────────────────────────────────────────────────────────
DATABASE_FILE: Path = DATABASE_DIR / "iimp.db"
DATABASE_URL: str = f"sqlite:///{DATABASE_FILE}"


def ensure_runtime_dirs() -> None:
    """Create all required runtime data directories if they do not exist."""
    dirs = [
        DATABASE_DIR,
        MODULE_DATA_DIR,
        WORKSPACE_DIR,
        EXPORTS_DIR,
        TEMP_DIR,
        LOGS_DIR,
        CACHE_DIR,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
