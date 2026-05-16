"""Platform-wide exception hierarchy for IIMP.

Raise the most specific exception possible so callers can handle
different failure modes cleanly without catching broad Exception.
"""


class IIMPError(Exception):
    """Base for all IIMP-specific errors."""


# ── Manifest errors ───────────────────────────────────────────────────────────
class ManifestError(IIMPError):
    """Raised when a module manifest is invalid or missing required fields."""

    def __init__(self, module_path: str, detail: str) -> None:
        self.module_path = module_path
        self.detail = detail
        super().__init__(f"Manifest error in '{module_path}': {detail}")


class ManifestNotFoundError(ManifestError):
    """Raised when module.json does not exist at the expected path."""

    def __init__(self, module_path: str) -> None:
        super().__init__(module_path, "module.json not found")


class ManifestValidationError(ManifestError):
    """Raised when manifest is found but fails schema validation."""


# ── Module load errors ────────────────────────────────────────────────────────
class ModuleLoadError(IIMPError):
    """Raised when a module entry point cannot be imported or instantiated."""

    def __init__(self, module_id: str, detail: str) -> None:
        self.module_id = module_id
        self.detail = detail
        super().__init__(f"Failed to load module '{module_id}': {detail}")


class ModuleNotFoundError(ModuleLoadError):
    """Raised when the module class cannot be resolved from entry_point."""


class ModuleCompatibilityError(IIMPError):
    """Raised when module sdk_version or min_platform_version is incompatible."""

    def __init__(self, module_id: str, required: str, current: str) -> None:
        self.module_id = module_id
        super().__init__(
            f"Module '{module_id}' requires platform >= {required}, current is {current}"
        )


# ── Dependency errors ─────────────────────────────────────────────────────────
class DependencyMissingError(ModuleLoadError):
    """Raised when a module's optional dependencies are not installed."""

    def __init__(self, module_id: str, missing: list[str]) -> None:
        self.missing = missing
        pkgs = ", ".join(missing)
        super().__init__(module_id, f"Missing optional dependencies: {pkgs}")


# ── State errors ──────────────────────────────────────────────────────────────
class StateError(IIMPError):
    """Base for state serialization / restore failures."""


class StateSaveError(StateError):
    """Raised when get_state() or state serialization fails."""


class StateRestoreError(StateError):
    """Raised when restore_state() fails; module should fallback gracefully."""


# ── Storage errors ────────────────────────────────────────────────────────────
class StorageError(IIMPError):
    """Raised for database or file I/O failures."""


class MigrationError(StorageError):
    """Raised when a DB migration cannot be applied."""


# ── Service errors ────────────────────────────────────────────────────────────
class ServiceUnavailableError(IIMPError):
    """Raised when a required host service is not registered."""

    def __init__(self, service_name: str) -> None:
        super().__init__(f"Host service '{service_name}' is not available")


# ── Export errors ─────────────────────────────────────────────────────────────
class ExportError(IIMPError):
    """Raised when an export operation fails."""
