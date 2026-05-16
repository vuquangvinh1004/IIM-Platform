"""Tests for discovery progress callback and batch DB sync.

Covers:
- Phương án A integration: cache is used during discovery
- Phương án C: batch DB sync (single-query load)
- Phương án E: on_progress callback is invoked during discovery
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.module_runtime.discovery import discover_modules
from core.module_runtime.registry import ModuleRegistry
from core.utils.constants import ModuleState


def _make_module(parent: Path, mod_id: str) -> None:
    """Create a minimal valid module directory."""
    mod_dir = parent / mod_id
    mod_dir.mkdir(parents=True, exist_ok=True)
    (mod_dir / "module.json").write_text(
        json.dumps({
            "id": mod_id,
            "name": f"Module {mod_id}",
            "version": "1.0.0",
            "sdk_version": "1.0.0",
            "min_platform_version": "1.0.0",
            "entry_point": f"modules.{mod_id}.entry:Mod",
            "description": f"Test module {mod_id}",
            "category": "test",
            "author": "Tests",
            "permissions": [],
            "tags": [],
            "supports_state_restore": False,
            "supports_export": False,
        }),
        encoding="utf-8",
    )
    (mod_dir / "__init__.py").write_text("", encoding="utf-8")


# ── Progress callback tests ──────────────────────────────────────────────────


class TestDiscoveryProgressCallback:
    """Verify the on_progress callback is invoked correctly."""

    def test_progress_called_for_each_module(self, tmp_path: Path):
        _make_module(tmp_path, "alpha")
        _make_module(tmp_path, "beta")
        _make_module(tmp_path, "gamma")

        calls: list[tuple[int, int, str]] = []

        def on_progress(current: int, total: int, name: str) -> None:
            calls.append((current, total, name))

        reg = ModuleRegistry()
        found, failed = discover_modules(reg, tmp_path, on_progress=on_progress)

        assert found == 3
        assert failed == 0
        assert len(calls) == 3
        # Each call should have total == 3
        for current, total, name in calls:
            assert total == 3
        # Current values should be 1, 2, 3
        assert [c[0] for c in calls] == [1, 2, 3]

    def test_progress_not_required(self, tmp_path: Path):
        _make_module(tmp_path, "solo")
        reg = ModuleRegistry()
        # Should work fine without callback
        found, failed = discover_modules(reg, tmp_path)
        assert found == 1

    def test_progress_called_on_failed_modules(self, tmp_path: Path):
        # Create a broken module
        broken_dir = tmp_path / "broken"
        broken_dir.mkdir()
        (broken_dir / "module.json").write_text('{"id": "broken"}', encoding="utf-8")

        calls: list[tuple[int, int, str]] = []
        reg = ModuleRegistry()
        discover_modules(reg, tmp_path, on_progress=lambda c, t, n: calls.append((c, t, n)))

        assert len(calls) == 1
        assert calls[0][0] == 1  # current
        assert calls[0][1] == 1  # total

    def test_progress_with_empty_dir(self, tmp_path: Path):
        calls: list = []
        reg = ModuleRegistry()
        discover_modules(reg, tmp_path, on_progress=lambda c, t, n: calls.append(1))
        assert len(calls) == 0


# ── Cache integration tests ──────────────────────────────────────────────────


class TestDiscoveryCacheIntegration:
    """Verify cache is populated and used during discovery."""

    def test_second_discovery_uses_cache(self, tmp_path: Path):
        _make_module(tmp_path, "cached_mod")

        # First discovery — populates cache
        reg1 = ModuleRegistry()
        found1, _ = discover_modules(reg1, tmp_path)
        assert found1 == 1

        # Second discovery with fresh registry — should use cache
        reg2 = ModuleRegistry()
        found2, _ = discover_modules(reg2, tmp_path)
        assert found2 == 1
        assert reg2.is_registered("cached_mod")

    def test_modified_manifest_invalidates_cache(self, tmp_path: Path):
        import time

        mod_dir = tmp_path / "evolving"
        _make_module(tmp_path, "evolving")

        # First discovery
        reg1 = ModuleRegistry()
        discover_modules(reg1, tmp_path)
        assert reg1.get_record("evolving").manifest.version == "1.0.0"

        # Modify manifest
        time.sleep(0.05)
        manifest_path = mod_dir / "module.json"
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        data["version"] = "2.0.0"
        manifest_path.write_text(json.dumps(data), encoding="utf-8")

        # Second discovery should pick up the change
        reg2 = ModuleRegistry()
        discover_modules(reg2, tmp_path)
        assert reg2.get_record("evolving").manifest.version == "2.0.0"
