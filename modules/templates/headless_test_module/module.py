"""Headless test module — no PySide6 dependency.

Used exclusively by loader integration tests to verify the load/instantiate
pipeline without requiring a display or Qt installation.
"""
from __future__ import annotations

from core.module_runtime.base_module import BaseModule


class HeadlessTestModule(BaseModule):
    """Minimal BaseModule implementation with no external UI dependencies."""

    def on_load(self) -> None:
        pass

    def build_view(self):  # type: ignore[override]
        return None  # Never called in headless test context

    def on_activate(self) -> None:
        pass

    def on_deactivate(self) -> None:
        pass

    def on_unload(self) -> None:
        pass
