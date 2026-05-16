"""Platform-wide constants and enumerations for IIMP.

All magic strings and global enums must be defined here and imported
from here — never duplicated across modules or services.
"""
from enum import Enum, auto


# ── Platform versions ─────────────────────────────────────────────────────────
PLATFORM_VERSION = "1.0.0"
SDK_VERSION = "1.0.0"
MIN_PYTHON_VERSION = (3, 11)

# ── Module lifecycle states ───────────────────────────────────────────────────
class ModuleState(str, Enum):
    """Represents every valid lifecycle state a module can be in."""
    DISCOVERED = "discovered"
    VALIDATED = "validated"
    LOADED = "loaded"
    VIEW_BUILT = "view_built"
    ACTIVATED = "activated"
    DEACTIVATED = "deactivated"
    UNLOADED = "unloaded"
    ERROR = "error"
    INCOMPATIBLE = "incompatible"
    DISABLED = "disabled"


# ── Artifact types (for installed_artifacts table) ────────────────────────────
class ArtifactType(str, Enum):
    MODULE = "MODULE"
    TEMPLATE = "TEMPLATE"
    ASSET = "ASSET"


# ── Activity log types ────────────────────────────────────────────────────────
class ActivityType(str, Enum):
    APP_START = "app_start"
    APP_SHUTDOWN = "app_shutdown"
    MODULE_INSTALLED = "module_installed"
    MODULE_UNINSTALLED = "module_uninstalled"
    MODULE_ENABLED = "module_enabled"
    MODULE_DISABLED = "module_disabled"
    MODULE_ACTIVATED = "module_activated"
    MODULE_DEACTIVATED = "module_deactivated"
    MODULE_LOADED = "module_loaded"
    MODULE_LOAD_ERROR = "module_load_error"
    STATE_SAVED = "state_saved"
    STATE_RESTORED = "state_restored"
    STATE_RESTORE_FAILED = "state_restore_failed"
    EXPORT_STARTED = "export_started"
    EXPORT_COMPLETED = "export_completed"
    EXPORT_FAILED = "export_failed"
    DB_MIGRATION = "db_migration"


# ── Permission keys ───────────────────────────────────────────────────────────
class PermissionType(str, Enum):
    STORAGE_READ = "storage.read"
    STORAGE_WRITE = "storage.write"
    SETTINGS_READ = "settings.read"
    SETTINGS_WRITE = "settings.write"
    EXPORT_FILE = "export.file"
    DIALOGS_BASIC = "dialogs.basic"
    ACTIVITY_WRITE = "activity.write"
    WORKSPACE_CONTROL = "workspace.control"
    CLIPBOARD_WRITE = "clipboard.write"


# ── UI constants ──────────────────────────────────────────────────────────────
SIDEBAR_WIDTH = 200
STATUS_BAR_HEIGHT = 24
TOOLBAR_HEIGHT = 40
MODULE_CARD_HEIGHT = 90

# ── Database constants ────────────────────────────────────────────────────────
DB_SCHEMA_VERSION = "1.0.0"
