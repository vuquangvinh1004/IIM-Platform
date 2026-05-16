"""Unit tests for ShutdownManager."""
from __future__ import annotations

import pytest

from core.app_kernel.shutdown_manager import ShutdownManager


class TestShutdownManager:

    def test_register_and_run(self):
        sm = ShutdownManager()
        called = []
        sm.register("a", lambda: called.append("a"))
        sm.run_shutdown()
        assert "a" in called

    def test_lifo_order(self):
        sm = ShutdownManager()
        order = []
        sm.register("first", lambda: order.append("first"))
        sm.register("second", lambda: order.append("second"))
        sm.register("third", lambda: order.append("third"))
        sm.run_shutdown()
        assert order == ["third", "second", "first"]

    def test_handler_exception_does_not_abort_others(self):
        sm = ShutdownManager()
        completed = []

        def bad():
            raise RuntimeError("boom")

        sm.register("ok_first", lambda: completed.append("ok_first"))
        sm.register("bad", bad)
        sm.register("ok_last", lambda: completed.append("ok_last"))

        sm.run_shutdown()  # must not raise
        # Both ok handlers ran despite bad one
        assert "ok_first" in completed
        assert "ok_last" in completed

    def test_empty_shutdown_is_noop(self):
        sm = ShutdownManager()
        sm.run_shutdown()  # Must not raise

    def test_multiple_calls_execute_again(self):
        sm = ShutdownManager()
        count = [0]
        sm.register("counter", lambda: count.__setitem__(0, count[0] + 1))
        sm.run_shutdown()
        sm.run_shutdown()
        assert count[0] == 2
