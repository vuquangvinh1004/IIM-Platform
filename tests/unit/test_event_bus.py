"""Unit tests for EventBus."""
from __future__ import annotations

import pytest

from core.module_runtime.event_bus import EventBus


class TestSubscribePublish:

    def test_publish_calls_listener(self):
        bus = EventBus()
        received = []
        bus.subscribe("app.test.event", lambda topic, data: received.append((topic, data)))
        bus.publish("app.test.event", {"key": "val"})
        assert received == [("app.test.event", {"key": "val"})]

    def test_publish_no_listeners_is_noop(self):
        bus = EventBus()
        # Must not raise
        bus.publish("app.ghost.event", {"x": 1})

    def test_publish_none_payload_defaults_to_empty_dict(self):
        bus = EventBus()
        received = []
        bus.subscribe("topic", lambda t, d: received.append(d))
        bus.publish("topic")
        assert received == [{}]

    def test_multiple_listeners_all_called(self):
        bus = EventBus()
        calls: list[int] = []
        bus.subscribe("t", lambda t, d: calls.append(1))
        bus.subscribe("t", lambda t, d: calls.append(2))
        bus.publish("t")
        assert calls == [1, 2]

    def test_listener_exception_does_not_propagate(self):
        bus = EventBus()

        def bad_listener(topic, data):
            raise RuntimeError("listener error")

        bus.subscribe("x", bad_listener)
        # Should not raise — exception is swallowed and logged
        bus.publish("x")

    def test_unsubscribe_removes_listener(self):
        bus = EventBus()
        received = []
        listener = lambda t, d: received.append(d)
        bus.subscribe("t", listener)
        bus.unsubscribe("t", listener)
        bus.publish("t", {"x": 1})
        assert received == []

    def test_unsubscribe_nonexistent_is_noop(self):
        bus = EventBus()
        listener = lambda t, d: None
        bus.unsubscribe("t", listener)  # Must not raise

    def test_clear_removes_all_listeners(self):
        bus = EventBus()
        received = []
        bus.subscribe("a", lambda t, d: received.append(d))
        bus.subscribe("b", lambda t, d: received.append(d))
        bus.clear()
        bus.publish("a")
        bus.publish("b")
        assert received == []

    def test_isolated_topics(self):
        bus = EventBus()
        received = []
        bus.subscribe("topic.a", lambda t, d: received.append("a"))
        bus.publish("topic.b")
        assert received == []
