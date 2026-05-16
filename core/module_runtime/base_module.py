"""BaseModule — the official contract every IIMP module must implement.

Rules:
- All abstract methods are mandatory.
- ``build_view()`` must return exactly one QWidget root; never None.
- Module must not open its own top-level window inside these methods.
- Module must clean up all resources in ``on_unload()``.
- State dict returned by ``get_state()`` must be JSON-serializable.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget
else:
    try:
        from PySide6.QtWidgets import QWidget as QWidget  # noqa: PLC0414
    except ImportError:  # pragma: no cover — only missing in headless test envs
        QWidget = object  # type: ignore[misc,assignment]


class BaseModule(ABC):
    """Abstract base class for all IIMP modules.

    Attributes:
        manifest: The validated manifest dict supplied by the loader.
        context:  The ModuleContext instance supplied by the host.
    """

    manifest: dict
    context: Any  # ModuleContext — typed loosely to avoid circular import

    def __init__(self, manifest: dict, context: Any) -> None:
        self.manifest = manifest
        self.context = context

    # ── Mandatory lifecycle methods ───────────────────────────────────────────

    @abstractmethod
    def on_load(self) -> None:
        """Initialise lightweight resources, bind services, prepare caches.

        Do NOT render heavy widgets here. Called once after instantiation.
        """

    @abstractmethod
    def build_view(self) -> QWidget:
        """Construct and return the root QWidget for this module.

        Must always return a valid QWidget — never None.
        Must not call ``show()`` on the returned widget.
        Must be idempotent if called more than once.
        """

    @abstractmethod
    def on_activate(self) -> None:
        """Called when the module is placed into the workspace and made visible."""

    @abstractmethod
    def on_deactivate(self) -> None:
        """Called when the module loses focus or is replaced by another module."""

    @abstractmethod
    def on_unload(self) -> None:
        """Release all resources: stop timers, join workers, close file handles."""

    # ── Optional but strongly recommended ────────────────────────────────────

    def get_state(self) -> dict:
        """Return a JSON-serializable dict representing the current session state.

        Override in modules that declare ``supports_state_restore: true``.

        Required keys:
            ``_state_version`` (str): Must match ``data_contract_version`` from
            the module's manifest. ``StateManager`` uses this to detect schema
            mismatches and trigger ``migrate_state()`` on restore.

        All other keys are module-defined but must be JSON-serializable.

        Example::

            return {"_state_version": "1.0", "selected_tab": 0, "zoom": 1.5}
        """
        return {}

    def restore_state(self, state: dict) -> None:
        """Restore session state from a previously persisted dict.

        Must tolerate missing keys and older state schema versions without crashing.
        """

    def migrate_state(self, old_state: dict, old_version: str) -> dict:
        """Migrate *old_state* saved under *old_version* to the current schema.

        Override this when ``data_contract_version`` is bumped and existing
        persisted states must be transformed rather than discarded.

        The default implementation returns *old_state* unchanged (best-effort
        forward compatibility).
        """
        return old_state

    # ── Optional capabilities ─────────────────────────────────────────────────

    def get_settings_schema(self) -> dict:
        """Return a JSON Schema dict describing this module's settings.

        Return an empty dict if the module has no configurable settings.
        """
        return {}

    def export(self, target_path: str, export_type: str = "default") -> None:
        """Export module output to *target_path*.

        Override in modules that declare ``supports_export: true``.
        Raise ``NotImplementedError`` if not supported.
        """
        raise NotImplementedError(
            f"Module '{self.manifest.get('id')}' does not implement export."
        )

    # ── Convenience properties ────────────────────────────────────────────────

    @property
    def module_id(self) -> str:
        return self.manifest.get("id", "unknown")

    @property
    def module_name(self) -> str:
        return self.manifest.get("name", self.module_id)

    @property
    def module_version(self) -> str:
        return self.manifest.get("version", "0.0.0")

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} id={self.module_id} v{self.module_version}>"
