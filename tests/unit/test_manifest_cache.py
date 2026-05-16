"""Tests for ManifestCache — Phương án A (discovery cache)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from core.module_runtime.manifest_cache import ManifestCache
from core.module_runtime.manifest_schema import ModuleManifest


# ── Helpers ───────────────────────────────────────────────────────────────────

_VALID_MANIFEST = {
    "id": "cache_test",
    "name": "Cache Test Module",
    "version": "1.0.0",
    "sdk_version": "1.0.0",
    "min_platform_version": "1.0.0",
    "entry_point": "modules.cache_test.entry:CacheModule",
    "description": "For manifest cache tests.",
    "category": "test",
    "author": "Tests",
    "permissions": [],
    "tags": [],
    "supports_state_restore": False,
    "supports_export": False,
}


def _write_manifest(module_dir: Path, data: dict | None = None) -> Path:
    module_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = module_dir / "module.json"
    manifest_path.write_text(
        json.dumps(data or _VALID_MANIFEST, ensure_ascii=False),
        encoding="utf-8",
    )
    return manifest_path


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestManifestCache:
    """Unit tests for ManifestCache."""

    def test_cache_miss_returns_none(self, tmp_path: Path):
        cache = ManifestCache(cache_file=tmp_path / "cache.json")
        module_dir = tmp_path / "nonexistent"
        assert cache.get_cached_manifest(module_dir) is None

    def test_put_and_get_returns_manifest(self, tmp_path: Path):
        cache = ManifestCache(cache_file=tmp_path / "cache.json")
        module_dir = tmp_path / "mod_a"
        _write_manifest(module_dir)

        manifest = ModuleManifest.model_validate(_VALID_MANIFEST)
        cache.put(module_dir, manifest)

        result = cache.get_cached_manifest(module_dir)
        assert result is not None
        assert result.id == "cache_test"
        assert result.version == "1.0.0"

    def test_cache_invalidated_on_mtime_change(self, tmp_path: Path):
        import time

        cache = ManifestCache(cache_file=tmp_path / "cache.json")
        module_dir = tmp_path / "mod_b"
        manifest_path = _write_manifest(module_dir)

        manifest = ModuleManifest.model_validate(_VALID_MANIFEST)
        cache.put(module_dir, manifest)

        # Simulate file change (update mtime)
        time.sleep(0.05)
        updated = {**_VALID_MANIFEST, "version": "2.0.0"}
        manifest_path.write_text(json.dumps(updated), encoding="utf-8")

        # Cache should miss because mtime changed
        assert cache.get_cached_manifest(module_dir) is None

    def test_save_and_reload(self, tmp_path: Path):
        cache_file = tmp_path / "cache.json"
        cache = ManifestCache(cache_file=cache_file)
        module_dir = tmp_path / "mod_c"
        _write_manifest(module_dir)

        manifest = ModuleManifest.model_validate(_VALID_MANIFEST)
        cache.put(module_dir, manifest)
        cache.save()

        assert cache_file.exists()

        # Reload from disk
        cache2 = ManifestCache(cache_file=cache_file)
        result = cache2.get_cached_manifest(module_dir)
        assert result is not None
        assert result.id == "cache_test"

    def test_invalidate_removes_entry(self, tmp_path: Path):
        cache = ManifestCache(cache_file=tmp_path / "cache.json")
        module_dir = tmp_path / "mod_d"
        _write_manifest(module_dir)

        manifest = ModuleManifest.model_validate(_VALID_MANIFEST)
        cache.put(module_dir, manifest)
        assert cache.get_cached_manifest(module_dir) is not None

        cache.invalidate(module_dir)
        assert cache.get_cached_manifest(module_dir) is None

    def test_clear_removes_all(self, tmp_path: Path):
        cache_file = tmp_path / "cache.json"
        cache = ManifestCache(cache_file=cache_file)
        module_dir = tmp_path / "mod_e"
        _write_manifest(module_dir)

        manifest = ModuleManifest.model_validate(_VALID_MANIFEST)
        cache.put(module_dir, manifest)
        cache.save()

        cache.clear()
        assert cache.get_cached_manifest(module_dir) is None
        assert not cache_file.exists()

    def test_corrupt_cache_file_handled(self, tmp_path: Path):
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("NOT JSON!", encoding="utf-8")

        # Should not raise, just starts with empty cache
        cache = ManifestCache(cache_file=cache_file)
        assert cache.get_cached_manifest(tmp_path / "anything") is None

    def test_no_manifest_file_returns_none(self, tmp_path: Path):
        cache = ManifestCache(cache_file=tmp_path / "cache.json")
        module_dir = tmp_path / "empty_mod"
        module_dir.mkdir()  # no module.json inside
        assert cache.get_cached_manifest(module_dir) is None
