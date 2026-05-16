"""Lightweight pub-sub event bus for IIMP.

Modules publish events via ``context.event_bus``. Shell components can
subscribe to specific event topics. The bus is intentionally simple —
no persistence, no threading, fire-and-forget on the Qt main thread.

Event naming convention:
    ``module.<module_id>.<action>``   — module-scoped events
    ``app.<domain>.<action>``         — platform-scoped events
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable

from core.utils.logger import get_logger

_log = get_logger("iimp.event_bus")

Listener = Callable[[str, dict], None]


class EventBus:
    """Simple synchronous pub-sub bus."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Listener]] = defaultdict(list)

    def subscribe(self, topic: str, listener: Listener) -> None:
        """Register *listener* for *topic*. Wildcards not supported."""
        self._listeners[topic].append(listener)
        _log.debug(f"Subscribed to '{topic}': {listener}")

    def unsubscribe(self, topic: str, listener: Listener) -> None:
        """Remove *listener* from *topic*. Silently ignores if not found."""
        try:
            self._listeners[topic].remove(listener)
        except ValueError:
            pass

    def publish(self, topic: str, payload: dict[str, Any] | None = None) -> None:
        """Dispatch *payload* to all listeners subscribed to *topic*."""
        data = payload or {}
        listeners = list(self._listeners.get(topic, []))
        if not listeners:
            return
        _log.debug(f"Publishing '{topic}' to {len(listeners)} listener(s).")
        for listener in listeners:
            try:
                listener(topic, data)
            except Exception:
                _log.exception(f"Listener error on topic '{topic}'.")

    def clear(self) -> None:
        """Remove all listeners (used during shutdown or testing)."""
        self._listeners.clear()
